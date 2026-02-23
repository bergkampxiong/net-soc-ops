# -*- coding: utf-8 -*-
"""设备发现结果统一结构，便于写入 CMDB。"""
from typing import Optional, List, Any, Dict
from dataclasses import dataclass


@dataclass
class DiscoveredDevice:
    """单台发现设备的信息，与 CMDB Asset + NetworkDevice 字段对应。"""
    ip_address: str
    name: str  # 主机名，用于 Asset.name
    asset_tag: str  # 唯一，用于 Asset.asset_tag
    serial_number: Optional[str] = None
    device_model: Optional[str] = None  # NetworkDevice.device_model
    os_version: Optional[str] = None  # Asset.version / NetworkDevice.os_version，从 show version 等解析
    vendor_name: str = "Cisco"  # 用于解析 vendor_id
    device_type_name: str = "Switch"  # 用于解析 device_type_id，如 Switch / Router
    system_type_name: Optional[str] = None  # 用于解析 system_type_id，与 netmiko/系统类型一致，如 cisco_ios、cisco_xe
    raw: Optional[Dict[str, Any]] = None  # 原始采集数据，便于扩展

    def __post_init__(self):
        if self.raw is None:
            self.raw = {}
