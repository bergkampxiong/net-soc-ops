/**
 * 会话活动通知：请求层在 token 刷新成功等时机通知会话管理器重置计时器，避免与 sessionManager 循环依赖
 */

let sessionActivityCallback: (() => void) | null = null;

export function setSessionActivityCallback(cb: (() => void) | null): void {
  sessionActivityCallback = cb;
}

export function notifySessionActivity(): void {
  if (sessionActivityCallback) {
    sessionActivityCallback();
  }
}
