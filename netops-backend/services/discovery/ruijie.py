# -*- coding: utf-8 -*-
"""锐捷网络设备发现：Ruijie OS，通过 SSH 执行 show version / show device / show manuinfo 等采集并解析。"""
import re
import logging
from typing import List, Optional, Tuple

from netmiko import ConnectHandler
from netmiko.ssh_exception import NetmikoTimeoutException, NetmikoAuthenticationException

from .base import DiscoveredDevice
from .ip_parser import parse_ip_range

logger = logging.getLogger(__name__)

# netmiko 设备类型：锐捷 OS
NETMIKO_DEVICE_TYPE = "ruijie_os"

# CMDB 系统类型（与 int_all_db 一致）
SYSTEM_TYPE_NAME = "ruijie_os"


def _parse_show_version(text: str, ip: str) -> Optional[DiscoveredDevice]:
    """从 show version 输出解析版本、型号、序列号、主机名。"""
    lines = text.strip().split("\n")
    name = ip.replace(".", "-")
    version = None
    model = None
    serial_number = None

    for line in lines:
        line_stripped = line.strip()
        # RGOS 10.4(3b), Release(123456) 或 Version x.x
        if "RGOS" in line_stripped or "version" in line_stripped.lower():
            m = re.search(r"(?:RGOS\s+)?([Vv]ersion\s+)?([\d.]+(?:\([^)]+\))?[^\s,]*)", line_stripped)
            if m and not version:
                v = m.group(2).strip(" ,")
                if v and len(v) <= 50:
                    version = v[:50]
        # Device model: / Model: / 型号
        if "model" in line_stripped.lower() or "型号" in line_stripped:
            m = re.search(r"(?:Device\s*model|Model|型号)\s*[：:]\s*([A-Za-z0-9\-]+)", line_stripped, re.IGNORECASE)
            if m and not model:
                model = m.group(1).strip()[:100]
        # Serial number: / SN: / 序列号
        if "serial" in line_stripped.lower() or "SN" in line_stripped or "序列号" in line_stripped:
            m = re.search(r"(?:Serial\s*number|SN|序列号)\s*[：:]\s*(\S+)", line_stripped, re.IGNORECASE)
            if m and not serial_number:
                serial_number = m.group(1).strip()
        # Ruijie Networks ... S6520-30QC-EI 或 hostname 行
        if "Ruijie" in line_stripped and not model:
            for m in re.finditer(r"\b([A-Z][A-Za-z0-9\-]{4,}(?:-[A-Z0-9\-]+)*)\b", line_stripped):
                s = m.group(1)
                if re.match(r"^S\d+", s, re.IGNORECASE) or re.match(r"^NBS|RG-", s, re.IGNORECASE):
                    model = s[:100]
                    break
        # 首行简短主机名
        if not name or name == ip.replace(".", "-"):
            if re.match(r"^[a-zA-Z0-9\-_]+$", line_stripped) and len(line_stripped) < 50 and "version" not in line_stripped.lower():
                name = line_stripped

    if not model:
        for m in re.finditer(r"\b(S\d{3,}[A-Z0-9\-]*|NBS\d*[A-Z0-9\-]*|RG-[A-Z0-9\-]+)\b", text, re.IGNORECASE):
            model = m.group(1)
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
        vendor_name="Ruijie",
        device_type_name="Switch",
        system_type_name=SYSTEM_TYPE_NAME,
        raw={"show_version": text[:2000]},
    )


def _parse_show_device(text: str) -> Optional[str]:
    """
    从 show device / display device 回显取设备型号（Type 列）。
    表格格式与 H3C 类似：Slot Type ... State ... / 1  S6520X-30QC-EI  Master ...
    """
    for line in text.split("\n"):
        line_stripped = line.strip()
        m = re.match(r"^\s*\d+\s+([A-Za-z0-9\-]+)\s+", line_stripped)
        if m:
            model = m.group(1).strip()
            if model and len(model) >= 4 and re.match(r"^[A-Z][A-Za-z0-9\-]+$", model):
                if model.upper() in ("MASTER", "STANDBY", "NONE", "PRESENT", "NORMAL"):
                    continue
                return model[:100]
    return None


