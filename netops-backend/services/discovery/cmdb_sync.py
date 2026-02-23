# -*- coding: utf-8 -*-
"""将发现结果写入 CMDB：Asset + NetworkDevice，按 IP 或 asset_tag 去重更新。"""
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from database.cmdb_models import Asset, NetworkDevice, DeviceType, Vendor, AssetStatus, SystemType, VirtualMachine
from .base import DiscoveredDevice

logger = logging.getLogger(__name__)

# 默认状态名（与 int_all_db 初始化一致）
DEFAULT_STATUS_NAME = "使用中"


def _resolve_ids(
    db: Session,
    vendor_name: str,
    device_type_name: str,
    system_type_name: Optional[str] = None,
) -> tuple:
    """解析 vendor_id、device_type_id、status_id、system_type_id。"""
    vendor = db.query(Vendor).filter(Vendor.name == vendor_name).first()
    device_type = db.query(DeviceType).filter(DeviceType.name == device_type_name).first()
    status = db.query(AssetStatus).filter(AssetStatus.name == DEFAULT_STATUS_NAME).first()
    vendor_id = vendor.id if vendor else None
    device_type_id = device_type.id if device_type else None
    status_id = status.id if status else None
    system_type_id = None
    if system_type_name:
        st = db.query(SystemType).filter(SystemType.name == system_type_name).first()
        system_type_id = st.id if st else None
    return vendor_id, device_type_id, status_id, system_type_id


def sync_discovered_to_cmdb(db: Session, devices: List[DiscoveredDevice]) -> int:
    """
    将发现的设备列表写入/更新到 CMDB。
    按 ip_address 查找是否已存在资产；存在则更新，否则创建。并创建或更新 NetworkDevice。
    返回写入或更新的设备数量。
    """
    if not devices:
        return 0
    count = 0
    now = datetime.utcnow().isoformat()
    for dev in devices:
        try:
            vendor_id, device_type_id, status_id, system_type_id = _resolve_ids(
                db,
                dev.vendor_name,
                dev.device_type_name,
                getattr(dev, "system_type_name", None),
            )
            existing = db.query(Asset).filter(Asset.ip_address == dev.ip_address).first()
            if not existing:
                existing = db.query(Asset).filter(Asset.asset_tag == dev.asset_tag).first()
            if existing:
                existing.name = (dev.name or dev.ip_address or "")[:100]
                existing.asset_tag = dev.asset_tag[:50]
                existing.ip_address = (dev.ip_address.strip() or None) if (dev.ip_address and dev.ip_address.strip()) else None
                if dev.serial_number:
                    existing.serial_number = dev.serial_number[:50]
                if device_type_id is not None:
                    existing.device_type_id = device_type_id
                if vendor_id is not None:
                    existing.vendor_id = vendor_id
                if status_id is not None:
                    existing.status_id = status_id
                if system_type_id is not None:
                    existing.system_type_id = system_type_id
                if dev.os_version:
                    existing.version = dev.os_version[:50]
                if getattr(dev, "cpu_count", None) is not None:
                    existing.cpu_count = dev.cpu_count
                if getattr(dev, "memory_capacity_gb", None) is not None:
                    existing.memory_capacity = dev.memory_capacity_gb
                if getattr(dev, "storage_capacity_gb", None) is not None:
                    existing.storage_capacity = dev.storage_capacity_gb
                existing.updated_at = now
                asset_id = existing.id
            else:
                asset_tag = dev.asset_tag[:50]
                name = (dev.name or dev.ip_address or "")[:100]
                new_asset = Asset(
                    name=name,
                    asset_tag=asset_tag,
                    ip_address=(dev.ip_address.strip() or None) if (dev.ip_address and dev.ip_address.strip()) else None,
                    serial_number=dev.serial_number[:50] if dev.serial_number else None,
                    device_type_id=device_type_id,
                    vendor_id=vendor_id,
                    status_id=status_id,
                    system_type_id=system_type_id,
                    version=dev.os_version[:50] if dev.os_version else None,
                    cpu_count=getattr(dev, "cpu_count", None),
                    memory_capacity=getattr(dev, "memory_capacity_gb", None),
                    storage_capacity=getattr(dev, "storage_capacity_gb", None),
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_asset)
                db.flush()
                asset_id = new_asset.id
            net_dev = db.query(NetworkDevice).filter(NetworkDevice.asset_id == asset_id).first()
            if net_dev:
                if dev.device_model:
                    net_dev.device_model = dev.device_model[:100]
                if dev.os_version:
                    net_dev.os_version = dev.os_version[:50]
                net_dev.management_ip = (dev.ip_address.strip() or None) if (dev.ip_address and dev.ip_address.strip()) else None
                net_dev.updated_at = now
            else:
                net_dev = NetworkDevice(
                    asset_id=asset_id,
                    device_model=dev.device_model[:100] if dev.device_model else None,
                    os_version=dev.os_version[:50] if dev.os_version else None,
                    management_ip=(dev.ip_address.strip() or None) if (dev.ip_address and dev.ip_address.strip()) else None,
                    created_at=now,
                    updated_at=now,
                )
                db.add(net_dev)
            # 虚拟机类型：同步到 cmdb_virtual_machines（vcpu_count 个、memory_size/disk_size GB）
            if getattr(dev, "device_type_name", None) == "Virtual Machine":
                _v = (getattr(dev, "vendor_name", None) or "").strip()
                vm_type_name = "AWS" if _v == "AWS" else ("阿里云" if _v == "阿里云" else "VMware")
                vm_rec = db.query(VirtualMachine).filter(VirtualMachine.asset_id == asset_id).first()
                if vm_rec:
                    if getattr(dev, "cpu_count", None) is not None:
                        vm_rec.vcpu_count = dev.cpu_count
                    if getattr(dev, "memory_capacity_gb", None) is not None:
                        vm_rec.memory_size = dev.memory_capacity_gb
                    if getattr(dev, "storage_capacity_gb", None) is not None:
                        vm_rec.disk_size = dev.storage_capacity_gb
                    vm_rec.vm_type = vm_type_name
                    vm_rec.updated_at = now
                else:
                    vm_rec = VirtualMachine(
                        asset_id=asset_id,
                        vm_type=vm_type_name,
                        vcpu_count=getattr(dev, "cpu_count", None),
                        memory_size=getattr(dev, "memory_capacity_gb", None),
                        disk_size=getattr(dev, "storage_capacity_gb", None),
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(vm_rec)
            count += 1
        except Exception as e:
            logger.exception("同步发现设备到 CMDB 失败 %s: %s", dev.ip_address, e)
            db.rollback()
            raise
    db.commit()
    return count
