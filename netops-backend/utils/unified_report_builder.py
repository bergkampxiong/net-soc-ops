# 统一渗透测试报告构建：读取 Strix 输出，拼接为单一 Markdown，可选 LLM 中文化
import os
import re
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List
import requests

logger = logging.getLogger(__name__)

# 统一报告文件名
UNIFIED_REPORT_MD = "unified_penetration_test_report.md"
UNIFIED_REPORT_HTML = "unified_penetration_test_report.html"


def _resolve_report_dir(report_path: str) -> Optional[str]:
    """解析得到包含 penetration_test_report.md 的目录（含子目录查找）。"""
    if not report_path or not os.path.isdir(report_path):
        return None
    p = os.path.join(report_path, "penetration_test_report.md")
    if os.path.isfile(p):
        return report_path
    for sub in os.listdir(report_path):
        sub_path = os.path.join(report_path, sub)
        if os.path.isdir(sub_path) and os.path.isfile(os.path.join(sub_path, "penetration_test_report.md")):
            return sub_path
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
    if not os.path.isdir(vuln_dir):
        return []
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    items = []
    for f in os.listdir(vuln_dir):
        if not f.endswith(".md"):
            continue
        path = os.path.join(vuln_dir, f)
        if not os.path.isfile(path):
            continue
        # 从文件内容或文件名取 severity（vuln-0001.md -> id）
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
            items.append((severity_order.get(sev, 5), id_, path))
        except Exception:
            items.append((5, id_, path))
    items.sort(key=lambda x: (x[0], x[1]))
    return [(id_, path) for _, id_, path in items]


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
    # 封面与元信息
    target_display = (task_target_value or "").strip()
    if target_display.startswith("["):
        try:
            import json
            target_display = json.loads(target_display)
            target_display = ", ".join(str(x) for x in target_display) if isinstance(target_display, list) else str(target_display)
        except Exception:
            pass
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    intro = f"""# 安全渗透测试报告

**报告生成时间：** {now_utc}
**测试目标：** {target_display or '-'}
**测试时间范围：** {task_created_at or '-'} 至 {task_finished_at or '-'}
**执行方：** Strix + net-soc-ops

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
        import markdown
        html_content = markdown.markdown(full_md, extensions=["extra", "codehilite"])
        html_full = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><title>统一渗透测试报告</title><style>pre{{background:#f5f5f5;padding:12px;overflow:auto;}} table{{border-collapse:collapse;}} th,td{{border:1px solid #ddd;padding:8px;}}</style></head><body>{html_content}</body></html>"""
        out_html = os.path.join(base_dir, UNIFIED_REPORT_HTML)
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(html_full)
    except ImportError:
        pass
    return (out_md, out_html, used_llm)
