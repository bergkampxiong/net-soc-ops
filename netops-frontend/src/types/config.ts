/**
 * 配置文件类型定义
 */

/**
 * 配置文件接口
 */
export interface ConfigFile {
  id: string;
  name: string;
  template_type: string;
  content: string;
  description: string | null;
  status: string;
  device_type: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}

/**
 * 配置文件版本接口
 */
export interface Version {
  version: number;
  content: string;
  comment: string;
  created_at: string;
  created_by: string;
} 