# 统一渗透测试报告构建：读取 Strix 输出，拼接为单一 Markdown，可选 LLM 中文化；HTML 报告按 NetOps 平台样式生成
import os
import re
import html
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
import requests
from utils.datetime_utils import utc_to_beijing_str

logger = logging.getLogger(__name__)

# 统一报告文件名
UNIFIED_REPORT_MD = "unified_penetration_test_report.md"
UNIFIED_REPORT_HTML = "unified_penetration_test_report.html"

# 严重程度排序与展示名
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_LABELS = {
    "critical": "严重",
    "high": "高危",
    "medium": "中危",
    "low": "低危",
    "info": "信息",
}

# CWE 到漏洞类型展示名（部分常见映射，其余用标题或「其他」）
CWE_TYPE_MAP = {
    "CWE-22": "路径遍历",
    "CWE-79": "跨站脚本",
    "CWE-89": "SQL 注入",
    "CWE-98": "文件包含",
    "CWE-284": "访问控制",
    "CWE-362": "竞态条件",
    "CWE-538": "信息泄露",
    "CWE-287": "认证绕过",
    "CWE-384": "会话固定",
    "CWE-613": "会话固定",
}


def _resolve_report_dir(report_path: str) -> Optional[str]:
    """解析得到包含 penetration_test_report.md 的目录（含子目录查找）。"""
    if not report_path or not os.path.isdir(report_path):
        return None
    p = os.path.join(report_path, "penetration_test_report.md")
    if os.path.isfile(p):
        return report_path
    for sub in os.listdir(report_path):
        sub_path = os.path.join(report_path, sub)
        if not os.path.isdir(sub_path):
            continue
        if os.path.isfile(os.path.join(sub_path, "penetration_test_report.md")):
            return sub_path
        for sub2 in os.listdir(sub_path):
            sub2_path = os.path.join(sub_path, sub2)
            if os.path.isdir(sub2_path) and os.path.isfile(os.path.join(sub2_path, "penetration_test_report.md")):
                return sub2_path
    return None


def _read_main_report(md_path: str) -> str:
    """读取总报告全文。"""
    try:
        with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logger.warning("读取总报告失败: %s", e)
        return ""


def _split_main_sections(content: str) -> dict:
    """按 # 标题切分总报告为 Executive Summary / Methodology / Technical Analysis / Recommendations。"""
    sections = {}
    current = []
    current_key = None
    for line in content.splitlines():
        if line.strip().startswith("# "):
            if current_key:
                sections[current_key] = "\n".join(current).strip()
            title = line.strip().lstrip("#").strip()
            current_key = title
            current = []
        elif current_key:
            current.append(line)
    if current_key:
        sections[current_key] = "\n".join(current).strip()
    return sections


def _list_vulnerability_files(vuln_dir: str) -> List[Tuple[str, str]]:
    """返回 (id, filepath) 列表，按 severity 与 id 排序。"""
    items = _get_vuln_list_with_severity(vuln_dir)
    return [(vid, path) for vid, path, _ in items]


def _vuln_id_to_index(vuln_id: str) -> int:
    """从 vuln-0001 / vuln-0010 等提取序号，用于按 1,2,...,10 排序。"""
    m = re.search(r"(\d+)\s*$", vuln_id.strip())
    return int(m.group(1)) if m else 0


def _get_vuln_list_with_severity(vuln_dir: str) -> List[Tuple[str, str, str]]:
    """返回 (id, filepath, severity) 列表，按漏洞编号从小到大排序（vuln-0001, 0002, ..., 0010）。"""
    if not os.path.isdir(vuln_dir):
        return []
    items = []
    for f in os.listdir(vuln_dir):
        if not f.endswith(".md"):
            continue
        path = os.path.join(vuln_dir, f)
        if not os.path.isfile(path):
            continue
        id_ = f.replace(".md", "")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                head = fp.read(1024)
            sev = "info"
            for line in head.splitlines():
                if "**Severity:**" in line or "**Severity**: " in line:
                    m = re.search(r"(?:critical|high|medium|low|info)", line.lower())
                    if m:
                        sev = m.group(0)
                    break
            items.append((_vuln_id_to_index(id_), id_, path, sev))
        except Exception:
            items.append((0, id_, path, "info"))
    items.sort(key=lambda x: (x[0], x[1]))
    return [(id_, path, sev) for _, id_, path, sev in items]


