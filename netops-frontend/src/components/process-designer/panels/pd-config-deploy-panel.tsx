import React, { useEffect, useState } from 'react';
import { Drawer, Form, Input, Select, message, Button } from 'antd';
import { getJobTemplates } from '../../../api/automation/job-template';

const { TextArea } = Input;

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
  const [jobTemplates, setJobTemplates] = useState<any[]>([]);

  useEffect(() => {
    if (visible) {
      // 获取作业模板列表
      getJobTemplates()
        .then((response) => {
          setJobTemplates(response.data);
        })
        .catch((error) => {
          message.error('获取作业模板失败');
          console.error(error);
        });
    }
  }, [visible]);

  const handleSave = () => {
    form
      .validateFields()
      .then((values) => {
        onSave(values);
        form.resetFields();
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
      width={500}
      footer={
        <div style={{ textAlign: 'right' }}>
          <Button onClick={onClose} style={{ marginRight: 8 }}>
            取消
          </Button>
          <Button type="primary" onClick={handleSave}>
            保存
          </Button>
        </div>
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
            options={jobTemplates.map((template) => ({
              label: template.name,
              value: template.name,
            }))}
          />
        </Form.Item>
        <Form.Item
          name="configContent"
          label="配置内容"
          rules={[{ required: true, message: '请输入配置内容' }]}
        >
          <TextArea rows={10} placeholder="请输入配置内容" />
        </Form.Item>
      </Form>
    </Drawer>
  );
}; 