# -*- coding: utf-8 -*-
"""Palo Alto 安全设备发现：PAN-OS，通过 SSH 执行 show system info 等采集并解析。"""
import re
import logging
from typing import List, Optional, Tuple

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException

from .base import DiscoveredDevice
from .ip_parser import parse_ip_range

logger = logging.getLogger(__name__)

# netmiko 设备类型：Palo Alto PAN-OS
NETMIKO_DEVICE_TYPE = "paloalto_panos"

# CMDB 系统类型（与 int_all_db 一致）
SYSTEM_TYPE_NAME = "paloalto_panos"


def _parse_show_system_info(text: str, ip: str) -> Optional[DiscoveredDevice]:
    """
    从 show system info 输出解析 hostname、serial、model、version。
    典型输出为 key-value 行，如：hostname: FW01, serial: xxx, model: PA-3220, version: 10.1.0
    """
    name = ip.replace(".", "-")
    version = None
    model = None
    serial_number = None

    for line in text.split("\n"):
        line_stripped = line.strip()
        # key: value 或 key = value
        m = re.match(r"^(hostname|serial|model|version|sw-version)\s*[=:]\s*(.+)", line_stripped, re.IGNORECASE)
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if key == "hostname" and val:
                name = val[:100]
            elif key == "serial" and val and not serial_number:
                serial_number = val[:50]
            elif key == "model" and val and not model:
                model = val[:100]
            elif key in ("version", "sw-version") and val and not version:
                version = val[:50]
            continue
        # 兼容其他常见写法（仅在尚未解析到时尝试）
        if "hostname" in line_stripped.lower() and ":" in line_stripped and (name == ip.replace(".", "-") or not name):
            m = re.search(r"hostname\s*[=:]\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                name = m.group(1).strip()[:100]
        if "serial" in line_stripped.lower() and ":" in line_stripped and not serial_number:
            m = re.search(r"serial\s*[=:]\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                serial_number = m.group(1).strip()[:50]
        if "model" in line_stripped.lower() and ":" in line_stripped and not model:
            m = re.search(r"model\s*[=:]\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                model = m.group(1).strip()[:100]
        if ("version" in line_stripped.lower() or "sw-version" in line_stripped.lower()) and ":" in line_stripped and not version:
            m = re.search(r"(?:sw-)?version\s*[=:]\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                version = m.group(1).strip()[:50]

    # 型号兜底：PA-xxx、PA-VM 等
    if not model:
        for m in re.finditer(r"\b(PA-[A-Z0-9\-]+|VM-50|VM-100)\b", text, re.IGNORECASE):
            model = m.group(1)[:100]
            break

    asset_tag = serial_number if serial_number else f"DISC-{ip.replace('.', '-')}"
    if not asset_tag.replace("-", "").replace(".", "").isalnum():
        asset_tag = f"DISC-{ip.replace('.', '-')}"
    return DiscoveredDevice(
        ip_address=ip,
        name=name[:100] if name else ip,
        asset_tag=asset_tag[:50],
        serial_number=serial_number,
        device_model=model,
        os_version=version,
        vendor_name="Palo Alto",
        device_type_name="Firewall",
        system_type_name=SYSTEM_TYPE_NAME,
        raw={"show_system_info": text[:2000]},
    )


def _failure_reason(e: Exception) -> str:
    """将异常转为前端可展示的简短原因。"""
    if isinstance(e, NetmikoAuthenticationException):
        return "认证失败（请检查用户名、密码）"
    if isinstance(e, NetmikoTimeoutException):
        return "连接超时"
    msg = str(e).strip()
    if len(msg) > 80:
        msg = msg[:77] + "..."
    return msg or "未知错误"


def discover_paloalto(
    ip_range: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 30,
    threads: int = 5,
    enable_password: Optional[str] = None,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    对 ip_range 内的 IP 逐个 SSH 连接（Palo Alto PAN-OS），执行 show system info，
    解析主机名、序列号、型号、版本。返回 (成功设备列表, 失败列表 [(ip, reason)])。
    """
    ip_list = parse_ip_range(ip_range)
    if not ip_list:
        return [], []
    results: List[DiscoveredDevice] = []
    failed: List[Tuple[str, str]] = []
    conn_params = {
        "device_type": NETMIKO_DEVICE_TYPE,
        "username": username,
        "password": password,
        "port": port,
        "conn_timeout": timeout,
        "auth_timeout": timeout,
        "banner_timeout": 15,
    }
    if enable_password:
        conn_params["secret"] = enable_password

    for ip in ip_list:
        try:
            conn_params["host"] = ip
            with ConnectHandler(**conn_params) as conn:
                # PAN-OS 推荐用 show system info 获取 hostname/serial/model/version
                info_text = conn.send_command("show system info", delay_factor=2)
                dev = _parse_show_system_info(info_text, ip)
                if dev:
                    logger.debug("Palo Alto 发现 %s 型号=%s 版本=%s", ip, dev.device_model, dev.os_version)
                    results.append(dev)
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            reason = _failure_reason(e)
            logger.warning("Palo Alto 发现跳过 %s: %s", ip, e)
            failed.append((ip, reason))
        except Exception as e:
            reason = _failure_reason(e)
            logger.warning("Palo Alto 发现失败 %s: %s", ip, e)
            failed.append((ip, reason))
    return results, failed
