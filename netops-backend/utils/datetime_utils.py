# 系统时间统一：对外展示/API 返回均为北京时间，精确到秒。
# 存库仍使用 UTC，本模块仅用于序列化输出。
from datetime import datetime, timezone, timedelta
from typing import Optional

# 北京时间 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))
# 输出格式：精确到秒
BEIJING_FORMAT = "%Y-%m-%d %H:%M:%S"


def utc_to_beijing_str(dt) -> Optional[str]:
    """
    将 datetime 转为北京时间字符串，精确到秒。
    - None 返回 None。
    - naive datetime 视为 UTC 再转北京时间。
    """
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    beijing = dt.astimezone(BEIJING_TZ)
    return beijing.strftime(BEIJING_FORMAT)
