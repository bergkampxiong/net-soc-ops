# Strix CLI 子进程调用：在指定工作目录执行 strix -n --target <目标> [选项]
# 安装方式：执行 scripts/install-strix.sh，将 Strix 二进制安装到 netops-backend/strix/bin/，不使用 .venv。
# 或设置 STRIX_CLI_PATH 指向任意可执行的 strix 二进制路径。
import os
import re
import subprocess
import threading
import uuid
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# 安装目录：与 install-strix.sh 一致，优先 /app/net-soc-ops/netops-backend/strix/bin，否则项目内 netops-backend/strix/bin
def _strix_install_bin() -> str:
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    local_bin = os.path.join(backend_root, "strix", "bin", "strix")
    if os.path.isfile(local_bin) and os.access(local_bin, os.X_OK):
        return local_bin
    app_bin = "/app/net-soc-ops/netops-backend/strix/bin/strix"
    if os.path.isfile(app_bin) and os.access(app_bin, os.X_OK):
        return app_bin
    return ""


# 解析 Strix CLI 路径：1) 环境变量 STRIX_CLI_PATH（若存在且可执行）2) 安装目录 bin/strix（install-strix.sh）3) 系统 PATH 的 strix
def _resolve_strix_cmd() -> str:
    env_path = os.environ.get("STRIX_CLI_PATH", "").strip()
    if env_path and (os.path.isabs(env_path) or os.sep in env_path) and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
        return env_path
    install_bin = _strix_install_bin()
    if install_bin:
        return install_bin
    return env_path if env_path else "strix"


def check_strix_activation() -> Tuple[bool, bool, str, Optional[str]]:
    """
    检查 Strix 是否已安装且 CLI 可执行（不依赖源码或 .venv）。
    返回 (安装目录存在, CLI 可执行, 说明信息, 检测到的 CLI 路径或 None)。
    """
    install_bin = _strix_install_bin()
    strix_cmd = _resolve_strix_cmd()
    source_ok = bool(install_bin) or (os.environ.get("STRIX_CLI_PATH", "").strip() and os.path.isfile(strix_cmd))

    if not strix_cmd or strix_cmd == "strix":
        if not source_ok:
            return False, False, "Strix 未安装。请执行 scripts/install-strix.sh，或设置 STRIX_CLI_PATH 指向 strix 二进制。", None
    elif not os.path.isfile(strix_cmd):
        return True, False, f"STRIX_CLI_PATH 指向的路径不存在或不可执行: {strix_cmd}", strix_cmd

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
    except subprocess.TimeoutExpired:
        cli_ok = False
    except Exception as e:
        logger.warning("Strix CLI 检查异常: %s", e)
        cli_ok = False

    if not cli_ok:
        return source_ok, False, "Strix 已安装但 CLI 不可执行（请重新运行 scripts/install-strix.sh 或检查 STRIX_CLI_PATH）", strix_cmd
    return (source_ok or True), True, "Strix 已就绪，CLI 可正常调用（未使用 .venv）", strix_cmd


# Strix 沙箱依赖 Docker，子进程需能访问 Docker（DOCKER_HOST 或默认 socket）
_DOCKER_ENV_KEYS = ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG", "DOCKER_CERT_PATH", "DOCKER_TLS_VERIFY")


def get_strix_env_from_config(config_kv: Dict[str, str]) -> Dict[str, str]:
    """从配置键值构建 Strix 所需环境变量（含当前进程的 DOCKER_*，供沙箱使用）。"""
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


def _ensure_str_for_json(v: Any) -> str:
    """保证可安全写入 JSON 的字符串，避免 bytes 导致 Object of type bytes is not JSON serializable。"""
    if v is None:
        return ""
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return str(v)


