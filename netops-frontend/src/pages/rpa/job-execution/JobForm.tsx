import React, { useEffect } from 'react';
import { Form, Input, Select, Button, Card } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import request from '@/utils/request';
import type { JobFormData } from './types';

const { TextArea } = Input;
const { Option } = Select;

const JobForm: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;

  useEffect(() => {
    if (isEdit) {
      fetchJob();
    }
  }, [id]);

  const fetchJob = async () => {
    try {
      const response = await request.get(`/jobs/${id}`);
      form.setFieldsValue(response.data);
    } catch (error) {
      console.error('获取作业详情失败:', error);
    }
  };

  const handleSubmit = async (values: JobFormData) => {
    try {
      if (isEdit) {
        await request.put(`/jobs/${id}`, values);
      } else {
        await request.post('/jobs', values);
      }
      navigate('/rpa/task-job-management/job-execution');
    } catch (error) {
      console.error('保存作业失败:', error);
    }
  };

  return (
    <Card title={isEdit ? '编辑作业' : '新建作业'}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <Form.Item
          name="name"
          label="作业名称"
          rules={[{ required: true, message: '请输入作业名称' }]}
        >
          <Input placeholder="请输入作业名称" />
        </Form.Item>

        <Form.Item
          name="description"
          label="作业描述"
        >
          <TextArea rows={4} placeholder="请输入作业描述" />
        </Form.Item>

        <Form.Item
          name="job_type"
          label="作业类型"
          rules={[{ required: true, message: '请选择作业类型' }]}
        >
          <Select placeholder="请选择作业类型">
            <Option value="network_config">网络配置</Option>
            <Option value="device_check">设备巡检</Option>
            <Option value="data_collection">数据采集</Option>
            <Option value="config_backup">配置备份</Option>
            <Option value="penetration_task">渗透任务</Option>
          </Select>
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit">
            {isEdit ? '保存' : '创建'}
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default JobForm; 