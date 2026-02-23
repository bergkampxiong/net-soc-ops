# -*- coding: utf-8 -*-
"""H3C 网络设备发现：Comware，通过 SSH 执行 display version / display device manuinfo 等采集并解析。"""
import re
import logging
from typing import List, Optional, Tuple

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException

from .base import DiscoveredDevice
from .ip_parser import parse_ip_range

logger = logging.getLogger(__name__)

# netmiko 设备类型：H3C Comware
NETMIKO_DEVICE_TYPE = "hp_comware"

# CMDB 系统类型（与 int_all_db 一致）
SYSTEM_TYPE_NAME = "hp_comware"


def _parse_display_version(text: str, ip: str) -> Optional[DiscoveredDevice]:
    """从 display version 输出解析版本、型号；设备名称由 sysname 或 manuinfo 单独获取。"""
    lines = text.strip().split("\n")
    version = None
    model = None

    for line in lines:
        line_stripped = line.strip()
        # H3C S5130-52C-EI Comware Software, Version 7.1.070, Release 5130-52C-EI
        if "Comware" in line_stripped and "Version" in line_stripped:
            m = re.search(r"[Vv]ersion\s+([^\s,]+)", line_stripped)
            if m:
                v = m.group(1).strip(" ,")
                if v and len(v) <= 50:
                    version = v
            if "H3C" in line_stripped:
                m_model = re.search(r"H3C\s+([A-Z0-9\-]+(?:\s+Comware|\s+uptime|$))", line_stripped)
                if m_model and not model:
                    model = m_model.group(1).replace("Comware", "").replace("uptime", "").strip()
        # H3C S5130-52C-EI uptime is ...
        if "H3C" in line_stripped and "uptime" in line_stripped.lower() and not model:
            m = re.search(r"H3C\s+([A-Z0-9\-]+)\s+uptime", line_stripped, re.IGNORECASE)
            if m:
                model = m.group(1)

    if not model:
        for m in re.finditer(r"\b(S\d{4}[\-\w]*|MSR\d*[\-\w]*|SR\d*[\-\w]*)\b", text, re.IGNORECASE):
            model = m.group(1)
            break

    return DiscoveredDevice(
        ip_address=ip,
        name=ip.replace(".", "-"),
        asset_tag=f"DISC-{ip.replace('.', '-')}",
        serial_number=None,
        device_model=model,
        os_version=version,
        vendor_name="H3C",
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


def _parse_display_device(text: str) -> Optional[str]:
    """
    从 display device 回显取设备型号（Type 列）。
    表格格式示例：
        Slot Type              State    Subslot  Soft Ver             Patch Ver
        1    S6520X-30QC-EI    Master   0        S6520X-6530P02       None
    取第一行数据中的 Type 列，即 S6520X-30QC-EI。
    """
    for line in text.split("\n"):
        line_stripped = line.strip()
        # 数据行：以数字(Slot) + 型号(Type)，如 "1    S6520X-30QC-EI    Master   0 ..."
        m = re.match(r"^\s*\d+\s+([A-Za-z0-9\-]+)\s+", line_stripped)
        if m:
            model = m.group(1).strip()
            # 过滤表头/无效行：型号通常为 S/MSR/SR 等开头且含连字符或足够长
            if model and len(model) >= 4 and re.match(r"^[A-Z][A-Za-z0-9\-]+$", model):
                if "Master" in model or "Standby" in model or "None" in model:
                    continue
                return model[:100]
    return None


def _parse_display_device_manuinfo(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    从 display device manuinfo 取 SN、设备名、型号。
    优先解析 H3C 格式：DEVICE_SERIAL_NUMBER : xxx、DEVICE_MODEL : xxx
    返回 (serial_number, device_name, device_model)。
    """
    serial = None
    device_name = None
    device_model = None
    lines = text.split("\n")
    for line in lines:
        line_stripped = line.strip()
        if "DEVICE_SERIAL_NUMBER" in line_stripped:
            m = re.search(r"DEVICE_SERIAL_NUMBER\s*:\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                serial = m.group(1).strip()
        if "DEVICE_MODEL" in line_stripped:
            m = re.search(r"DEVICE_MODEL\s*:\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                device_model = m.group(1).strip()[:100]
        if re.match(r"^\s*\d+\s+", line_stripped) and not serial:
            parts = re.split(r"\s{2,}", line_stripped)
            if len(parts) >= 3:
                sn_candidate = parts[2].strip()
                if sn_candidate and re.match(r"^[A-Za-z0-9]+$", sn_candidate) and len(sn_candidate) >= 5:
                    serial = sn_candidate
                    break
        if not serial and (
            "ESN:" in line_stripped or "SN:" in line_stripped
            or "Serial Number:" in line_stripped or "Serial-number:" in line_stripped or "BarCode:" in line_stripped
        ):
            m = re.search(r"(?:ESN|SN|Serial\s*Number|Serial-number|BarCode):\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                serial = m.group(1).strip()
        if "Device name:" in line_stripped or "Product name:" in line_stripped:
            m = re.search(r"(?:Device\s*name|Product\s*name):\s*(.+)", line_stripped, re.IGNORECASE)
            if m:
                device_name = m.group(1).strip()[:100]
    return (serial, device_name, device_model)


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


def discover_h3c(
    ip_range: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 30,
    threads: int = 5,
    enable_password: Optional[str] = None,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    对 ip_range 内的 IP 逐个 SSH 连接（H3C Comware），执行 display version、display device manuinfo、
    display current-configuration | include sysname，解析主机名、序列号、型号、版本。
    返回 (成功设备列表, 失败列表 [(ip, reason)])。
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
                    # 优先从 display device 取型号（Type 列，如 S6520X-30QC-EI）
                    try:
                        dev_text = conn.send_command("display device", delay_factor=2)
                        dev_model = _parse_display_device(dev_text)
                        if dev_model:
                            dev.device_model = dev_model[:100]
                            logger.debug("H3C 发现 %s 型号来自 display device: %s", ip, dev_model)
                    except Exception as e:
                        logger.debug("H3C 发现 %s display device 未获取型号: %s", ip, e)
                    try:
                        manu_text = conn.send_command("display device manuinfo", delay_factor=2)
                        sn, manu_name, manu_model = _parse_display_device_manuinfo(manu_text)
                        if sn:
                            dev.serial_number = sn
                            dev.asset_tag = sn[:50] if len(sn) <= 50 else dev.asset_tag
                        if manu_name:
                            dev.name = manu_name[:100]
                        if manu_model and not dev.device_model:
                            dev.device_model = manu_model[:100]
                            logger.debug("H3C 发现 %s 型号来自 display device manuinfo: %s", ip, manu_model)
                        elif dev.device_model:
                            logger.debug("H3C 发现 %s 型号已由 display device 填充: %s", ip, dev.device_model)
                    except Exception as e:
                        logger.debug("H3C 发现 %s manuinfo 未获取: %s", ip, e)
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
            logger.warning("H3C 发现跳过 %s: %s", ip, e)
            failed.append((ip, reason))
        except Exception as e:
            reason = _failure_reason(e)
            logger.warning("H3C 发现失败 %s: %s", ip, e)
            failed.append((ip, reason))
    return results, failed
