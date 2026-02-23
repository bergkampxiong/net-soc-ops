# -*- coding: utf-8 -*-
"""飞塔(Fortinet)安全设备发现：FortiOS，通过 SSH 执行 get system status 采集并解析。"""
import re
import logging
from typing import List, Optional, Tuple

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException

from .base import DiscoveredDevice
from .ip_parser import parse_ip_range

logger = logging.getLogger(__name__)

# netmiko 设备类型：Fortinet FortiOS
NETMIKO_DEVICE_TYPE = "fortinet_ssh"

# CMDB 系统类型（与 int_all_db 一致）
SYSTEM_TYPE_NAME = "fortinet"


def _parse_get_system_status(text: str, ip: str) -> Optional[DiscoveredDevice]:
    """
    从 get system status 输出解析 Hostname、Serial-Number、Version。
    典型输出：Version: FortiGate-60F v7.0.0,build0123 | Hostname: xxx | Serial-Number: FGxxx
    """
    name = ip.replace(".", "-")
    version = None
    model = None
    serial_number = None

    for line in text.split("\n"):
        line_stripped = line.strip()
        # Hostname: xxx
        m = re.match(r"^Hostname\s*:\s*(.+)", line_stripped, re.IGNORECASE)
        if m:
            name = m.group(1).strip()[:100]
            continue
        # Serial-Number: xxx 或 Serial Number: xxx
        m = re.match(r"^Serial[- ]?Number\s*:\s*(.+)", line_stripped, re.IGNORECASE)
        if m and not serial_number:
            serial_number = m.group(1).strip()[:50]
            continue
        # Version: FortiGate-60F v7.0.0,build0123,... -> model=FortiGate-60F, version=7.0.0
        m = re.match(r"^Version\s*:\s*(.+)", line_stripped, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # 匹配 "FortiGate-60F v7.0.0" 或 "FortiADC-VM v4.4.0,build0468"
            vm = re.match(r"^([A-Za-z0-9\-]+)\s+v([\d.]+)", val)
            if vm:
                model = vm.group(1).strip()[:100]
                version = vm.group(2).strip()[:50]
            else:
                version = val[:50] if not version else version
            continue
        # 兼容小写、等号等
        if "hostname" in line_stripped.lower() and (name == ip.replace(".", "-") or not name):
            m = re.search(r"hostname\s*[=:]\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                name = m.group(1).strip()[:100]
        if "serial" in line_stripped.lower() and not serial_number:
            m = re.search(r"serial[- ]?number\s*[=:]\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                serial_number = m.group(1).strip()[:50]
        if "version" in line_stripped.lower() and ":" in line_stripped and not version:
            m = re.search(r"version\s*[=:]\s*(.+)", line_stripped, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                vm = re.match(r"^([A-Za-z0-9\-]+)\s+v([\d.]+)", val)
                if vm:
                    model = vm.group(1)[:100] if not model else model
                    version = vm.group(2)[:50]
                else:
                    version = val[:50]

    # 型号兜底：FortiGate-xxx、FortiADC、FGVME 等
    if not model:
        for m in re.finditer(r"\b(FortiGate-[A-Z0-9\-]+|FortiADC[^\s,]*|FGVME\d*|FGVM\d*)\b", text, re.IGNORECASE):
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
        vendor_name="Fortinet",
        device_type_name="Firewall",
        system_type_name=SYSTEM_TYPE_NAME,
        raw={"get_system_status": text[:2000]},
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


def discover_fortinet(
    ip_range: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 30,
    threads: int = 5,
    enable_password: Optional[str] = None,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    对 ip_range 内的 IP 逐个 SSH 连接（Fortinet FortiOS），执行 get system status，
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
                status_text = conn.send_command("get system status", delay_factor=2)
                dev = _parse_get_system_status(status_text, ip)
                if dev:
                    logger.debug("Fortinet 发现 %s 型号=%s 版本=%s", ip, dev.device_model, dev.os_version)
                    results.append(dev)
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            reason = _failure_reason(e)
            logger.warning("Fortinet 发现跳过 %s: %s", ip, e)
            failed.append((ip, reason))
        except Exception as e:
            reason = _failure_reason(e)
            logger.warning("Fortinet 发现失败 %s: %s", ip, e)
            failed.append((ip, reason))
    return results, failed
