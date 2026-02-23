# -*- coding: utf-8 -*-
"""Cisco 数据中心网络设备发现：Nexus NX-OS，通过 SSH 执行 show version / show inventory 采集并解析。"""
import re
import logging
from typing import List, Optional, Tuple

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException

from .base import DiscoveredDevice
from .ip_parser import parse_ip_range

logger = logging.getLogger(__name__)

# netmiko 设备类型：数据中心 Nexus NX-OS
NETMIKO_DEVICE_TYPE = "cisco_nxos"

# CMDB 系统类型与园区区分
SYSTEM_TYPE_NAME = "cisco_nxos"


def _parse_show_version(text: str, ip: str) -> Optional[DiscoveredDevice]:
    """从 NX-OS show version 输出解析主机名、版本、型号、序列号。"""
    lines = text.strip().split("\n")
    name = ip.replace(".", "-")
    version = None
    model = None
    serial_number = None

    for line in lines:
        line_stripped = line.strip()
        # Hostname: xxx 或 Device name: xxx
        if re.match(r"^(?:Hostname|Device name|hostname):\s*(\S+)", line_stripped, re.IGNORECASE):
            m = re.search(r":\s*(\S+)", line_stripped)
            if m:
                name = m.group(1).strip()
        # NXOS: version x.y(z) 或 kickstart_ver_str / system image 行
        if "NXOS:" in line_stripped or "version" in line_stripped.lower():
            m = re.search(r"(?:NXOS:?\s*)?[Vv]ersion\s+([^\s,]+)", line_stripped)
            if not m:
                m = re.search(r"(\d+\.\d+\(\d+\)[^\s,]*)", line_stripped)
            if m:
                v = m.group(1).strip(" ,")
                if v and len(v) <= 50 and ("." in v or "(" in v):
                    if "kickstart" in line_stripped.lower() or "system" in line_stripped.lower() or "NXOS" in line_stripped:
                        version = v
                    elif version is None:
                        version = v
        # Processor Board ID 或 proc_board_id
        if "Processor Board ID" in line_stripped or "proc_board_id" in line_stripped.lower():
            m = re.search(r"(?:Processor Board ID|proc_board_id):?\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                serial_number = m.group(1).strip()
        # 型号：Nexus9000 C9396PX、cisco N9K-C9300、N3K-C3164 等
        if "nexus" in line_stripped.lower() or "N9K-" in line_stripped or "N3K-" in line_stripped or "N7K-" in line_stripped:
            for m in re.finditer(r"(?:Nexus\s*\d*\s*)?(N[379]K-[A-Z0-9-]+|C\d{4}[A-Z]*)", line_stripped, re.IGNORECASE):
                model = m.group(1)
                break
        # 首行若为简短主机名（无空格、无冒号）
        if not name or name == ip.replace(".", "-"):
            if re.match(r"^[a-zA-Z0-9\-_]+$", line_stripped) and len(line_stripped) < 50 and "version" not in line_stripped.lower():
                name = line_stripped

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
        vendor_name="Cisco",
        device_type_name="Switch",
        system_type_name=SYSTEM_TYPE_NAME,
        raw={"show_version": text[:2000]},
    )


def _parse_show_inventory(text: str) -> Optional[str]:
    """从 NX-OS show inventory 取 Chassis 的 SN。"""
    for line in text.split("\n"):
        if "SN:" in line or "Serial Number:" in line or "serial_number" in line.lower():
            m = re.search(r"(?:SN:|Serial Number:|serial_number):\s*(\S+)", line, re.IGNORECASE)
            if m:
                return m.group(1).strip()
    return None


def _failure_reason(e: Exception) -> str:
    """将异常转为前端可展示的简短原因。"""
    if isinstance(e, NetmikoAuthenticationException):
        return "认证失败（请检查用户名、密码或 Enable 密码）"
    if isinstance(e, NetmikoTimeoutException):
        return "连接超时"
    msg = str(e).strip()
    if len(msg) > 80:
        msg = msg[:77] + "..."
    return msg or "未知错误"


def discover_cisco_datacenter(
    ip_range: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 30,
    threads: int = 5,
    enable_password: Optional[str] = None,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    对 ip_range 内的 IP 逐个 SSH 连接（Cisco NX-OS），执行 show version（及 show inventory），
    解析出主机名、序列号、型号、版本。返回 (成功设备列表, 失败列表 [(ip, reason)])。
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
                ver_text = conn.send_command("show version", delay_factor=2)
                dev = _parse_show_version(ver_text, ip)
                if dev:
                    try:
                        inv_text = conn.send_command("show inventory", delay_factor=2)
                        sn = _parse_show_inventory(inv_text)
                        if sn:
                            dev.serial_number = sn
                            dev.asset_tag = sn[:50] if len(sn) <= 50 else dev.asset_tag
                    except Exception:
                        pass
                    results.append(dev)
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            reason = _failure_reason(e)
            logger.warning("Cisco 数据中心发现跳过 %s: %s", ip, e)
            failed.append((ip, reason))
        except Exception as e:
            reason = _failure_reason(e)
            logger.warning("Cisco 数据中心发现失败 %s: %s", ip, e)
            failed.append((ip, reason))
    return results, failed
