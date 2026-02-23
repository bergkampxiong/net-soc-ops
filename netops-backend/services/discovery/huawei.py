# -*- coding: utf-8 -*-
"""华为网络设备发现：VRP，通过 SSH 执行 display version / display device manufacture-info 等采集并解析。"""
import re
import logging
from typing import List, Optional, Tuple

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException

from .base import DiscoveredDevice
from .ip_parser import parse_ip_range

logger = logging.getLogger(__name__)

# netmiko 设备类型：华为 VRP
NETMIKO_DEVICE_TYPE = "huawei"

# CMDB 系统类型（与 int_all_db 一致）
SYSTEM_TYPE_NAME = "huawei_vrpv8"

# 资产标签与 SN 使用此命令（用户指定）
DISPLAY_DEVICE_MANUFACTURE_INFO_CMD = "display device manufacture-info"


def _parse_display_version(text: str, ip: str) -> Optional[DiscoveredDevice]:
    """从 display version 输出解析版本、型号；设备名称由 display current-configuration | include sysname 单独获取。"""
    lines = text.strip().split("\n")
    version = None
    model = None

    for line in lines:
        line_stripped = line.strip()
        # Software      Version   : VRP (R) Software, Version 5.170 (V200R011C10SPC600)
        if "Software" in line_stripped and "Version" in line_stripped and ("VRP" in line_stripped or "version" in line_stripped.lower()):
            m = re.search(r"Version\s*:\s*(?:VRP\s*\([^)]+\)\s*Software,?\s*Version\s+)?([^\n]+)", line_stripped, re.IGNORECASE)
            if m:
                v = m.group(1).strip(" ,")
                if v and len(v) <= 80:
                    version = v[:50]
            if not version:
                m = re.search(r"Version\s+([\d.]+(?:\s*\([^)]+\))?)", line_stripped)
                if m:
                    version = m.group(1).strip()[:50]
            # 型号：括号内 V200R011C10SPC600 前的型号或 (S5700 V200R022C10)
            m_model = re.search(r"\(([A-Z0-9\-]+)\s+V[\dR]+[C\d]*\)", line_stripped)
            if m_model and not model:
                model = m_model.group(1)
        # Huawei AR6300 Router uptime / Huawei S5700 uptime
        if "Huawei" in line_stripped and "uptime" in line_stripped.lower():
            m = re.search(r"Huawei\s+([A-Z0-9\-]+)\s+(?:Router|Switch|uptime)", line_stripped, re.IGNORECASE)
            if m and not model:
                model = m.group(1)

    if not model:
        for m in re.finditer(r"\b(AR\d{3,4}|S\d{3,4}|CE\d{4}|NE\d{2,4})\b", text, re.IGNORECASE):
            model = m.group(1)
            break

    # 设备名称占位，由调用方用 sysname 覆盖
    return DiscoveredDevice(
        ip_address=ip,
        name=ip.replace(".", "-"),
        asset_tag=f"DISC-{ip.replace('.', '-')}",
        serial_number=None,
        device_model=model,
        os_version=version,
        vendor_name="Huawei",
        device_type_name="Switch",
        system_type_name=SYSTEM_TYPE_NAME,
        raw={"display_version": text[:2000]},
    )


def _parse_sysname(text: str) -> Optional[str]:
    """从 display current-configuration | include sysname 输出解析主机名。"""
    for line in text.split("\n"):
        line = line.strip()
        m = re.match(r"sysname\s+(.+)", line, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:100]
    return None


def _parse_display_device_manufacture_info(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    从 display device manufacture-info 取 SN（及可选设备名）。
    输出为表格时格式示例：
      Slot  Sub  Serial-number          Manu-date
      - - - - - - - - - - - - - - - - - - - - - -
      0     -    2102359562DMK7000733   2019-07-28
    返回 (serial_number, device_name)；设备名若输出中无则为 None。
    """
    serial = None
    device_name = None
    lines = text.split("\n")
    for line in lines:
        line_stripped = line.strip()
        # 表格式：以数字开头（Slot）的行，第三列为 Serial-number
        if re.match(r"^\s*\d+\s+", line_stripped):
            parts = re.split(r"\s{2,}", line_stripped)
            if len(parts) >= 3:
                sn_candidate = parts[2].strip()
                if sn_candidate and re.match(r"^[A-Za-z0-9]+$", sn_candidate) and len(sn_candidate) >= 5:
                    serial = sn_candidate
                    break
        # 键值对格式：ESN: / SN: / Serial Number: 等
        if not serial and (
            "ESN:" in line_stripped or "SN:" in line_stripped
            or "Serial Number:" in line_stripped or "BarCode:" in line_stripped or "Serial number:" in line_stripped
        ):
            m = re.search(r"(?:ESN|SN|Serial\s*Number|BarCode):\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                serial = m.group(1).strip()
        if "Device name:" in line_stripped or "Product name:" in line_stripped:
            m = re.search(r"(?:Device\s*name|Product\s*name):\s*(.+)", line_stripped, re.IGNORECASE)
            if m:
                device_name = m.group(1).strip()[:100]
    return (serial, device_name)


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


def discover_huawei(
    ip_range: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 30,
    threads: int = 5,
    enable_password: Optional[str] = None,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    对 ip_range 内的 IP 逐个 SSH 连接（华为 VRP），执行 display version（及 display device manuinfo），
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
                ver_text = conn.send_command("display version", delay_factor=2)
                dev = _parse_display_version(ver_text, ip)
                if dev:
                    try:
                        manu_text = conn.send_command(DISPLAY_DEVICE_MANUFACTURE_INFO_CMD, delay_factor=2)
                        sn, manu_name = _parse_display_device_manufacture_info(manu_text)
                        if sn:
                            dev.serial_number = sn
                            dev.asset_tag = sn[:50] if len(sn) <= 50 else dev.asset_tag
                        if manu_name:
                            dev.name = manu_name[:100]
                    except Exception:
                        pass
                    try:
                        sysname_text = conn.send_command("display current-configuration | include sysname", delay_factor=2)
                        name_from_sysname = _parse_sysname(sysname_text)
                        if name_from_sysname:
                            dev.name = name_from_sysname[:100]
                    except Exception:
                        pass
                    if not dev.serial_number:
                        dev.asset_tag = f"DISC-{ip.replace('.', '-')}"
                    results.append(dev)
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            reason = _failure_reason(e)
            logger.warning("华为发现跳过 %s: %s", ip, e)
            failed.append((ip, reason))
        except Exception as e:
            reason = _failure_reason(e)
            logger.warning("华为发现失败 %s: %s", ip, e)
            failed.append((ip, reason))
    return results, failed