def _severity_counts(vuln_list_with_severity: List[Tuple[str, str, str]]) -> Dict[str, int]:
    """根据 (id, path, severity) 列表统计各等级数量。返回 total, critical, high, medium, low, info。"""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for _, _, sev in vuln_list_with_severity:
        key = sev.lower() if sev else "info"
        if key not in counts:
            key = "info"
        counts[key] = counts.get(key, 0) + 1
    counts["total"] = sum(counts[k] for k in ("critical", "high", "medium", "low", "info"))
    return counts


def _parse_vuln_from_content(content: str, path_for_log: str = "") -> Dict[str, Any]:
    """从 vuln 文件内容字符串解析出结构化字段与各 section 正文（供 MD 翻译后复用）。"""
    result = {
        "title": "",
        "id": "",
        "severity": "info",
        "found": "",
        "target": "",
        "endpoint": "",
        "method": "",
        "cwe": "",
        "cvss": "",
        "type_label": "",
        "description": "",
        "impact": "",
        "technical_analysis": "",
        "proof": "",
        "remediation": "",
    }
    lines = content.splitlines()
    # 首行标题
    for line in lines:
        s = line.strip()
        if s.startswith("# "):
            result["title"] = s.lstrip("#").strip()
            break

    # **Key:** value
    key_pattern = re.compile(r"^\*\*([^*]+)\*\*:\s*(.*)$")
    for line in lines:
        m = key_pattern.match(line.strip())
        if m:
            key, val = m.group(1).strip().lower(), m.group(2).strip()
            if key == "id":
                result["id"] = val
            elif key == "severity":
                result["severity"] = val.lower() if val else "info"
            elif key == "found":
                result["found"] = val
            elif key == "target":
                result["target"] = val
            elif key == "endpoint":
                result["endpoint"] = val
            elif key == "method":
                result["method"] = val
            elif key == "cwe":
                result["cwe"] = val
            elif key == "cvss":
                result["cvss"] = val

    # 类型：优先 CWE 映射，否则用标题首段
    if result["cwe"]:
        cwe_upper = result["cwe"].upper().split()[0] if result["cwe"] else ""
        result["type_label"] = CWE_TYPE_MAP.get(cwe_upper, result["title"] or "其他")
    else:
        result["type_label"] = result["title"] or "其他"

    # ## Section 正文（支持中英文标题与三级标题，翻译后可能为中文；同一 key 多次出现则追加内容确保修复建议不丢失）
    section_headers = [
        ("description", "## Description"),
        ("description", "## 描述"),
        ("impact", "## Impact"),
        ("impact", "## 影响"),
        ("technical_analysis", "## Technical Analysis"),
        ("technical_analysis", "## 技术分析"),
        ("proof", "## Proof of Concept"),
        ("proof", "## 概念验证"),
        ("remediation", "## Remediation"),
        ("remediation", "## 修复建议"),
        ("remediation", "## 整改措施"),
        ("remediation", "### Remediation"),
        ("remediation", "### 修复建议"),
        ("remediation", "### 整改措施"),
        ("remediation", "### 修复"),
        ("remediation", "## 修复"),
        ("remediation", "## 建议"),
    ]
    current_key = None
    current_lines = []
    for line in lines:
        line_stripped = line.strip()
        matched = False
        for key, header in section_headers:
            if line_stripped.startswith(header):
                if current_key:
                    new_content = "\n".join(current_lines).strip()
                    if new_content:
                        existing = (result.get(current_key) or "").strip()
                        result[current_key] = (existing + "\n\n" + new_content) if existing else new_content
                current_key = key
                current_lines = []
                rest = line_stripped[len(header) :].strip()
                if rest:
                    current_lines.append(rest)
                matched = True
                break
        if not matched and current_key:
            current_lines.append(line)
    if current_key:
        new_content = "\n".join(current_lines).strip()
        if new_content:
            existing = (result.get(current_key) or "").strip()
            result[current_key] = (existing + "\n\n" + new_content) if existing else new_content

    # 若修复建议仍为空，尝试从全文末尾或含「修复」的段落兜底提取（确保写入）
    if not (result.get("remediation") or "").strip():
        fallback = _extract_remediation_fallback(content)
        if fallback:
            result["remediation"] = fallback

    return result


