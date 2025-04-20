from celery import Celery
import time
import os
import json
import logging
import pytz
from datetime import datetime, timedelta
from database.config import get_redis_url
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from database.session import SessionLocal
from auth.audit import cleanup_old_logs

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S %z'
)

# 设置日志时区
logging.Formatter.converter = lambda *args: datetime.now(pytz.timezone('Asia/Shanghai')).timetuple()

logger = logging.getLogger(__name__)

# 创建Celery实例
celery_app = Celery(
    'netops_tasks',
    broker=get_redis_url(1),
    backend=get_redis_url(2)
)

# 任务配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
)

# 创建调度器
scheduler = BackgroundScheduler()

# 清理旧审计日志的任务
def cleanup_audit_logs_task():
    """清理超过3个月的审计日志"""
    try:
        db = SessionLocal()
        deleted_count = cleanup_old_logs(db, months=3)
        logging.info(f"已清理 {deleted_count} 条超过3个月的审计日志")
    except Exception as e:
        logging.error(f"清理审计日志失败: {e}")
    finally:
        db.close()

# 添加定时任务，每天凌晨2点执行清理
scheduler.add_job(
    cleanup_audit_logs_task,
    CronTrigger(hour=2, minute=0),
    id='cleanup_audit_logs',
    name='清理旧审计日志',
    replace_existing=True
)

@celery_app.task(name="backup_network_devices")
def backup_network_devices(devices=None):
    """
    备份网络设备配置的任务
    """
    if devices is None:
        devices = ["Core-Router-01", "Switch-Floor3-01", "Firewall-Main"]
    
    logger.info(f"开始备份网络设备配置: {devices}")
    
    results = {}
    for device in devices:
        try:
            # 模拟备份过程
            logger.info(f"连接设备 {device}")
            time.sleep(2)  # 模拟连接时间
            
            logger.info(f"备份设备 {device} 的配置")
            time.sleep(3)  # 模拟备份时间
            
            # 模拟备份文件
            backup_file = f"backup_{device}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.cfg"
            
            results[device] = {
                "status": "success",
                "backup_file": backup_file,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"设备 {device} 备份完成")
        except Exception as e:
            logger.error(f"备份设备 {device} 时出错: {str(e)}")
            results[device] = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    logger.info("所有设备备份完成")
    return results

@celery_app.task(name="monitor_bandwidth")
def monitor_bandwidth(devices=None):
    """
    监控带宽使用率的任务
    """
    if devices is None:
        devices = ["Core-Router-01", "Switch-Floor3-01"]
    
    logger.info(f"开始监控带宽使用率: {devices}")
    
    results = {}
    for device in devices:
        try:
            # 模拟监控过程
            logger.info(f"连接设备 {device}")
            time.sleep(1)  # 模拟连接时间
            
            logger.info(f"获取设备 {device} 的带宽数据")
            time.sleep(2)  # 模拟数据收集时间
            
            # 模拟带宽数据
            import random
            bandwidth_usage = random.randint(10, 95)
            
            results[device] = {
                "status": "success",
                "bandwidth_usage": f"{bandwidth_usage}%",
                "timestamp": datetime.now().isoformat()
            }
            
            # 如果带宽使用率过高，记录警告
            if bandwidth_usage > 80:
                logger.warning(f"设备 {device} 带宽使用率过高: {bandwidth_usage}%")
            
            logger.info(f"设备 {device} 带宽监控完成")
        except Exception as e:
            logger.error(f"监控设备 {device} 带宽时出错: {str(e)}")
            results[device] = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    logger.info("所有设备带宽监控完成")
    return results

@celery_app.task(name="update_firewall_rules")
def update_firewall_rules(firewall="Firewall-Main", rules=None):
    """
    更新防火墙规则的任务
    """
    if rules is None:
        rules = [
            {"action": "allow", "source": "192.168.1.0/24", "destination": "any", "port": "80,443"},
            {"action": "deny", "source": "any", "destination": "192.168.1.10", "port": "22"}
        ]
    
    logger.info(f"开始更新防火墙 {firewall} 规则")
    
    try:
        # 模拟更新过程
        logger.info(f"连接防火墙 {firewall}")
        time.sleep(2)  # 模拟连接时间
        
        logger.info(f"获取当前规则配置")
        time.sleep(1)  # 模拟获取配置时间
        
        logger.info(f"应用新规则: {json.dumps(rules)}")
        time.sleep(3)  # 模拟应用规则时间
        
        # 模拟验证
        logger.info("验证新规则")
        time.sleep(2)  # 模拟验证时间
        
        # 随机决定是否成功（实际项目中不应该这样做）
        import random
        success = random.choice([True, True, True, False])  # 75%成功率
        
        if success:
            logger.info("规则更新成功")
            return {
                "status": "success",
                "firewall": firewall,
                "rules_count": len(rules),
                "timestamp": datetime.now().isoformat()
            }
        else:
            error_msg = "规则验证失败"
            logger.error(error_msg)
            return {
                "status": "error",
                "firewall": firewall,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        error_msg = f"更新防火墙规则时出错: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "firewall": firewall,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # 用于测试任务
    result = backup_network_devices()
    print(result) 