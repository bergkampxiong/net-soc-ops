# -*- coding: utf-8 -*-
"""AWS 设备发现：通过 boto3 列出指定区域 EC2 实例，采集名称、实例 ID、IP、vCPU、内存、存储。"""
import logging
from typing import List, Optional, Tuple, Dict, Any

from .base import DiscoveredDevice

logger = logging.getLogger(__name__)

# CMDB 设备类型（与 int_all_db 一致）
DEVICE_TYPE_NAME = "Virtual Machine"
VENDOR_NAME = "AWS"


def _platform_to_system_type(platform: Optional[str]) -> str:
    """根据 EC2 的 Platform 映射系统类型：Windows -> 其他，其余 -> linux。"""
    if not platform:
        return "linux"
    if str(platform).lower() == "windows":
        return "其他"
    return "linux"


def _get_instance_name(tags: Optional[List[Dict[str, str]]]) -> Optional[str]:
    """从 Tags 中取 Name。"""
    if not tags:
        return None
    for t in tags:
        if t.get("Key") == "Name" and t.get("Value"):
            return (t["Value"] or "").strip()
    return None


def _fetch_instance_type_specs(
    ec2_client: Any,
    instance_types: List[str],
) -> Dict[str, Dict[str, Any]]:
    """批量查询实例类型规格（vCPU、内存 MiB），返回 {instance_type: {"vcpu": int, "memory_mib": int}}。"""
    if not instance_types:
        return {}
    unique_types = list(dict.fromkeys(t for t in instance_types if t))
    result = {}
    # describe_instance_types 单次最多 100 个
    for i in range(0, len(unique_types), 100):
        batch = unique_types[i : i + 100]
        try:
            resp = ec2_client.describe_instance_types(InstanceTypes=batch)
            for it in resp.get("InstanceTypes", []):
                itype = it.get("InstanceType")
                if not itype:
                    continue
                vcpu = None
                mem_mib = None
                if "VCpuInfo" in it and it["VCpuInfo"]:
                    vcpu = it["VCpuInfo"].get("DefaultVCpus")
                if "MemoryInfo" in it and it["MemoryInfo"]:
                    mem_mib = it["MemoryInfo"].get("SizeInMiB")
                result[itype] = {"vcpu": vcpu, "memory_mib": mem_mib}
        except Exception as e:
            logger.warning("describe_instance_types 失败 %s: %s", batch[:3], e)
    return result


def _fetch_volumes_size_gb(ec2_client: Any, volume_ids: List[str]) -> Dict[str, int]:
    """批量查询 EBS 卷大小（GB），返回 {volume_id: size_gb}。"""
    if not volume_ids:
        return {}
    result = {}
    for i in range(0, len(volume_ids), 100):
        batch = volume_ids[i : i + 100]
        try:
            resp = ec2_client.describe_volumes(VolumeIds=batch)
            for vol in resp.get("Volumes", []):
                vid = vol.get("VolumeId")
                size = vol.get("Size")
                if vid is not None and size is not None:
                    result[vid] = int(size)
        except Exception as e:
            logger.warning("describe_volumes 失败: %s", e)
    return result


def discover_aws(
    access_key: str,
    secret_key: str,
    region: str,
    **kwargs,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    使用 boto3 连接 AWS EC2，列出指定区域内的 EC2 实例，返回 (成功设备列表, 失败列表 [(id或ip, reason)])。
    设备名称=实例 Name 标签或 instance_id，资产标签=instance_id，IP=PrivateIpAddress 或 PublicIpAddress，
    设备类型=虚拟机，厂商=AWS，系统类型=根据 Platform：Windows 为 其他，其余为 linux；
    CPU 数量=vCPU 个，内存/存储为 GB。
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError as e:
        logger.exception("boto3 未安装: %s", e)
        return [], [(
            region,
            "未安装 boto3，请执行: pip install boto3",
        )]

    results: List[DiscoveredDevice] = []
    failed: List[Tuple[str, str]] = []
    ec2 = None
    try:
        ec2 = boto3.client(
            "ec2",
            region_name=region.strip(),
            aws_access_key_id=(access_key or "").strip(),
            aws_secret_access_key=(secret_key or "").strip(),
        )
    except Exception as e:
        msg = str(e).strip()[:80] or "创建 EC2 客户端失败"
        failed.append((region, msg))
        return results, failed

    try:
        instances: List[Dict[str, Any]] = []
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for res in page.get("Reservations", []):
                for inst in res.get("Instances", []):
                    instances.append(inst)

        if not instances:
            return results, failed

        # 收集所有 instance_type 和 volume_id
        instance_types = []
        volume_ids = []
        for inst in instances:
            itype = inst.get("InstanceType")
            if itype:
                instance_types.append(itype)
            for bdm in inst.get("BlockDeviceMappings", []):
                ebs = bdm.get("Ebs")
                if ebs and ebs.get("VolumeId"):
                    volume_ids.append(ebs["VolumeId"])

        type_specs = _fetch_instance_type_specs(ec2, instance_types)
        volume_sizes = _fetch_volumes_size_gb(ec2, volume_ids)

        for inst in instances:
            try:
                instance_id = (inst.get("InstanceId") or "").strip()
                if not instance_id:
                    continue
                name_tag = _get_instance_name(inst.get("Tags"))
                name = (name_tag or instance_id)[:100]
                asset_tag = instance_id[:50]
                private_ip = (inst.get("PrivateIpAddress") or "").strip()
                public_ip = (inst.get("PublicIpAddress") or "").strip()
                ip_address = private_ip or public_ip or ""
                platform = inst.get("Platform")
                system_type = _platform_to_system_type(platform)
                itype = inst.get("InstanceType") or ""
                specs = type_specs.get(itype, {})
                vcpu = specs.get("vcpu")
                memory_mib = specs.get("memory_mib")
                memory_gb = round(memory_mib / 1024.0, 2) if memory_mib is not None else None
                storage_gb = 0
                for bdm in inst.get("BlockDeviceMappings", []):
                    ebs = bdm.get("Ebs")
                    if ebs and ebs.get("VolumeId"):
                        storage_gb += volume_sizes.get(ebs["VolumeId"], 0)
                storage_gb = round(storage_gb, 2) if storage_gb is not None else None

                dev = DiscoveredDevice(
                    ip_address=ip_address,
                    name=name,
                    asset_tag=asset_tag,
                    serial_number=None,
                    device_model=itype or None,
                    os_version=None,
                    vendor_name=VENDOR_NAME,
                    device_type_name=DEVICE_TYPE_NAME,
                    system_type_name=system_type,
                    raw={"instance_id": instance_id, "instance_type": itype},
                    cpu_count=vcpu,
                    memory_capacity_gb=memory_gb,
                    storage_capacity_gb=storage_gb,
                )
                results.append(dev)
            except Exception as e:
                iid = inst.get("InstanceId") or "unknown"
                failed.append((str(iid), str(e).strip()[:80] or "未知错误"))
                logger.warning("AWS 发现单台实例失败 %s: %s", iid, e)
    except Exception as e:
        msg = str(e).strip()
        if len(msg) > 80:
            msg = msg[:77] + "..."
        failed.append((region, msg))
        logger.warning("AWS 发现列举失败 %s: %s", region, e)
    return results, failed
