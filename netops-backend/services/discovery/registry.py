# -*- coding: utf-8 -*-
"""
发现类型与执行函数的注册表，便于后续扩展 Cisco 数据中心、华为、H3C 等。
当前仅实现 cisco-campus；其他类型在测试通过后按路线图逐步开发。
"""
import logging
from typing import List, Optional, Callable, Any, Tuple

from .base import DiscoveredDevice
from .cisco_campus import discover_cisco_campus
from .cisco_datacenter import discover_cisco_datacenter
from .huawei import discover_huawei
from .h3c import discover_h3c
from .ruijie import discover_ruijie
from .paloalto import discover_paloalto
from .fortinet import discover_fortinet
from .vmware import discover_vmware
from .aws import discover_aws
from .aliyun import discover_aliyun

logger = logging.getLogger(__name__)

# 返回 (成功设备列表, 失败列表 [(ip, reason)])
DiscoveryResult = Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]
DiscoveryRunner = Callable[[dict], DiscoveryResult]


def _run_cisco_campus(params: dict) -> DiscoveryResult:
    return discover_cisco_campus(
        ip_range=params["ip_range"],
        username=params["username"],
        password=params["password"],
        port=params.get("port", 22),
        timeout=params.get("timeout", 30),
        threads=params.get("threads", 5),
        enable_password=params.get("enable_password"),
    )


def _run_cisco_datacenter(params: dict) -> DiscoveryResult:
    return discover_cisco_datacenter(
        ip_range=params["ip_range"],
        username=params["username"],
        password=params["password"],
        port=params.get("port", 22),
        timeout=params.get("timeout", 30),
        threads=params.get("threads", 5),
        enable_password=params.get("enable_password"),
    )


def _run_huawei(params: dict) -> DiscoveryResult:
    return discover_huawei(
        ip_range=params["ip_range"],
        username=params["username"],
        password=params["password"],
        port=params.get("port", 22),
        timeout=params.get("timeout", 30),
        threads=params.get("threads", 5),
        enable_password=params.get("enable_password"),
    )


def _run_h3c(params: dict) -> DiscoveryResult:
    return discover_h3c(
        ip_range=params["ip_range"],
        username=params["username"],
        password=params["password"],
        port=params.get("port", 22),
        timeout=params.get("timeout", 30),
        threads=params.get("threads", 5),
        enable_password=params.get("enable_password"),
    )


def _run_ruijie(params: dict) -> DiscoveryResult:
    return discover_ruijie(
        ip_range=params["ip_range"],
        username=params["username"],
        password=params["password"],
        port=params.get("port", 22),
        timeout=params.get("timeout", 30),
        threads=params.get("threads", 5),
        enable_password=params.get("enable_password"),
    )


def _run_paloalto(params: dict) -> DiscoveryResult:
    return discover_paloalto(
        ip_range=params["ip_range"],
        username=params["username"],
        password=params["password"],
        port=params.get("port", 22),
        timeout=params.get("timeout", 30),
        threads=params.get("threads", 5),
        enable_password=params.get("enable_password"),
    )


def _run_fortinet(params: dict) -> DiscoveryResult:
    return discover_fortinet(
        ip_range=params["ip_range"],
        username=params["username"],
        password=params["password"],
        port=params.get("port", 22),
        timeout=params.get("timeout", 30),
        threads=params.get("threads", 5),
        enable_password=params.get("enable_password"),
    )


def _run_vmware(params: dict) -> DiscoveryResult:
    # VMware 使用 ip_range 作为 vCenter/ESXi 主机地址，端口默认 443
    return discover_vmware(
        host=params["ip_range"].strip(),
        username=params["username"],
        password=params["password"],
        port=params.get("port", 443),
        timeout=params.get("timeout"),
        threads=params.get("threads"),
        enable_password=params.get("enable_password"),
    )


def _run_aws(params: dict) -> DiscoveryResult:
    return discover_aws(
        access_key=params["access_key"],
        secret_key=params["secret_key"],
        region=params["region"],
    )


def _run_aliyun(params: dict) -> DiscoveryResult:
    return discover_aliyun(
        access_key=params["access_key"],
        secret_key=params["secret_key"],
        region=params["region"],
    )


# 已实现的发现类型
DISCOVERY_RUNNERS: dict[str, DiscoveryRunner] = {
    "cisco-campus": _run_cisco_campus,
    "cisco-datacenter": _run_cisco_datacenter,
    "huawei": _run_huawei,
    "h3c": _run_h3c,
    "ruijie": _run_ruijie,
    "paloalto": _run_paloalto,
    "fortinet": _run_fortinet,
    "vmware": _run_vmware,
    "aws": _run_aws,
    "aliyun": _run_aliyun,
}


def run_discovery(discovery_type: str, params: dict) -> DiscoveryResult:
    """
    根据 discovery_type 调用对应发现逻辑，返回 (成功设备列表, 失败列表 [(ip, reason)])。
    不支持的类型抛出 ValueError。
    """
    runner = DISCOVERY_RUNNERS.get(discovery_type)
    if runner is None:
        raise ValueError(f"不支持的发现类型: {discovery_type}")
    return runner(params)
