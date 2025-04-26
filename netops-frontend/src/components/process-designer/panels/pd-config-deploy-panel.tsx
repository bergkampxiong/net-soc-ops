import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Select, message, Button, Space } from 'antd';
import { getJobTemplates } from '../../../api/automation/job-template';

const { TextArea } = Input;

// 定义作业模板接口
interface JobTemplate {
  name: string;
  content: string;
}

interface PDConfigDeployPanelProps {
  visible: boolean;
  onClose: () => void;
  initialData?: any;
  onSave: (data: any) => void;
}

export const PDConfigDeployPanel: React.FC<PDConfigDeployPanelProps> = ({
  visible,
  onClose,
  initialData,
  onSave,
}) => {
  const [form] = Form.useForm();
  const [jobTemplates, setJobTemplates] = useState<JobTemplate[]>([]);

  // 重置表单
  const resetForm = () => {
    form.resetFields();
    setJobTemplates([]);
  };

  useEffect(() => {
    if (visible) {
      // 获取作业模板列表
      getJobTemplates()
        .then((response) => {
          setJobTemplates(response.data);
          // 如果有初始数据，自动填充配置内容
          if (initialData?.configName) {
            const selectedTemplate = response.data.find((template: JobTemplate) => template.name === initialData.configName);
            if (selectedTemplate) {
              form.setFieldsValue({
                configName: initialData.configName,
                configContent: selectedTemplate.content
              });
            }
          }
        })
        .catch((error) => {
          message.error('获取作业模板失败');
          console.error(error);
        });
    } else {
      // 关闭面板时重置表单
      resetForm();
    }
  }, [visible, initialData]);

  // 处理配置名称选择变化
  const handleConfigNameChange = (value: string) => {
    const selectedTemplate = jobTemplates.find((template: JobTemplate) => template.name === value);
    if (selectedTemplate) {
      form.setFieldsValue({
        configContent: selectedTemplate.content
      });
    }
  };

  const handleSave = () => {
    form
      .validateFields()
      .then((values) => {
        if (!values.configContent) {
          message.error('请先选择配置名称');
          return;
        }
        onSave(values);
        onClose(); // 保存后关闭面板
      })
      .catch((error) => {
        console.error('表单验证失败:', error);
      });
  };

  return (
    <Drawer
      title="配置部署"
      placement="right"
      onClose={onClose}
      open={visible}
      width={400}
      extra={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSave}>
            保存
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={initialData}
      >
        <Form.Item
          name="configName"
          label="配置名称"
          rules={[{ required: true, message: '请选择配置名称' }]}
        >
          <Select
            placeholder="请选择配置名称"
            options={jobTemplates.map((template: JobTemplate) => ({
              label: template.name,
              value: template.name,
            }))}
            onChange={handleConfigNameChange}
          />
        </Form.Item>
        <Form.Item
          name="configContent"
          label="配置内容"
        >
          <TextArea 
            rows={20} 
            placeholder="请选择配置名称后自动填充配置内容" 
            readOnly 
            style={{ height: '750px' }}
          />
        </Form.Item>
      </Form>
    </Drawer>
  );
}; 