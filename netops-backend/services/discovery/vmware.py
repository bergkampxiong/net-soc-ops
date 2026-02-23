# -*- coding: utf-8 -*-
"""VMware 设备发现：通过 vCenter/ESXi API 列出所有虚拟机，采集名称、UUID、IP、客户机操作系统。"""
import logging
from typing import List, Optional, Tuple

from .base import DiscoveredDevice

logger = logging.getLogger(__name__)

# CMDB 设备类型（与 int_all_db 一致）
DEVICE_TYPE_NAME = "Virtual Machine"


def _guest_id_to_system_type(guest_id: Optional[str]) -> str:
    """
    根据 config.guestId 映射系统类型：Windows -> 其他，Linux -> linux，其余 -> 其他。
    """
    if not guest_id:
        return "其他"
    g = guest_id.lower()
    if "windows" in g or g.startswith("win"):
        return "其他"
    if "linux" in g or "rhel" in g or "ubuntu" in g or "centos" in g or "debian" in g or "sles" in g or "oracle" in g:
        return "linux"
    return "其他"


def _get_vm_guest_ip(vm) -> str:
    """从 VM guest 信息取第一个可用 IP，无则返回空字符串。"""
    try:
        if hasattr(vm, "guest") and vm.guest:
            if getattr(vm.guest, "ipAddress", None) and vm.guest.ipAddress:
                return (vm.guest.ipAddress or "").strip()
            if getattr(vm.guest, "net", None) and vm.guest.net:
                for nic in vm.guest.net:
                    if getattr(nic, "ipAddress", None) and nic.ipAddress:
                        for addr in nic.ipAddress:
                            if addr and addr.strip():
                                return addr.strip()
    except Exception:
        pass
    return ""


def _get_vm_uuid(vm) -> str:
    """取 VM 的 config.uuid，若无则用 config.instanceUuid 或 name 兜底。"""
    try:
        if hasattr(vm, "config") and vm.config:
            if getattr(vm.config, "uuid", None) and vm.config.uuid:
                return (vm.config.uuid or "").strip()
            if getattr(vm.config, "instanceUuid", None) and vm.config.instanceUuid:
                return (vm.config.instanceUuid or "").strip()
    except Exception:
        pass
    return ""


def _get_vm_guest_id(vm) -> Optional[str]:
    """取 VM 的 config.guestId（客户机操作系统标识）。"""
    try:
        if hasattr(vm, "config") and vm.config and getattr(vm.config, "guestId", None):
            return (vm.config.guestId or "").strip() or None
    except Exception:
        pass
    return None


def _get_vm_cpu_count(vm) -> Optional[int]:
    """取 VM 的 vCPU 数量（个）。"""
    try:
        if hasattr(vm, "config") and vm.config and hasattr(vm.config, "hardware") and vm.config.hardware:
            n = getattr(vm.config.hardware, "numCPU", None)
            if n is not None and isinstance(n, int) and n >= 0:
                return n
    except Exception:
        pass
    return None


def _get_vm_memory_gb(vm) -> Optional[float]:
    """取 VM 的内存容量，转换为 GB（config.hardware.memoryMB / 1024）。"""
    try:
        if hasattr(vm, "config") and vm.config and hasattr(vm.config, "hardware") and vm.config.hardware:
            mb = getattr(vm.config.hardware, "memoryMB", None)
            if mb is not None and isinstance(mb, (int, float)) and mb >= 0:
                return round(mb / 1024.0, 2)
    except Exception:
        pass
    return None


