# 系统时间统一：对外展示/API 返回使用全局配置时区（默认北京时间），精确到秒。
# 存库仍使用 UTC，本模块仅用于序列化输出。全局时区由 system_global_config 的 GLOBAL_TIMEZONE 控制。
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import pytz
except ImportError:
    pytz = None

# 默认展示时区：北京时间 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))
BEIJING_FORMAT = "%Y-%m-%d %H:%M:%S"

# 全局时钟：展示用时区，可由系统全局配置覆盖（启动时或 PUT global-config 时加载）
_display_tz = BEIJING_TZ


def set_display_timezone(tz_name: Optional[str]) -> None:
    """设置全局展示时区（如 Asia/Shanghai、UTC）。空或无效时恢复默认北京时间。"""
    global _display_tz
    if not tz_name or not (tz_name := str(tz_name).strip()):
        _display_tz = BEIJING_TZ
        return
    if pytz is None:
        _display_tz = BEIJING_TZ
        return
    try:
        _display_tz = pytz.timezone(tz_name)
    except Exception:
        _display_tz = BEIJING_TZ


def get_display_timezone_name() -> str:
    """返回当前展示时区名称（如 Asia/Shanghai），供前端或配置展示。"""
    if _display_tz is BEIJING_TZ:
        return "Asia/Shanghai"
    if pytz and hasattr(_display_tz, "zone"):
        return getattr(_display_tz, "zone", "Asia/Shanghai")
    return "Asia/Shanghai"


def utc_to_beijing_str(dt) -> Optional[str]:
    """
    将 datetime 转为全局配置时区的字符串，精确到秒。
    - None 返回 None。
    - naive datetime 视为 UTC 再转展示时区。
    """
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(_display_tz)
    return local.strftime(BEIJING_FORMAT)