def _extract_remediation_fallback(content: str) -> str:
    """当未解析到修复建议时，从正文中尝试提取含修复/建议的段落。"""
    if not content or not content.strip():
        return ""
    # 尝试匹配 ## Remediation / ## 修复建议 后的整块（含多种写法）
    for pattern in [
        r"##\s*Remediation\s*\n([\s\S]*?)(?=\n##\s|\n###\s|\Z)",
        r"##\s*修复建议\s*\n([\s\S]*?)(?=\n##\s|\n###\s|\Z)",
        r"##\s*整改措施\s*\n([\s\S]*?)(?=\n##\s|\n###\s|\Z)",
        r"###\s*修复建议\s*\n([\s\S]*?)(?=\n##\s|\n###\s|\Z)",
        r"###\s*整改措施\s*\n([\s\S]*?)(?=\n##\s|\n###\s|\Z)",
        r"###\s*Remediation\s*\n([\s\S]*?)(?=\n##\s|\n###\s|\Z)",
    ]:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            block = m.group(1).strip()
            if len(block) > 20:
                return block
    return ""


def _parse_vuln_md(path: str) -> Dict[str, Any]:
    """从文件路径读取并解析 vuln-0xxx.md。"""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        logger.warning("读取漏洞文件失败 %s: %s", path, e)
        return {
            "title": "", "id": "", "severity": "info", "found": "", "target": "",
            "endpoint": "", "method": "", "cwe": "", "cvss": "", "type_label": "",
            "description": "", "impact": "", "technical_analysis": "", "proof": "", "remediation": "",
        }
    return _parse_vuln_from_content(content, path)


def _markdown_to_html(text: str) -> str:
    """将 Markdown 转为 HTML 片段，无外围标签。"""
    if not (text or text.strip()):
        return ""
    try:
        import markdown
        return markdown.markdown(text, extensions=["extra", "codehilite"])
    except ImportError:
        return "<pre>" + html.escape(text) + "</pre>"


