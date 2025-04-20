import React, { useState, useEffect } from 'react';
import { Select, message } from 'antd';
import type { SelectProps } from 'antd';

interface Template {
  id: string;
  name: string;
  template_type: string;
  content: string;
  description: string;
  status: string;
  device_type: string;
}

const ConfigGenerator: React.FC = () => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);

  // 获取模板列表
  const fetchTemplates = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/config-generator/templates');
      if (!response.ok) {
        throw new Error('获取模板列表失败');
      }
      const data = await response.json();
      // 确保只显示jinja2类型的模板
      const jinja2Templates = data.filter((template: Template) => template.template_type === 'jinja2');
      setTemplates(jinja2Templates);
    } catch (error) {
      console.error('获取模板列表失败:', error);
      message.error('获取模板列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const options: SelectProps['options'] = templates.map(template => ({
    label: template.name,
    value: template.id,
    description: template.description
  }));

  return (
    <div>
      <Select
        showSearch
        placeholder="请选择Jinja2模板"
        optionFilterProp="children"
        loading={loading}
        options={options}
        style={{ width: '100%' }}
      />
    </div>
  );
};

export default ConfigGenerator; 