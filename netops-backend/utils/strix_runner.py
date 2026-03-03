# Strix CLI 子进程调用：在指定工作目录执行 strix -n --target <目标> [选项]
# 推荐激活方式（任务执行 + 报告读取/统一报告均适用）：
#   在 netops-backend/strix 目录执行 poetry install，netops 会自动使用 .venv/bin/strix，无需配置环境变量。
#   或设置 STRIX_CLI_PATH 指向任意可执行的 strix 二进制/脚本路径。
import os
import subprocess
import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# 解析 Strix CLI 路径：1) 环境变量 STRIX_CLI_PATH（若为绝对路径且存在）2) 项目内 .venv/bin/strix（或指向可访问目标的 symlink）3) 系统 PATH 的 strix
def _resolve_strix_cmd() -> str:
    env_path = os.environ.get("STRIX_CLI_PATH", "").strip()
    if env_path and (os.path.isabs(env_path) or os.sep in env_path) and os.path.isfile(env_path):
        return env_path
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    poetry_strix = os.path.join(backend_root, "strix", ".venv", "bin", "strix")
    if os.path.lexists(poetry_strix):  # 存在（含断开的 symlink）
        try:
            real = os.path.realpath(poetry_strix)
            if os.path.isfile(real) or (os.path.isfile(poetry_strix) and not os.path.islink(poetry_strix)):
                return real if os.path.isfile(real) else poetry_strix
        except OSError:
            pass
        if os.path.isfile(poetry_strix):
            return poetry_strix
    return env_path if env_path else "strix"


# 每次调用时解析 CLI 路径，避免后端先启动、后执行 activate-strix.sh 时仍用旧结果（无需重启后端）