def _build_html_report(
    main_report_html: str,
    vuln_list_with_severity: List[Tuple[str, str, str]],
    vuln_parsed_list: List[Dict[str, Any]],
    session_id: str,
) -> str:
    """生成符合 NetOps 平台样式的静态 HTML 报告（三部分：总报告、威胁统计卡片、漏洞列表）。vuln_parsed_list 与 vuln_list_with_severity 顺序一致，且已含可选 LLM 翻译后的内容。"""
    counts = _severity_counts(vuln_list_with_severity)
    card_colors = {
        "total": "#ff4d4f",
        "critical": "#ff4d4f",
        "high": "#fa8c16",
        "medium": "#faad14",
        "low": "#52c41a",
        "info": "#1890ff",
    }
    cards_html = []
    for key, label in [
        ("total", "总漏洞数"),
        ("critical", "严重"),
        ("high", "高危"),
        ("medium", "中危"),
        ("low", "低危"),
        ("info", "信息"),
    ]:
        num = counts.get(key, 0) if key != "total" else counts.get("total", 0)
        border = card_colors.get(key, "#d9d9d9")
        cards_html.append(
            f'<div class="stat-card stat-card-{key}" style="border-left: 4px solid {border}">'
            f'<div class="stat-value">{num}</div><div class="stat-label">{label}</div></div>'
        )
    stats_section = '<div class="stats-row">' + "".join(cards_html) + "</div>"

    vuln_blocks = []
    for idx, (vid, path, _) in enumerate(vuln_list_with_severity):
        v = vuln_parsed_list[idx] if idx < len(vuln_parsed_list) else _parse_vuln_md(path)
        sev = v.get("severity") or "info"
        sev_label = SEVERITY_LABELS.get(sev, sev)
        border_color = card_colors.get(sev, "#d9d9d9")
        desc_html = _markdown_to_html(v.get("description") or "")
        # 证明、影响、修复建议合并为一段正文，不再分节，避免翻译/解析差异导致缺漏
        proof_html = _markdown_to_html(v.get("proof") or "")
        impact_html = _markdown_to_html(v.get("impact") or "")
        remediation_html = _markdown_to_html(v.get("remediation") or "")
        detail_parts = [p for p in (proof_html, impact_html, remediation_html) if (p or "").strip()]
        detail_combined = "\n\n".join(detail_parts) if detail_parts else ""

        title_esc = html.escape(v.get("title") or vid)
        id_esc = html.escape(v.get("id") or vid)
        type_esc = html.escape(v.get("type_label") or "-")
        target_esc = html.escape(v.get("target") or "-")
        session_esc = html.escape(session_id)
        found_esc = html.escape(v.get("found") or "-")

        block = f"""
<div class="vuln-card" style="border-left: 4px solid {border_color}">
  <details class="vuln-details" open>
    <summary class="vuln-summary">
      <span class="vuln-title">{title_esc}</span>
      <span class="vuln-tag severity-{sev}" style="background: {border_color}; color: #fff;">{sev_label}</span>
      <span class="vuln-tag status">待处理</span>
      <span class="vuln-time">{found_esc}</span>
    </summary>
    <div class="vuln-body">
      <div class="vuln-desc section"><h4>描述</h4>{desc_html}</div>
      <div class="vuln-meta section">
        <h4>详细信息</h4>
        <table class="meta-table">
          <tr><td>漏洞ID</td><td>{id_esc}</td></tr>
          <tr><td>类型</td><td>{type_esc}</td></tr>
          <tr><td>目标</td><td>{target_esc}</td></tr>
          <tr><td>会话ID</td><td>{session_esc}</td></tr>
        </table>
      </div>
      <div class="vuln-detail section"><h4>详情</h4>{detail_combined}</div>
    </div>
  </details>
</div>"""
        vuln_blocks.append(block)

    vuln_section = '<div class="vuln-list">' + "\n".join(vuln_blocks) + "</div>"

    css = """
* { box-sizing: border-box; }
.report-page {
  max-width: 1000px; margin: 0 auto; padding: 32px 24px 48px;
  background: linear-gradient(165deg, #e8ecf4 0%, #dde2eb 30%, #f0f3f8 70%, #e4e8f0 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 14px; line-height: 1.6; color: #1f2937;
}
.report-page .report-header {
  text-align: center; margin-bottom: 28px; padding: 24px 28px;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 50%, #3b82f6 100%);
  border-radius: 12px; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
}
.report-page .report-header h1 {
  font-size: 22px; font-weight: 700; margin: 0; color: #fff; letter-spacing: 0.5px; text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}
.report-page .main-report {
  background: #fff; border-radius: 12px; padding: 28px 32px; margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06); border: 1px solid rgba(30, 58, 95, 0.08);
}
.report-page .main-report h1 { font-size: 18px; margin: 0 0 16px; color: #1e3a5f; }
.report-page .main-report h2 {
  font-size: 16px; margin: 24px 0 12px; color: #1e40af; font-weight: 600;
  padding-bottom: 6px; border-bottom: 2px solid #93c5fd;
}
.report-page .main-report p { margin: 0 0 12px; }
.report-page .main-report strong { color: #1e3a5f; }
.report-page .stats-row { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 24px; }
.report-page .stat-card {
  border-radius: 12px; padding: 20px 24px; min-width: 128px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.report-page .stat-card:hover { box-shadow: 0 6px 16px rgba(0,0,0,0.1); transform: translateY(-2px); }
.report-page .stat-card-total { background: linear-gradient(145deg, #f8fafc 0%, #f1f5f9 100%); border: 1px solid #e2e8f0; }
.report-page .stat-card-total .stat-value { color: #475569; }
.report-page .stat-card-critical { background: linear-gradient(145deg, #fef2f2 0%, #fee2e2 100%); border: 1px solid #fecaca; }
.report-page .stat-card-critical .stat-value { color: #dc2626; }
.report-page .stat-card-critical .stat-label { color: #b91c1c; }
.report-page .stat-card-high { background: linear-gradient(145deg, #fff7ed 0%, #ffedd5 100%); border: 1px solid #fed7aa; }
.report-page .stat-card-high .stat-value { color: #ea580c; }
.report-page .stat-card-high .stat-label { color: #c2410c; }
.report-page .stat-card-medium { background: linear-gradient(145deg, #fefce8 0%, #fef9c3 100%); border: 1px solid #fde047; }
.report-page .stat-card-medium .stat-value { color: #ca8a04; }
.report-page .stat-card-medium .stat-label { color: #a16207; }
.report-page .stat-card-low { background: linear-gradient(145deg, #f0fdf4 0%, #dcfce7 100%); border: 1px solid #bbf7d0; }
.report-page .stat-card-low .stat-value { color: #16a34a; }
.report-page .stat-card-low .stat-label { color: #15803d; }
.report-page .stat-card-info { background: linear-gradient(145deg, #eff6ff 0%, #dbeafe 100%); border: 1px solid #93c5fd; }
.report-page .stat-card-info .stat-value { color: #2563eb; }
.report-page .stat-card-info .stat-label { color: #1d4ed8; }
.report-page .stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.report-page .stat-label { font-size: 13px; margin-top: 6px; font-weight: 500; }
.report-page .vuln-list-title {
  font-size: 17px; font-weight: 700; margin-bottom: 16px; color: #1e3a5f; padding: 0 4px;
}
.report-page .vuln-list { display: flex; flex-direction: column; gap: 16px; }
.report-page .vuln-card {
  background: #fff; border-radius: 12px; padding: 20px 24px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.06); border: 1px solid rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease;
}
.report-page .vuln-card:hover { box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
.report-page .vuln-details { border: none; }
.report-page .vuln-summary {
  display: flex; align-items: center; flex-wrap: wrap; gap: 10px; cursor: pointer; list-style: none;
  padding: 4px 0; font-size: 14px;
}
.report-page .vuln-summary::-webkit-details-marker { display: none; }
.report-page .vuln-title { font-weight: 600; flex: 1 1 auto; color: #1f2937; }
.report-page .vuln-tag { padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 500; }
.report-page .vuln-tag.status { background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); color: #1d4ed8; border: 1px solid #93c5fd; }
.report-page .vuln-time { color: #6b7280; font-size: 13px; }
.report-page .vuln-body {
  margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb;
}
.report-page .vuln-body .section { margin-bottom: 20px; overflow: visible; max-height: none; }
.report-page .vuln-body .section:last-child { margin-bottom: 0; }
.report-page .vuln-body .vuln-desc, .report-page .vuln-body .vuln-detail { overflow: visible; max-height: none; }
.report-page .vuln-body .section h4 {
  font-size: 14px; font-weight: 600; margin: 0 0 10px; color: #1e40af;
  padding-left: 8px; border-left: 3px solid #3b82f6;
}
.report-page .meta-table { border-collapse: collapse; width: 100%; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.report-page .meta-table td { border: 1px solid #e5e7eb; padding: 10px 14px; }
.report-page .meta-table td:first-child { width: 100px; color: #4b5563; font-weight: 600; background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%); }
.report-page .vuln-body .section pre {
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); padding: 14px 16px; overflow: visible; max-height: none; border-radius: 8px;
  font-size: 13px; border: 1px solid #cbd5e1; margin: 8px 0; color: #334155; white-space: pre-wrap; word-break: break-all;
}
.report-page pre {
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); padding: 14px 16px; overflow: visible; max-height: none; border-radius: 8px;
  font-size: 13px; border: 1px solid #cbd5e1; margin: 8px 0; color: #334155; white-space: pre-wrap; word-break: break-all;
}
.report-page code { background: #e0e7ff; color: #3730a3; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
.report-page table { border-collapse: collapse; width: 100%; }
.report-page th, .report-page td { border: 1px solid #e5e7eb; padding: 10px 14px; }
.report-page .main-report ul, .report-page .vuln-body ul { margin: 8px 0; padding-left: 24px; }
.report-page .main-report li, .report-page .vuln-body li { margin: 4px 0; }
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>渗透测试报告 - NetOps 平台生成</title>
  <style>{css}</style>
</head>
<body class="report-page">
  <header class="report-header">
    <h1>渗透测试报告 - NetOps 平台生成</h1>
  </header>
  <div class="main-report">{main_report_html}</div>
  {stats_section}
  <div class="vuln-list-title" style="font-weight:600; margin-bottom:12px;">漏洞列表</div>
  {vuln_section}
</body>
</html>"""