def _strip_ansi(text: str) -> str:
    """去掉 PTY 输出的 ANSI 转义序列（颜色等），便于正则匹配与展示。"""
    if not text or not isinstance(text, str):
        return text
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def _parse_stdout_stats(text: str) -> Dict[str, Any]:
    """从输出文本中解析 Model、Vulnerabilities、Agents、Tools；解析前先去除 ANSI 码。"""
    if not text or not isinstance(text, str):
        return {}
    text = _strip_ansi(text)
    stats: Dict[str, Any] = {}
    m = re.search(r"Model\s+(\S+)", text)
    if m:
        stats["model"] = _strip_ansi(m.group(1)).strip()
    # Vulnerabilities：取最后一次数字（如 Total: 6）；Agents/Tools：取关键词后第一个数字，多行时取最后一次出现
    m = re.search(r"Vulnerabilities.*(\d+)", text)
    if m:
        stats["vulnerabilities"] = int(m.group(1))
    agents_m = re.findall(r"Agents\s+[\s·]*(\d+)", text)
    if agents_m:
        stats["agents"] = int(agents_m[-1])
    tools_m = re.findall(r"Tools\s+[\s·]*(\d+)", text)
    if tools_m:
        stats["tools"] = int(tools_m[-1])
    return stats


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
    process_holder: Optional[Dict[Any, Any]] = None,
    task_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    同步执行 Strix 扫描。使用 Popen 实时写 progress 文件，便于运行中读取 Agents/Tools。
    若 process_holder 与 task_id 均提供，则 Popen 启动后写入 process_holder[task_id]=proc，供外部 cancel 杀进程。
    返回 dict: success, returncode, stdout, stderr, run_name, report_path。
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
    for k in _DOCKER_ENV_KEYS:
        if k in os.environ and os.environ[k]:
            env[k] = os.environ[k]
    progress_file = os.path.join(cwd, "progress.json")
    try:
        run_user = os.environ.get("USER", os.environ.get("LOGNAME", "")) or str(os.getuid()) if hasattr(os, "getuid") else ""
        logger.info("Strix 子进程即将执行，运行用户: %s，cwd: %s", run_user or "(未知)", cwd)
    except Exception:
        pass

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []
    stdout_lock = threading.Lock()
    stderr_lock = threading.Lock()
    latest_stats: Dict[str, int] = {}

    def read_stdout(pipe):
        nonlocal latest_stats
        for line in iter(pipe.readline, ""):
            with stdout_lock:
                stdout_lines.append(line)
            buf = "".join(stdout_lines)
            stats = _parse_stdout_stats(buf)
            if stats:
                latest_stats.update(stats)
                try:
                    with open(progress_file, "w", encoding="utf-8") as f:
                        json.dump(latest_stats, f, ensure_ascii=False)
                except OSError:
                    pass
        pipe.close()

    def read_stderr(pipe):
        for line in iter(pipe.readline, ""):
            with stderr_lock:
                stderr_lines.append(line)
        pipe.close()

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=os.name != "nt",
        )
        if process_holder is not None and task_id is not None:
            process_holder[task_id] = proc
        t_out = threading.Thread(target=read_stdout, args=(proc.stdout,))
        t_err = threading.Thread(target=read_stderr, args=(proc.stderr,))
        t_out.daemon = True
        t_err.daemon = True
        t_out.start()
        t_err.start()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            t_out.join(timeout=2)
            t_err.join(timeout=2)
            with stdout_lock:
                full_stdout = "".join(stdout_lines)
            with stderr_lock:
                full_stderr = "".join(stderr_lines)
            full_stdout = _ensure_str_for_json(full_stdout)
            full_stderr = _ensure_str_for_json(full_stderr or "Strix run timeout")
            return {
                "success": False,
                "returncode": -1,
                "stdout": full_stdout,
                "stderr": full_stderr,
                "run_name": name,
                "report_path": cwd,
            }
        t_out.join(timeout=5)
        t_err.join(timeout=5)
        with stdout_lock:
            full_stdout = "".join(stdout_lines)
        with stderr_lock:
            full_stderr = "".join(stderr_lines)
        full_stdout = _ensure_str_for_json(full_stdout)
        full_stderr = _ensure_str_for_json(full_stderr)
        returncode = proc.returncode
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
        success = returncode in (0, 2)
        return {
            "success": success,
            "returncode": returncode or 0,
            "stdout": full_stdout,
            "stderr": full_stderr,
            "run_name": name,
            "report_path": possible_report if os.path.isdir(possible_report) else cwd,
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
