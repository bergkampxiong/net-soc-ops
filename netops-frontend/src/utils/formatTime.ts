/**
 * 系统时间统一：展示均为北京时间，精确到秒。
 * 入参可为 API 返回的 ISO 字符串或已是 "YYYY-MM-DD HH:mm:ss" 的字符串。
 */
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

const BEIJING = 'Asia/Shanghai';
const FORMAT_SEC = 'YYYY-MM-DD HH:mm:ss';

/** 已是北京时间的 "YYYY-MM-DD HH:mm:ss" 格式（无需再转换） */
const BEIJING_PATTERN = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;

/**
 * 将时间格式化为北京时间，精确到秒。
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
  if (BEIJING_PATTERN.test(s)) return s;
  const d = dayjs(s).tz(BEIJING);
  return d.isValid() ? d.format(FORMAT_SEC) : fallback;
}
