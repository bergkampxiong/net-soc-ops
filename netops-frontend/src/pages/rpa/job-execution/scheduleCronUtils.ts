/**
 * 根据「每天/每周/每月」+ 时间生成 cron 表达式。
 * 格式：分 时 日 月 周（标准 cron，0=周日，1=周一）
 */

export type RecurrenceMode = 'daily' | 'weekly' | 'monthly';

/**
 * 从 recurrence + 时间字符串(HH:mm) + 可选星期/日期 生成 cron
 * @param recurrence 每天 | 每周 | 每月
 * @param timeHHmm 执行时间 "HH:mm"
 * @param dayOfWeek 每周时：1=周一 … 7=周日
 * @param dayOfMonth 每月时：1-31
 */
export function buildCronExpression(
  recurrence: RecurrenceMode,
  timeHHmm: string,
  dayOfWeek?: number,
  dayOfMonth?: number
): string {
  const [hour = 0, minute = 0] = timeHHmm.split(':').map(Number);
  const m = minute;
  const h = hour;
  if (recurrence === 'daily') {
    return `${m} ${h} * * *`;
  }
  if (recurrence === 'weekly' && dayOfWeek !== undefined && dayOfWeek >= 0 && dayOfWeek <= 7) {
    // cron 中 0=周日，1=周一；此处约定 1=周一、7=周日，与 cron 一致
    const dow = dayOfWeek === 7 ? 0 : dayOfWeek;
    return `${m} ${h} * * ${dow}`;
  }
  if (recurrence === 'monthly' && dayOfMonth !== undefined && dayOfMonth >= 1 && dayOfMonth <= 31) {
    return `${m} ${h} ${dayOfMonth} * *`;
  }
  return `${m} ${h} * * *`;
}

/**
 * 尝试从 cron 表达式反解析为预设模式（用于编辑回显）
 * 仅支持标准格式：分 时 日 月 周
 * 返回 null 表示无法映射到预设
 */
export function parseCronToPreset(cronExpression: string): {
  recurrence: RecurrenceMode;
  timeHHmm: string;
  dayOfWeek?: number;
  dayOfMonth?: number;
} | null {
  if (!cronExpression || typeof cronExpression !== 'string') return null;
  const parts = cronExpression.trim().split(/\s+/);
  if (parts.length < 5) return null;
  const [minute, hour, dom, month, dow] = parts;
  const m = minute;
  const h = hour;
  const hasDom = dom && dom !== '*';
  const hasDow = dow !== undefined && dow !== '*';
  if (hasDom && hasDow) return null;
  const pad = (s: string | number) => String(s).padStart(2, '0');
  if (hasDom) {
    const day = parseInt(dom, 10);
    if (Number.isNaN(day) || day < 1 || day > 31) return null;
    return {
      recurrence: 'monthly',
      timeHHmm: `${pad(h)}:${pad(m)}`,
      dayOfMonth: day,
    };
  }
  if (hasDow) {
    const w = parseInt(dow, 10);
    if (Number.isNaN(w) || w < 0 || w > 6) return null;
    const dayOfWeek = w === 0 ? 7 : w;
    return {
      recurrence: 'weekly',
      timeHHmm: `${pad(h)}:${pad(m)}`,
      dayOfWeek,
    };
  }
  if (dom === '*' && dow === '*') {
    return { recurrence: 'daily', timeHHmm: `${pad(h)}:${pad(m)}` };
  }
  return null;
}

const WEEKDAY_LABELS: Record<number, string> = {
  1: '周一',
  2: '周二',
  3: '周三',
  4: '周四',
  5: '周五',
  6: '周六',
  7: '周日',
};

/**
 * 将 schedule_config 格式化为简短中文摘要，便于详情/列表展示
 */
export function formatScheduleSummary(config: {
  type?: string;
  cron_expression?: string;
  interval_seconds?: number;
  timezone?: string;
} | null | undefined): string {
  if (!config) return '-';
  const tz = config.timezone || 'Asia/Shanghai';
  if (config.type === 'interval' && config.interval_seconds != null) {
    const min = Math.floor(config.interval_seconds / 60);
    if (min < 60) return `每 ${config.interval_seconds} 秒（${tz}）`;
    const h = Math.floor(min / 60);
    if (h < 24) return `每 ${h} 小时（${tz}）`;
    return `每 ${Math.floor(h / 24)} 天（${tz}）`;
  }
  if (config.type === 'cron' && config.cron_expression) {
    const preset = parseCronToPreset(config.cron_expression);
    if (preset) {
      const timePart = preset.timeHHmm;
      if (preset.recurrence === 'daily') return `每天 ${timePart}（${tz}）`;
      if (preset.recurrence === 'weekly' && preset.dayOfWeek != null) {
        return `每周${WEEKDAY_LABELS[preset.dayOfWeek] ?? ''} ${timePart}（${tz}）`;
      }
      if (preset.recurrence === 'monthly' && preset.dayOfMonth != null) {
        return `每月 ${preset.dayOfMonth} 号 ${timePart}（${tz}）`;
      }
    }
    return `Cron: ${config.cron_expression}（${tz}）`;
  }
  return '-';
}
