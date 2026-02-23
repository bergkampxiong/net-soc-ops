# -*- coding: utf-8 -*-
"""将前端 ip_range 解析为可探测的 IP 列表。支持 CIDR 与 start-end 范围。"""
import ipaddress
import re
from typing import List


def parse_ip_range(ip_range: str) -> List[str]:
    """
    解析 IP 范围字符串，返回主机 IP 列表。
    支持格式：
    - CIDR: 192.168.1.0/24
    - 范围: 192.168.1.1-192.168.1.254 或 192.168.1.1-254
    - 单 IP: 192.168.1.1
    """
    if not ip_range or not ip_range.strip():
        return []
    ip_range = ip_range.strip()
    ips: List[str] = []

    # CIDR
    if "/" in ip_range:
        try:
            net = ipaddress.ip_network(ip_range, strict=False)
            for host in net.hosts():
                ips.append(str(host))
            return ips
        except ValueError:
            pass

    # 范围 192.168.1.1-192.168.1.254 或 192.168.1.1-254
    range_match = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.)(\d{1,3})\s*-\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.)?(\d{1,3})$", ip_range)
    if range_match:
        prefix = range_match.group(1)
        start = int(range_match.group(2))
        end_prefix = range_match.group(3)
        end_last = int(range_match.group(4))
        if end_prefix is None:
            end_last = end_last
            end_prefix = prefix
        else:
            end_prefix = end_prefix
        for last in range(start, min(end_last, 255) + 1):
            ips.append(f"{prefix}{last}")
        return ips

    # 单 IP
    try:
        ipaddress.ip_address(ip_range)
        return [ip_range]
    except ValueError:
        pass

    return []