def check_strix_activation() -> Tuple[bool, bool, str, Optional[str]]:
    """
    检查 Strix 是否已激活（源码存在且 CLI 可执行）。
    返回 (源码目录存在, CLI 可执行, 说明信息, 检测到的 CLI 路径或 None)。
    """
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    strix_dir = os.path.join(backend_root, "strix")
    pyproject = os.path.join(strix_dir, "pyproject.toml")
    main_py = os.path.join(strix_dir, "strix", "interface", "main.py")

    source_ok = os.path.isdir(strix_dir) and os.path.isfile(pyproject) and os.path.isfile(main_py)
    if not source_ok:
        return False, False, "Strix 源码目录缺失或结构不完整（需 strix/pyproject.toml 与 strix/strix/interface/main.py）", None

    cli_path = os.environ.get("STRIX_CLI_PATH") or "strix"
    if os.path.isabs(cli_path) or os.sep in cli_path:
        if not os.path.isfile(cli_path):
            return True, False, f"STRIX_CLI_PATH 指向的路径不存在: {cli_path}", cli_path

    strix_cmd = _resolve_strix_cmd()
    try:
        result = subprocess.run(
            [strix_cmd, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(__file__),
        )
        cli_ok = result.returncode == 0 or (result.stdout or result.stderr or "").strip() != ""
    except FileNotFoundError:
        cli_ok = False
        result = None
    except subprocess.TimeoutExpired:
        cli_ok = False
        result = None
    except Exception as e:
        logger.warning("Strix CLI 检查异常: %s", e)
        cli_ok = False
        result = None

    if not cli_ok:
        return True, False, "Strix 源码存在，但 CLI 未安装或不可执行（请在 netops-backend/strix 目录下执行 poetry install 并确保 strix 在 PATH，或设置 STRIX_CLI_PATH）", strix_cmd

    return True, True, "Strix 已激活，CLI 可正常调用", strix_cmd


def get_strix_env_from_config(config_kv: Dict[str, str]) -> Dict[str, str]:
    """从配置键值构建 Strix 所需环境变量。"""
    env = os.environ.copy()
    key_map = {
        "STRIX_LLM": "STRIX_LLM",
        "LLM_API_KEY": "LLM_API_KEY",
        "LLM_API_BASE": "LLM_API_BASE",
        "PERPLEXITY_API_KEY": "PERPLEXITY_API_KEY",
        "STRIX_REASONING_EFFORT": "STRIX_REASONING_EFFORT",
    }
    for k, v in (config_kv or {}).items():
        if k in key_map and v:
            env[key_map[k]] = str(v)
    return env


def test_llm_config(config_kv: Optional[Dict[str, str]]) -> Tuple[bool, str]:
    """
    使用当前配置的 LLM API Key/Base/Model 发起一次最小 chat 请求，验证是否可用。
    返回 (成功与否, 说明信息)。
    """
    if not config_kv:
        return False, "未配置 LLM：请先配置 STRIX_LLM 与 LLM_API_KEY"
    model = (config_kv.get("STRIX_LLM") or "").strip()
    api_key = (config_kv.get("LLM_API_KEY") or "").strip()
    api_base = (config_kv.get("LLM_API_BASE") or "").strip()
    if not model:
        return False, "未配置 STRIX_LLM（模型名）"
    if not api_key:
        return False, "未配置 LLM_API_KEY"
    if not httpx:
        return False, "缺少 httpx 依赖，无法发起测试请求"
    # OpenAI 兼容：POST {base}/chat/completions
    base_url = (api_base or "https://api.openai.com/v1").rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # OpenAI 官方要求 model 为短名（如 gpt-4o）；部分代理接受 openai/gpt-4o
    model_in_request = model.split("/")[-1] if "/" in model else model
    payload = {
        "model": model_in_request,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 5,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        return False, "请求超时，请检查网络或 LLM_API_BASE 是否可达"
    except Exception as e:
        return False, f"请求异常: {e!s}"
    if resp.status_code == 200:
        return True, "LLM API 连接正常"
    try:
        err_body = resp.json()
        err_msg = err_body.get("error", {}).get("message") or err_body.get("message") or resp.text[:200]
    except Exception:
        err_msg = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
    return False, f"API 返回错误 ({resp.status_code}): {err_msg}"


def run_strix_sync(
    target: str,
    targets: Optional[List[str]] = None,
    scan_mode: str = "deep",
    instruction: Optional[str] = None,
    instruction_file: Optional[str] = None,
    workspace_dir: str = "",
    run_name: Optional[str] = None,
    env_override: Optional[Dict[str, str]] = None,
    timeout: int = 3600,
) -> Dict[str, Any]:
    """
    同步执行 Strix 扫描。返回 dict: success, returncode, stdout, stderr, run_name, report_path。
    """
    if not workspace_dir:
        workspace_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "data", "strix_workspace")
    try:
        os.makedirs(workspace_dir, exist_ok=True)
    except OSError as e:
        if e.errno == 13:  # Permission denied
            raise PermissionError(
                f"无法创建 Strix 工作目录 {workspace_dir}，请将 netops-backend/data 属主改为运行后端的用户，例如: "
                "sudo chown -R $(whoami) netops-backend/data"
            ) from e
        raise
    name = run_name or f"netops_{uuid.uuid4().hex[:12]}"
    cwd = os.path.join(workspace_dir, name)
    try:
        os.makedirs(cwd, exist_ok=True)
    except OSError as e:
        if e.errno == 13:
            raise PermissionError(
                f"无法创建任务目录 {cwd}，请将 netops-backend/data 属主改为运行后端的用户，例如: "
                "sudo chown -R $(whoami) netops-backend/data"
            ) from e
        raise

    strix_cmd = _resolve_strix_cmd()
    cmd = [strix_cmd, "-n", "--non-interactive"]
    # 目标：多目标用多个 -t
    if targets:
        for t in targets:
            cmd.extend(["--target", t])
    else:
        cmd.extend(["--target", target])
    cmd.extend(["--scan-mode", scan_mode])
    if instruction:
        cmd.extend(["--instruction", instruction])
    if instruction_file:
        cmd.extend(["--instruction-file", instruction_file])

    env = env_override or os.environ.copy()
    report_path = os.path.join(cwd, "strix_runs")  # Strix 默认在 cwd 下生成 strix_runs/<run_name>

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        # Strix 实际输出在 strix_runs 下，子目录名常为基于目标的 run_name（如 172-18-40-99-8080_e44c），未必等于 name
        strix_runs_dir = os.path.join(cwd, "strix_runs")
        possible_report = os.path.join(strix_runs_dir, name)
        if not os.path.isdir(possible_report) and os.path.isdir(strix_runs_dir):
            for sub in sorted(os.listdir(strix_runs_dir)):
                sub_path = os.path.join(strix_runs_dir, sub)
                if not os.path.isdir(sub_path):
                    continue
                if any(f.endswith(".html") or f == "penetration_test_report.md" for f in os.listdir(sub_path)):
                    possible_report = sub_path
                    break
            else:
                possible_report = strix_runs_dir
        if not os.path.isdir(possible_report):
            for d in os.listdir(cwd) if os.path.isdir(cwd) else []:
                if d.startswith("strix"):
                    possible_report = os.path.join(cwd, d)
                    break
            else:
                possible_report = cwd
        # Strix 约定：0=正常结束，2=发现漏洞后结束（main.py 中 non_interactive 且 vulnerability_reports 时 sys.exit(2)），均视为扫描成功
        success = result.returncode in (0, 2)
        return {
            "success": success,
            "returncode": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "run_name": name,
            "report_path": possible_report if os.path.isdir(possible_report) else cwd,
        }
    except subprocess.TimeoutExpired as e:
        logger.exception("Strix timeout")
        return {
            "success": False,
            "returncode": -1,
            "stdout": getattr(e, "output", "") or "",
            "stderr": "Strix run timeout",
            "run_name": name,
            "report_path": cwd,
        }
    except FileNotFoundError:
        logger.exception("Strix CLI not found: %s", strix_cmd)
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Strix CLI not found: {strix_cmd}. Set STRIX_CLI_PATH or install strix.",
            "run_name": name,
            "report_path": cwd,
        }
