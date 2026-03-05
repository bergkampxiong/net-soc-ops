/**
 * 系统时间统一：展示使用全局时钟时区（系统管理配置），24 小时制，精确到秒。
 * 入参可为 API 返回的 ISO 字符串或已是 "YYYY-MM-DD HH:mm:ss" 的字符串。
 */
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

/** 默认展示时区，与后端一致 */
const DEFAULT_DISPLAY_TZ = 'Asia/Shanghai';

/** 全局时钟：展示用时区，由系统全局配置 GLOBAL_TIMEZONE 控制，Layout 初始化时拉取并设置 */
let _displayTimezone: string = DEFAULT_DISPLAY_TZ;

/** 24 小时制，精确到秒 */
const FORMAT_SEC = 'YYYY-MM-DD HH:mm:ss';

/** 已是 "YYYY-MM-DD HH:mm:ss" 格式（无需再转换） */
const ALREADY_PATTERN = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;

/** 带有时区信息的字符串（Z 或 ±HH:MM）按原意解析；否则视为服务端 UTC（如作业 API 返回的 naive datetime） */
function parseToDisplayTz(s: string): dayjs.Dayjs | null {
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(s);
  const d = hasTz ? dayjs(s) : dayjs.utc(s);
  const inDisplay = d.tz(_displayTimezone);
  return inDisplay.isValid() ? inDisplay : null;
}

/**
 * 设置全局展示时区（由系统管理-全局配置/安全设置中的 GLOBAL_TIMEZONE 驱动）。
 * 空或无效时使用 Asia/Shanghai。
 */
export function setDisplayTimezone(tzName: string | undefined | null): void {
  const tz = (tzName != null && String(tzName).trim()) ? String(tzName).trim() : DEFAULT_DISPLAY_TZ;
  _displayTimezone = tz;
}

/**
 * 返回当前全局展示时区名称，供需要直接使用 dayjs.tz 的代码使用。
 */
export function getDisplayTimezone(): string {
  return _displayTimezone;
}

/**
 * 将时间按全局时钟时区格式化为 24 小时制，精确到秒。
 * @param value API 返回的 ISO 字符串或 "YYYY-MM-DD HH:mm:ss"
 * @param fallback 空值时显示，默认 '-'
 */
export function formatBeijingToSecond(
  value: string | undefined | null,
  fallback: string = '-'
): string {
  if (value == null || value === '') return fallback;
  const s = String(value).trim();
  if (!s) return fallback;
  if (ALREADY_PATTERN.test(s)) return s;
  const d = parseToDisplayTz(s);
  return d ? d.format(FORMAT_SEC) : fallback;
}
