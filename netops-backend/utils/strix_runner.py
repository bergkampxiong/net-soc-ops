# Strix CLI 子进程调用：在指定工作目录执行 strix -n --target <目标> [选项]
import os
import subprocess
import uuid
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# 可执行路径：优先环境变量，否则系统 PATH 中的 strix
STRIX_CMD = os.environ.get("STRIX_CLI_PATH", "strix")


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
    os.makedirs(workspace_dir, exist_ok=True)
    name = run_name or f"netops_{uuid.uuid4().hex[:12]}"
    cwd = os.path.join(workspace_dir, name)
    os.makedirs(cwd, exist_ok=True)

    cmd = [STRIX_CMD, "-n", "--non-interactive"]
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
        # 常见输出目录：strix 可能在 cwd 下创建 strix_runs/<name>
        possible_report = os.path.join(cwd, "strix_runs", name)
        if not os.path.isdir(possible_report):
            for d in os.listdir(cwd) if os.path.isdir(cwd) else []:
                if d.startswith("strix"):
                    possible_report = os.path.join(cwd, d)
                    break
        return {
            "success": result.returncode == 0,
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
        logger.exception("Strix CLI not found: %s", STRIX_CMD)
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Strix CLI not found: {STRIX_CMD}. Set STRIX_CLI_PATH or install strix.",
            "run_name": name,
            "report_path": cwd,
        }