def _translate_with_llm(
    text: str,
    api_key: str,
    api_base: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 60,
) -> Optional[str]:
    """调用 OpenAI 兼容的 Chat 接口将英文段落翻译为中文。api_base 留空则用 https://api.openai.com/v1。"""
    if not text or not text.strip():
        return text
    base = (api_base or "").strip().rstrip("/") or "https://api.openai.com/v1"
    url = f"{base}/chat/completions" if not base.endswith("/chat/completions") else base
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": (model or "").strip() or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "你只输出翻译后的中文内容，不要添加任何解释或前后缀。保留 Markdown 格式、代码块和列表结构。"},
                    {"role": "user", "content": f"将以下安全报告段落翻译为中文，保持原有格式：\n\n{text[:6000]}"},
                ],
                "max_tokens": 4096,
                "temperature": 0.2,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data.get("choices") or []
        if choice and isinstance(choice[0].get("message"), dict):
            return (choice[0]["message"].get("content") or "").strip()
    except Exception as e:
        logger.warning("LLM 翻译失败: %s", e)
    return None


def build_unified_report(
    report_path: str,
    task_target_value: Optional[str] = None,
    task_created_at: Optional[str] = None,
    task_finished_at: Optional[str] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    model: Optional[str] = None,
    use_llm: bool = True,
) -> Tuple[str, Optional[str], bool]:
    """
    构建统一报告。返回 (unified_md_path, unified_html_path, used_llm)。
    报告写入 report_path 对应目录下的 UNIFIED_REPORT_MD / UNIFIED_REPORT_HTML。
    api_key/api_base/model 为全局 LLM 配置，兼容 OpenAI 及兼容接口（Minimax、DeepSeek、Claude 等）。
    """
    base_dir = _resolve_report_dir(report_path)
    if not base_dir:
        raise FileNotFoundError("未找到 penetration_test_report.md 所在目录")
    main_md = os.path.join(base_dir, "penetration_test_report.md")
    if not os.path.isfile(main_md):
        raise FileNotFoundError("总报告文件不存在")
    vuln_dir = os.path.join(base_dir, "vulnerabilities")
    main_content = _read_main_report(main_md)
    sections = _split_main_sections(main_content)
    vuln_list = _list_vulnerability_files(vuln_dir)
    vuln_list_with_severity = _get_vuln_list_with_severity(vuln_dir)
    # 封面与元信息
    target_display = (task_target_value or "").strip()
    if target_display.startswith("["):
        try:
            import json
            target_display = json.loads(target_display)
            target_display = ", ".join(str(x) for x in target_display) if isinstance(target_display, list) else str(target_display)
        except Exception:
            pass
    now_display = utc_to_beijing_str(datetime.now(timezone.utc)) or ""
    intro = f"""# 安全渗透测试报告

**报告生成时间：** {now_display}（北京时间）
**测试目标：** {target_display or '-'}
**测试时间范围：** {task_created_at or '-'} 至 {task_finished_at or '-'}
**执行方：** NETOPS

---
"""
    used_llm = False
    if use_llm and api_key:
        for key in ("Executive Summary", "Methodology", "Technical Analysis", "Recommendations"):
            if sections.get(key):
                cn = _translate_with_llm(sections[key], api_key, api_base=api_base, model=model)
                if cn:
                    sections[key] = cn
                    used_llm = True
    elif use_llm and not api_key:
        intro += "\n*（未配置全局 API Key，以下为英文原文。）*\n\n---\n\n"

    # 拼接正文
    body = []
    body.append("## 执行摘要\n\n")
    body.append(sections.get("Executive Summary", "*无*") + "\n\n")
    body.append("## 测试范围与方法论\n\n")
    body.append(sections.get("Methodology", "*无*") + "\n\n")
    body.append("## 漏洞发现总览\n\n")
    body.append("| 序号 | ID | 严重程度 |\n|------|-----|----------|\n")
    for i, (vid, _) in enumerate(vuln_list, 1):
        body.append(f"| {i} | {vid} | - |\n")
    body.append("\n## 漏洞详情\n\n")
    vuln_parsed_list: List[Dict[str, Any]] = []
    for vid, path in vuln_list:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                vuln_content = f.read()
            if use_llm and api_key:
                cn = _translate_with_llm(vuln_content[:5000], api_key, api_base=api_base, model=model)
                if cn:
                    vuln_content = cn
                    used_llm = True
        except Exception as e:
            vuln_content = f"*读取失败: {e}*"
        vuln_parsed_list.append(_parse_vuln_from_content(vuln_content, path))
        body.append("---\n\n")
        body.append(vuln_content)
        body.append("\n\n")
    body.append("## 技术分析总结\n\n")
    body.append(sections.get("Technical Analysis", "*无*") + "\n\n")
    body.append("## 修复与改进建议\n\n")
    body.append(sections.get("Recommendations", "*无*") + "\n\n")
    full_md = intro + "\n".join(body)
    out_md = os.path.join(base_dir, UNIFIED_REPORT_MD)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(full_md)
    out_html = None
    try:
        # 第一部分 HTML：总报告（intro + 四章节，与 MD 一致）
        main_report_md = (
            intro
            + "## 执行摘要\n\n" + (sections.get("Executive Summary") or "*无*") + "\n\n"
            + "## 测试范围与方法论\n\n" + (sections.get("Methodology") or "*无*") + "\n\n"
            + "## 技术分析\n\n" + (sections.get("Technical Analysis") or "*无*") + "\n\n"
            + "## 修复与改进建议\n\n" + (sections.get("Recommendations") or "*无*")
        )
        main_report_html = _markdown_to_html(main_report_md)
        session_id = os.path.basename(base_dir)
        html_full = _build_html_report(
            main_report_html=main_report_html,
            vuln_list_with_severity=vuln_list_with_severity,
            vuln_parsed_list=vuln_parsed_list,
            session_id=session_id,
        )
        out_html = os.path.join(base_dir, UNIFIED_REPORT_HTML)
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(html_full)
    except Exception as e:
        logger.warning("生成 HTML 报告失败: %s", e)
    return (out_md, out_html, used_llm)
