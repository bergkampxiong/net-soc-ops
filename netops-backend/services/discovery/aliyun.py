# -*- coding: utf-8 -*-
"""阿里云设备发现：通过 ECS SDK 列出指定区域 ECS 实例，采集名称、实例 ID、IP、vCPU、内存、存储。"""
import logging
from typing import List, Optional, Tuple, Dict, Any

from .base import DiscoveredDevice

logger = logging.getLogger(__name__)

# CMDB 设备类型（与 int_all_db 一致）
DEVICE_TYPE_NAME = "Virtual Machine"
VENDOR_NAME = "阿里云"


def _os_type_to_system_type(os_type: Optional[str]) -> str:
    """根据 OSType 映射系统类型：windows -> 其他，linux -> linux。"""
    if not os_type:
        return "linux"
    if str(os_type).lower() == "windows":
        return "其他"
    return "linux"


def _get_instance_ip(inst: Any) -> str:
    """从实例取第一个可用 IP：Vpc 私网 IP 或公网 IP。"""
    try:
        # VpcAttributes.PrivateIpAddress.IpAddress 可能为列表
        vpc = getattr(inst, "vpc_attributes", None)
        if vpc and getattr(vpc, "private_ip_address", None):
            addrs = vpc.private_ip_address
            if isinstance(addrs, list) and addrs:
                return (addrs[0] or "").strip()
            if isinstance(addrs, str) and addrs.strip():
                return addrs.strip()
        # 公网 IP
        pub = getattr(inst, "public_ip_address", None)
        if pub:
            if isinstance(pub, list) and pub:
                return (pub[0] or "").strip()
            if isinstance(pub, str) and pub.strip():
                return pub.strip()
        # InnerIpAddress（经典网络）
        inner = getattr(inst, "inner_ip_address", None)
        if inner:
            if isinstance(inner, list) and inner:
                return (inner[0] or "").strip()
            if isinstance(inner, str) and inner.strip():
                return inner.strip()
    except Exception:
        pass
    return ""


def _fetch_disks_size_gb(client: Any, region: str, instance_ids: List[str]) -> Dict[str, int]:
    """按实例 ID 查询挂载的云盘总容量（GB），返回 {instance_id: size_gb}。"""
    if not instance_ids:
        return {}
    result = {iid: 0 for iid in instance_ids}
    try:
        from alibabacloud_ecs20140526 import models as ecs_models
    except ImportError:
        return result
    for iid in instance_ids:
        try:
            req = ecs_models.DescribeDisksRequest(region_id=region, instance_id=iid, page_size=100)
            resp = client.describe_disks(req)
            if not resp.body or not getattr(resp.body, "disks", None):
                continue
            disks = resp.body.disks
            if not isinstance(disks, list):
                disks = [disks] if disks else []
            total = 0
            for d in disks:
                size = getattr(d, "size", None)
                if size is not None:
                    total += int(size)
            result[iid] = total
        except Exception as e:
            logger.debug("DescribeDisks %s: %s", iid, e)
    return result


def discover_aliyun(
    access_key: str,
    secret_key: str,
    region: str,
    **kwargs,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    使用阿里云 ECS SDK 列出指定区域内的 ECS 实例，返回 (成功设备列表, 失败列表 [(id或ip, reason)])。
    设备名称=InstanceName 或 InstanceId，资产标签=InstanceId，IP=私网或公网 IP，
    设备类型=虚拟机，厂商=阿里云，系统类型=根据 OSType：Windows 为 其他，其余为 linux；
    CPU 数量=vCPU 个，内存/存储为 GB。
    """
    try:
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_ecs20140526.client import Client as EcsClient
        from alibabacloud_ecs20140526 import models as ecs_models
    except ImportError as e:
        logger.exception("阿里云 ECS SDK 未安装: %s", e)
        return [], [(
            region,
            "未安装 alibabacloud_ecs20140526，请执行: pip install alibabacloud_ecs20140526",
        )]

    results: List[DiscoveredDevice] = []
    failed: List[Tuple[str, str]] = []
    region = (region or "").strip()
    access_key = (access_key or "").strip()
    secret_key = (secret_key or "").strip()
    if not region or not access_key or not secret_key:
        failed.append((region or "unknown", "access_key、secret_key、region 必填"))
        return results, failed

    try:
        config = open_api_models.Config(
            access_key_id=access_key,
            access_key_secret=secret_key,
            endpoint=f"ecs.{region}.aliyuncs.com",
            region_id=region,
        )
        client = EcsClient(config)
    except Exception as e:
        msg = str(e).strip()[:80] or "创建 ECS 客户端失败"
        failed.append((region, msg))
        return results, failed

    instances: List[Any] = []
    try:
        next_token = None
        while True:
            req = ecs_models.DescribeInstancesRequest(region_id=region, max_results=100)
            if next_token:
                req.next_token = next_token
            resp = client.describe_instances(req)
            if not resp.body or not getattr(resp.body, "instances", None):
                break
            inst_list = resp.body.instances
            if not isinstance(inst_list, list):
                inst_list = [inst_list] if inst_list else []
            instances.extend(inst_list)
            next_token = getattr(resp.body, "next_token", None)
            if not next_token:
                break
    except Exception as e:
        msg = str(e).strip()
        if len(msg) > 80:
            msg = msg[:77] + "..."
        failed.append((region, msg))
        logger.warning("阿里云 DescribeInstances 失败 %s: %s", region, e)
        return results, failed

    if not instances:
        return results, failed

    # 可选：拉取每台实例的磁盘总容量（会多 N 次 API 调用）
    instance_ids = []
    for inst in instances:
        iid = getattr(inst, "instance_id", None)
        if iid:
            instance_ids.append(iid)
    disk_sizes = _fetch_disks_size_gb(client, region, instance_ids)

    for inst in instances:
        try:
            instance_id = (getattr(inst, "instance_id", None) or "").strip()
            if not instance_id:
                continue
            instance_name = (getattr(inst, "instance_name", None) or "").strip()
            name = (instance_name or instance_id)[:100]
            asset_tag = instance_id[:50]
            ip_address = _get_instance_ip(inst)
            os_type = getattr(inst, "os_type", None)
            system_type = _os_type_to_system_type(os_type)
            cpu = getattr(inst, "cpu", None)
            cpu_count = int(cpu) if cpu is not None and str(cpu).isdigit() else None
            memory_mib = getattr(inst, "memory", None)
            try:
                memory_gb = round(int(memory_mib) / 1024.0, 2) if memory_mib is not None else None
            except (TypeError, ValueError):
                memory_gb = None
            instance_type = (getattr(inst, "instance_type", None) or "").strip() or None
            storage_gb = disk_sizes.get(instance_id)
            if storage_gb is not None and storage_gb == 0:
                storage_gb = None
            elif storage_gb is not None:
                storage_gb = round(storage_gb, 2)

            dev = DiscoveredDevice(
                ip_address=ip_address,
                name=name,
                asset_tag=asset_tag,
                serial_number=None,
                device_model=instance_type,
                os_version=None,
                vendor_name=VENDOR_NAME,
                device_type_name=DEVICE_TYPE_NAME,
                system_type_name=system_type,
                raw={"instance_id": instance_id, "instance_type": instance_type},
                cpu_count=cpu_count,
                memory_capacity_gb=memory_gb,
                storage_capacity_gb=storage_gb,
            )
            results.append(dev)
        except Exception as e:
            iid = getattr(inst, "instance_id", "unknown")
            failed.append((str(iid), str(e).strip()[:80] or "未知错误"))
            logger.warning("阿里云 发现单台实例失败 %s: %s", iid, e)
    return results, failed