def _get_vm_storage_gb(vm) -> Optional[float]:
    """取 VM 的存储容量（所有 VirtualDisk 的 capacityInKB 之和），转换为 GB。"""
    try:
        if not hasattr(vm, "config") or not vm.config or not getattr(vm.config, "hardware", None):
            return None
        devs = getattr(vm.config.hardware, "device", None) or []
        total_kb = 0
        for dev in devs:
            # VirtualDisk: capacityInKB 或 capacityInBytes
            if type(dev).__name__ == "VirtualDisk" or (hasattr(dev, "capacityInKB") or hasattr(dev, "capacityInBytes")):
                if getattr(dev, "capacityInKB", None) is not None and dev.capacityInKB > 0:
                    total_kb += int(dev.capacityInKB)
                elif getattr(dev, "capacityInBytes", None) is not None and dev.capacityInBytes > 0:
                    total_kb += int(dev.capacityInBytes) // 1024
        if total_kb > 0:
            return round(total_kb / (1024 * 1024), 2)
    except Exception:
        pass
    return None


def discover_vmware(
    host: str,
    username: str,
    password: str,
    port: int = 443,
    timeout: Optional[int] = None,
    threads: Optional[int] = None,
    enable_password: Optional[str] = None,
    **kwargs,
) -> Tuple[List[DiscoveredDevice], List[Tuple[str, str]]]:
    """
    连接 vCenter/ESXi，列出所有虚拟机，返回 (成功设备列表, 失败列表 [(ip或host, reason)])。
    设备名称=虚拟机名称，资产标签=虚拟机 UUID，IP=客户机 IP（无则空），设备类型=虚拟机，厂商为空，
    系统类型=根据客户机操作系统：Windows 为 其他，Linux 为 linux，其余为 其他。
    """
    try:
        from pyVim.connect import SmartConnect, Disconnect
        from pyVmomi import vim
    except ImportError as e:
        logger.exception("pyvmomi 未安装: %s", e)
        return [], [(
            host,
            "未安装 pyvmomi，请执行: pip install pyvmomi",
        )]

    results: List[DiscoveredDevice] = []
    failed: List[Tuple[str, str]] = []
    si = None
    try:
        # pyvmomi 9.x 已移除 SmartConnectNoSSL，改用 SmartConnect(disableSslCertValidation=True)
        si = SmartConnect(
            host=host.strip(),
            user=username,
            pwd=password,
            port=port,
            disableSslCertValidation=True,
        )
        if not si:
            failed.append((host, "连接失败（未返回服务实例）"))
            return results, failed
        content = si.RetrieveContent()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        for vm in container.view:
            try:
                name = (getattr(vm, "name", None) or "").strip() or "unknown"
                uuid_val = _get_vm_uuid(vm)
                asset_tag = uuid_val if uuid_val else f"VM-{name}"[:50]
                ip_address = _get_vm_guest_ip(vm)
                guest_id = _get_vm_guest_id(vm)
                system_type = _guest_id_to_system_type(guest_id)
                cpu_count = _get_vm_cpu_count(vm)
                memory_gb = _get_vm_memory_gb(vm)
                storage_gb = _get_vm_storage_gb(vm)
                dev = DiscoveredDevice(
                    ip_address=ip_address or "",
                    name=name[:100],
                    asset_tag=asset_tag[:50],
                    serial_number=None,
                    device_model=None,
                    os_version=None,
                    vendor_name="",
                    device_type_name=DEVICE_TYPE_NAME,
                    system_type_name=system_type,
                    raw={"guestId": guest_id},
                    cpu_count=cpu_count,
                    memory_capacity_gb=memory_gb,
                    storage_capacity_gb=storage_gb,
                )
                results.append(dev)
            except Exception as e:
                vm_name = getattr(vm, "name", host) or host
                failed.append((str(vm_name), str(e).strip()[:80] or "未知错误"))
                logger.warning("VMware 发现单台 VM 失败 %s: %s", vm_name, e)
        container.Destroy()
    except Exception as e:
        msg = str(e).strip()
        if len(msg) > 80:
            msg = msg[:77] + "..."
        failed.append((host, msg))
        logger.warning("VMware 发现连接/列举失败 %s: %s", host, e)
    finally:
        if si:
            try:
                Disconnect(si)
            except Exception:
                pass
    return results, failed