def _parse_show_manuinfo(text: str) -> Tuple[Optional[str], Optional[str]]:
    """从 show manuinfo 取序列号、型号。返回 (serial_number, device_model)。"""
    serial = None
    device_model = None
    for line in text.split("\n"):
        line_stripped = line.strip()
        if "serial" in line_stripped.lower() or "SN" in line_stripped or "序列号" in line_stripped:
            m = re.search(r"(?:Serial|SN|序列号)\s*[：:]\s*(\S+)", line_stripped, re.IGNORECASE)
            if m:
                serial = m.group(1).strip()
        if "model" in line_stripped.lower() or "型号" in line_stripped:
            m = re.search(r"(?:Model|型号)\s*[：:]\s*([A-Za-z0-9\-]+)", line_stripped, re.IGNORECASE)
            if m:
                device_model = m.group(1).strip()[:100]
    return (serial, device_model)


def _parse_hostname(text: str) -> Optional[str]:
    """从 show running-config | include hostname 或 show run 中解析主机名。"""
    for line in text.split("\n"):
        line = line.strip()
        m = re.match(r"hostname\s+(.+)", line, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:100]
    return None


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


def discover_ruijie(
    ip_range: str,
    username: str,
    password: str,
    port: int = 22,
    timeout: int = 30,
    threads: int = 5,
    enable_password: Optional[str] = None,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    对 ip_range 内的 IP 逐个 SSH 连接（锐捷 Ruijie OS），执行 show version、show device、show manuinfo，
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
                ver_text = conn.send_command("show version", delay_factor=2)
                dev = _parse_show_version(ver_text, ip)
                if dev:
                    # 优先从 show device 取型号（Type 列）
                    try:
                        dev_text = conn.send_command("show device", delay_factor=2)
                        dev_model = _parse_show_device(dev_text)
                        if dev_model:
                            dev.device_model = dev_model[:100]
                            logger.debug("锐捷发现 %s 型号来自 show device: %s", ip, dev_model)
                    except Exception as e:
                        logger.debug("锐捷发现 %s show device 未获取型号: %s", ip, e)
                    try:
                        manu_text = conn.send_command("show manuinfo", delay_factor=2)
                        sn, manu_model = _parse_show_manuinfo(manu_text)
                        if sn:
                            dev.serial_number = sn
                            dev.asset_tag = sn[:50] if len(sn) <= 50 else dev.asset_tag
                        if manu_model and not dev.device_model:
                            dev.device_model = manu_model[:100]
                            logger.debug("锐捷发现 %s 型号来自 show manuinfo: %s", ip, manu_model)
                        elif dev.device_model:
                            logger.debug("锐捷发现 %s 型号已由 show device 填充: %s", ip, dev.device_model)
                    except Exception as e:
                        logger.debug("锐捷发现 %s show manuinfo 未获取: %s", ip, e)
                    try:
                        run_text = conn.send_command("show running-config | include hostname", delay_factor=2)
                        name_from_cfg = _parse_hostname(run_text)
                        if name_from_cfg:
                            dev.name = name_from_cfg[:100]
                    except Exception:
                        pass
                    if not dev.serial_number:
                        dev.asset_tag = f"DISC-{ip.replace('.', '-')}"
                    results.append(dev)
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            reason = _failure_reason(e)
            logger.warning("锐捷发现跳过 %s: %s", ip, e)
            failed.append((ip, reason))
        except Exception as e:
            reason = _failure_reason(e)
            logger.warning("锐捷发现失败 %s: %s", ip, e)
            failed.append((ip, reason))
    return results, failed
