import React from 'react';
import request from './request';
import { message } from 'antd';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

// 配置 dayjs 使用 UTC 和时区插件
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('Asia/Shanghai'); // 设置默认时区为 UTC+8

interface SessionManagerOptions {
  defaultTimeout?: number; // 默认超时时间（分钟）
  warningTime?: number;    // 警告时间（秒）
  onTimeout?: () => void;  // 超时回调
  onWarning?: () => void;  // 警告回调
}

class SessionManager {
  private timeoutMinutes: number;
  private warningTimeSeconds: number;
  private timer: NodeJS.Timeout | null = null;
  private warningTimer: NodeJS.Timeout | null = null;
  private initialized: boolean = false;
  private events: string[] = [
    'mousedown',
    'keydown',
    'scroll',
    'touchstart'
  ];
  private onTimeout: () => void;
  private onWarning: () => void;
  private lastActivityTime: number = 0;

  constructor(options: SessionManagerOptions = {}) {
    this.timeoutMinutes = options.defaultTimeout || 30;
    this.warningTimeSeconds = options.warningTime || 60;
    this.onTimeout = options.onTimeout || this.defaultTimeoutHandler;
    this.onWarning = options.onWarning || this.defaultWarningHandler;
  }

  /**
   * 默认超时处理函数
   */
  private defaultTimeoutHandler = async (): Promise<void> => {
    try {
      await request.post('/auth/logout', {}, { timeout: 5000 });
    } catch (error) {
      // 超时或网络错误时忽略，下面统一清除并跳转
    }
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  }

  /**
   * 默认警告处理函数
   */
  private defaultWarningHandler = (): void => {
    message.warning({
      content: `由于长时间未操作，您的会话将在 ${this.warningTimeSeconds} 秒后超时。请选择继续操作或退出系统。`,
      duration: this.warningTimeSeconds,
      onClose: () => {
        // 用户关闭警告消息，重置计时器
        this.resetTimer();
      }
    });
  }

  /**
   * 初始化会话管理器
   */
  public async init(): Promise<void> {
    if (this.initialized) {
      return;
    }

    // 检查是否已登录
    const token = localStorage.getItem('token');
    if (token) {
      try {
        // 尝试从后端获取超时设置
        const timeout = await this.getTimeoutFromServer();
        if (timeout) {
          this.timeoutMinutes = timeout;
          console.log(`从服务器获取会话超时设置: ${this.timeoutMinutes}分钟`);
        } else {
          console.log(`使用默认会话超时设置: ${this.timeoutMinutes}分钟`);
        }
      } catch (error) {
        // 使用默认值
        console.log(`获取会话超时设置失败，使用默认值: ${this.timeoutMinutes}分钟`);
      }

      // 添加事件监听器
      this.addEventListeners();
      
      // 添加页面可见性变化监听
      document.addEventListener('visibilitychange', this.handleVisibilityChange);
      
      // 启动计时器
      this.resetTimer();
      
      this.initialized = true;
      console.log(`会话管理器已初始化，超时时间: ${this.timeoutMinutes}分钟，警告时间: ${this.warningTimeSeconds}秒`);
    } else {
      console.log('用户未登录，会话管理器不启动');
    }
  }

  /**
   * 停止会话管理器
   */
  public stop(): void {
    // 移除所有事件监听器
    this.events.forEach(event => {
      document.removeEventListener(event, this.handleUserActivity);
    });
    
    // 移除页面可见性监听
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    
    // 清除计时器
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    
    if (this.warningTimer) {
      clearTimeout(this.warningTimer);
      this.warningTimer = null;
    }
    
    this.initialized = false;
    console.log('会话管理器已停止');
  }

  /**
   * 添加用户活动事件监听器
   */
  private addEventListeners(): void {
    this.events.forEach(event => {
      document.addEventListener(event, this.handleUserActivity);
    });
  }

  /**
   * 处理用户活动
   */
  public handleUserActivity = (): void => {
    // 更新最后活动时间
    this.updateLastActivity();

    // 清除所有现有计时器
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    
    if (this.warningTimer) {
      clearTimeout(this.warningTimer);
      this.warningTimer = null;
    }

    // 重新设置计时器
    const timeoutMs = this.timeoutMinutes * 60 * 1000;
    const warningMs = timeoutMs - (this.warningTimeSeconds * 1000);
    
    // 设置警告计时器
    this.warningTimer = setTimeout(() => {
      this.onWarning();
    }, warningMs);
    
    // 设置超时计时器
    this.timer = setTimeout(() => {
      this.timeout();
    }, timeoutMs);

    console.log('用户活动，重置会话计时器');
  }

  /**
   * 处理页面可见性变化
   */
  private handleVisibilityChange = (): void => {
    if (document.visibilityState === 'visible') {
      // 页面变为可见时，重置计时器
      this.handleUserActivity();
    }
  }

  /**
   * 重置计时器
   */
  private resetTimer(): void {
    this.handleUserActivity();
  }

  /**
   * 超时处理
   */
  private timeout(): void {
    this.onTimeout();
  }

  /**
   * 从服务器获取超时设置（系统管理-安全设置-会话策略的会话超时时间）
   * 任意登录用户可读，与角色无关
   */
  private async getTimeoutFromServer(): Promise<number | null> {
    try {
      const response = await request.get('/security/session-timeout');
      if (response.data && typeof response.data.session_timeout_minutes === 'number') {
        return response.data.session_timeout_minutes;
      }
      return null;
    } catch (error: any) {
      if (error?.response && (error.response.status === 401 || error.response.status === 403)) {
        console.log('获取会话超时设置失败，使用默认值');
        return null;
      }
      console.error('获取会话超时设置失败:', error);
      return null;
    }
  }

  /**
   * 重置会话计时器（供请求拦截器在刷新 token 成功后调用，视为用户活动）
   */
  public resetSessionTimer(): void {
    if (this.initialized) {
      this.handleUserActivity();
    }
  }

  /**
   * 获取当前超时时间（分钟）
   */
  public getTimeoutMinutes(): number {
    return this.timeoutMinutes;
  }

  /**
   * 获取警告时间（秒）
   */
  public getWarningTimeSeconds(): number {
    return this.warningTimeSeconds;
  }

  /**
   * 更新最后活动时间
   */
  public updateLastActivity(): void {
    const now = dayjs().tz('Asia/Shanghai');
    this.lastActivityTime = now.valueOf();
    localStorage.setItem('lastActivityTime', this.lastActivityTime.toString());
  }

  /**
   * 检查会话是否超时
   */
  public checkSessionTimeout(): boolean {
    const now = dayjs().tz('Asia/Shanghai');
    const lastActivity = dayjs(this.lastActivityTime).tz('Asia/Shanghai');
    const diffMinutes = now.diff(lastActivity, 'minute');
    return diffMinutes >= this.timeoutMinutes;
  }
}

const sessionManager = new SessionManager();
export default sessionManager; 