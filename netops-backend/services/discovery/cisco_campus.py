# -*- coding: utf-8 -*-
"""Cisco 园区网络设备发现：通过 SSH 执行 show version / show inventory 采集并解析。"""
import re
import logging
from typing import List, Optional, Tuple

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException

from .base import DiscoveredDevice
from .ip_parser import parse_ip_range

logger = logging.getLogger(__name__)

# netmiko 设备类型：园区常用 IOS / IOS-XE
NETMIKO_DEVICE_TYPE = "cisco_ios"


def _parse_show_version(text: str, ip: str) -> Optional[DiscoveredDevice]:
    """从 show version 输出解析主机名、版本、型号、序列号、系统类型（IOS/IOS-XE）。"""
    lines = text.strip().split("\n")
    name = ip.replace(".", "-")
    version = None
    model = None
    serial_number = None
    system_type_name = "cisco_ios"  # 默认；若检测到 IOS-XE 则改为 cisco_xe

    # 先判断是否为 IOS-XE（与 cmdb 系统类型 cisco_xe 对应）
    if "IOS XE" in text or "IOS-XE" in text or "XE Software" in text:
        system_type_name = "cisco_xe"

    for line in lines:
        line_stripped = line.strip()
        # 首行常为 hostname
        if re.match(r"^[a-zA-Z0-9\-_]+$", line_stripped) and len(line_stripped) < 50 and "version" not in line_stripped.lower():
            if not name or name == ip.replace(".", "-"):
                name = line_stripped
        # 版本：支持 "System Bootstrap, Version 16.12.2r" 与 "Cisco IOS Software, ... Version 15.2(4)E6"
        if "Version" in line_stripped or "version" in line_stripped:
            m = re.search(r"[Vv]ersion\s+([^\s,]+)", line_stripped)
            if m:
                v = m.group(1).strip(" ,")
                if v and len(v) <= 50 and "." in v:
                    if "Bootstrap" in line_stripped:
                        version = v  # 用户指定：Bootstrap 行版本优先（如 16.12.2r）
                    elif ("Software" in line_stripped or "software" in line_stripped) and version is None:
                        version = v
                    elif version is None:
                        version = v
        if "Processor board ID" in line_stripped:
            m = re.search(r"Processor board ID\s+(\S+)", line_stripped)
            if m:
                serial_number = m.group(1)
        if "cisco" in line_stripped.lower() and ("WS-" in line_stripped or "CISCO" in line_stripped or "C9" in line_stripped):
            parts = line_stripped.split()
            for p in parts:
                if re.match(r"^(WS-C|CISCO|C9\d)", p):
                    model = p
                    break
        if "uptime" in line_stripped.lower() and not model:
            m = re.search(r"^(\S+)\s+uptime", line_stripped, re.IGNORECASE)
            if m:
                name = m.group(1)

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
        system_type_name=system_type_name,
        raw={"show_version": text[:2000]},
    )


def _parse_show_inventory(text: str) -> Optional[str]:
    """从 show inventory 取第一个 Chassis 的 PID 与 SN，用于补充 model 与 serial。"""
    serial = None
    for line in text.split("\n"):
        if "SN:" in line or "Serial Number:" in line:
            m = re.search(r"(?:SN:|Serial Number:)\s*(\S+)", line, re.IGNORECASE)
            if m:
                serial = m.group(1).strip()
                break
    return serial


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


def discover_cisco_campus(
    ip_range: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 30,
    threads: int = 5,
    enable_password: Optional[str] = None,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    对 ip_range 内的 IP 逐个 SSH 连接（Cisco IOS/IOS-XE），执行 show version（及 show inventory），
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
            logger.warning("Cisco 发现跳过 %s: %s", ip, e)
            failed.append((ip, reason))
        except Exception as e:
            reason = _failure_reason(e)
            logger.warning("Cisco 发现失败 %s: %s", ip, e)
            failed.append((ip, reason))
    return results, failed
