from utils.device_connection_manager import DeviceConnectionManager
from fastapi import Depends
from .device_connection_pool import DeviceConnectionPool, connection_pool

# 创建设备连接管理器实例
device_connection_manager = DeviceConnectionManager()

# 获取设备连接管理器的依赖函数
async def get_device_connection_manager():
    """获取设备连接管理器实例"""
    return device_connection_manager

async def get_connection_pool() -> DeviceConnectionPool:
    """获取设备连接池实例"""
    return connection_pool 