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


# 已实现的发现类型
DISCOVERY_RUNNERS: dict[str, DiscoveryRunner] = {
    "cisco-campus": _run_cisco_campus,
    "cisco-datacenter": _run_cisco_datacenter,
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
