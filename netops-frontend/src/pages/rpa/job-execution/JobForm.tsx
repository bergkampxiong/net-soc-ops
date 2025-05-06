import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  message,
  Divider,
  TimePicker,
  InputNumber,
  Switch,
} from 'antd';
import { RollbackOutlined } from '@ant-design/icons';
import request from '../../../utils/request';
import type { JobFormData } from './types';

const { TextArea } = Input;
const { Option } = Select;

const JobForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [scheduleType, setScheduleType] = useState<'manual' | 'cron' | 'interval'>('manual');

  // 获取作业详情
  const fetchJobDetail = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const response = await request.get(`/jobs/${id}`);
      const job = response.data;
      form.setFieldsValue({
        ...job,
        schedule_config: {
          type: job.schedule_config?.type || 'manual',
          cron_expression: job.schedule_config?.cron_expression,
          interval_seconds: job.schedule_config?.interval_seconds,
          start_time: job.schedule_config?.start_time,
          end_time: job.schedule_config?.end_time,
          timezone: job.schedule_config?.timezone,
        },
      });
      setScheduleType(job.schedule_config?.type || 'manual');
    } catch (error) {
      message.error('获取作业详情失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchJobDetail();
    }
  }, [id]);

  // 提交表单
  const handleSubmit = async (values: JobFormData) => {
    try {
      setLoading(true);
      if (id) {
        await request.put(`/jobs/${id}`, values);
        message.success('更新作业成功');
      } else {
        await request.post('/jobs', values);
        message.success('创建作业成功');
      }
      navigate('/rpa/job-execution/jobs');
    } catch (error) {
      message.error(id ? '更新作业失败' : '创建作业失败');
    } finally {
      setLoading(false);
    }
  };

  // 渲染调度配置表单
  const renderScheduleConfig = () => {
    switch (scheduleType) {
      case 'cron':
        return (
          <>
            <Form.Item
              label="Cron表达式"
              name={['schedule_config', 'cron_expression']}
              rules={[{ required: true, message: '请输入Cron表达式' }]}
            >
              <Input placeholder="例如: 0 0 * * *" />
            </Form.Item>
            <Form.Item
              label="时区"
              name={['schedule_config', 'timezone']}
              initialValue="Asia/Shanghai"
            >
              <Select>
                <Option value="Asia/Shanghai">Asia/Shanghai</Option>
                <Option value="UTC">UTC</Option>
              </Select>
            </Form.Item>
          </>
        );
      case 'interval':
        return (
          <>
            <Form.Item
              label="间隔时间(秒)"
              name={['schedule_config', 'interval_seconds']}
              rules={[{ required: true, message: '请输入间隔时间' }]}
            >
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item
              label="开始时间"
              name={['schedule_config', 'start_time']}
            >
              <TimePicker format="HH:mm:ss" />
            </Form.Item>
            <Form.Item
              label="结束时间"
              name={['schedule_config', 'end_time']}
            >
              <TimePicker format="HH:mm:ss" />
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <Card
      title={id ? '编辑作业' : '新建作业'}
      extra={
        <Button
          icon={<RollbackOutlined />}
          onClick={() => navigate('/rpa/job-execution/jobs')}
        >
          返回
        </Button>
      }
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          schedule_config: {
            type: 'manual',
          },
        }}
      >
        <Form.Item
          label="作业名称"
          name="name"
          rules={[{ required: true, message: '请输入作业名称' }]}
        >
          <Input placeholder="请输入作业名称" />
        </Form.Item>

        <Form.Item
          label="作业描述"
          name="description"
        >
          <TextArea rows={4} placeholder="请输入作业描述" />
        </Form.Item>

        <Form.Item
          label="作业类型"
          name="job_type"
          rules={[{ required: true, message: '请选择作业类型' }]}
        >
          <Select placeholder="请选择作业类型">
            <Option value="network_config">网络配置</Option>
            <Option value="device_check">设备巡检</Option>
            <Option value="data_collection">数据采集</Option>
          </Select>
        </Form.Item>

        <Divider>调度配置</Divider>

        <Form.Item
          label="执行方式"
          name={['schedule_config', 'type']}
          rules={[{ required: true, message: '请选择执行方式' }]}
        >
          <Select onChange={(value) => setScheduleType(value)}>
            <Option value="manual">手动执行</Option>
            <Option value="cron">Cron调度</Option>
            <Option value="interval">间隔执行</Option>
          </Select>
        </Form.Item>

        {renderScheduleConfig()}

        <Divider>高级配置</Divider>

        <Form.Item
          label="执行参数"
          name="parameters"
          tooltip="JSON格式的执行参数"
        >
          <TextArea
            rows={4}
            placeholder='{"key": "value"}'
          />
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              {id ? '更新' : '创建'}
            </Button>
            <Button onClick={() => navigate('/rpa/job-execution/jobs')}>
              取消
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default JobForm; 