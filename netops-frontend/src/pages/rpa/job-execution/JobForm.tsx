import React, { useEffect } from 'react';
import { Form, Input, Select, Button, Card, Space, TimePicker, InputNumber, Switch } from 'antd';
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
        initialValues={{
          schedule_config: {
            enabled: false,
            type: 'manual',
          },
        }}
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
          </Select>
        </Form.Item>

        <Form.Item
          name={['schedule_config', 'enabled']}
          label="启用调度"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item
          noStyle
          shouldUpdate={(prevValues, currentValues) =>
            prevValues.schedule_config?.enabled !== currentValues.schedule_config?.enabled
          }
        >
          {({ getFieldValue }) =>
            getFieldValue(['schedule_config', 'enabled']) && (
              <>
                <Form.Item
                  name={['schedule_config', 'type']}
                  label="调度类型"
                  rules={[{ required: true, message: '请选择调度类型' }]}
                >
                  <Select placeholder="请选择调度类型">
                    <Option value="manual">手动执行</Option>
                    <Option value="cron">Cron表达式</Option>
                    <Option value="interval">间隔时间</Option>
                    <Option value="calendar">日历规则</Option>
                  </Select>
                </Form.Item>

                <Form.Item
                  noStyle
                  shouldUpdate={(prevValues, currentValues) =>
                    prevValues.schedule_config?.type !== currentValues.schedule_config?.type
                  }
                >
                  {({ getFieldValue }) => {
                    const scheduleType = getFieldValue(['schedule_config', 'type']);
                    switch (scheduleType) {
                      case 'cron':
                        return (
                          <Form.Item
                            name={['schedule_config', 'cron_expression']}
                            label="Cron表达式"
                            rules={[{ required: true, message: '请输入Cron表达式' }]}
                          >
                            <Input placeholder="请输入Cron表达式" />
                          </Form.Item>
                        );
                      case 'interval':
                        return (
                          <Form.Item
                            name={['schedule_config', 'interval_seconds']}
                            label="间隔时间(秒)"
                            rules={[{ required: true, message: '请输入间隔时间' }]}
                          >
                            <InputNumber min={1} />
                          </Form.Item>
                        );
                      case 'calendar':
                        return (
                          <>
                            <Form.Item
                              name={['schedule_config', 'calendar_rules']}
                              label="日历规则"
                              rules={[{ required: true, message: '请设置日历规则' }]}
                            >
                              <Select mode="multiple" placeholder="请选择执行日期">
                                <Option value="monday">周一</Option>
                                <Option value="tuesday">周二</Option>
                                <Option value="wednesday">周三</Option>
                                <Option value="thursday">周四</Option>
                                <Option value="friday">周五</Option>
                                <Option value="saturday">周六</Option>
                                <Option value="sunday">周日</Option>
                              </Select>
                            </Form.Item>
                            <Form.Item
                              name={['schedule_config', 'time']}
                              label="执行时间"
                              rules={[{ required: true, message: '请选择执行时间' }]}
                            >
                              <TimePicker format="HH:mm" />
                            </Form.Item>
                          </>
                        );
                      default:
                        return null;
                    }
                  }}
                </Form.Item>

                <Form.Item
                  name={['schedule_config', 'timezone']}
                  label="时区"
                  initialValue="Asia/Shanghai"
                >
                  <Select>
                    <Option value="Asia/Shanghai">中国标准时间 (UTC+8)</Option>
                    <Option value="UTC">世界标准时间 (UTC)</Option>
                  </Select>
                </Form.Item>

                <Form.Item
                  name={['schedule_config', 'retry_policy']}
                  label="重试策略"
                >
                  <Space>
                    <Form.Item
                      name={['schedule_config', 'retry_policy', 'max_retries']}
                      noStyle
                    >
                      <InputNumber min={0} placeholder="最大重试次数" />
                    </Form.Item>
                    <Form.Item
                      name={['schedule_config', 'retry_policy', 'retry_interval']}
                      noStyle
                    >
                      <InputNumber min={1} placeholder="重试间隔(秒)" />
                    </Form.Item>
                  </Space>
                </Form.Item>

                <Form.Item
                  name={['schedule_config', 'timeout']}
                  label="超时时间(秒)"
                >
                  <InputNumber min={1} />
                </Form.Item>

                <Form.Item
                  name={['schedule_config', 'concurrent_limit']}
                  label="并发限制"
                >
                  <InputNumber min={1} />
                </Form.Item>
              </>
            )
          }
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              {isEdit ? '保存' : '创建'}
            </Button>
            <Button onClick={() => navigate('/rpa/task-job-management/job-execution')}>
              取消
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default JobForm; 