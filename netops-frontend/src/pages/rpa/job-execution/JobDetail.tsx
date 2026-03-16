import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Button,
  Space,
  Table,
  Tag,
  message,
  Modal,
  Form,
  Input,
  Select,
  Tabs,
  Typography,
  TimePicker,
  Collapse,
} from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { formatBeijingToSecond } from '@/utils/formatTime';
import { buildCronExpression, parseCronToPreset, formatScheduleSummary, type RecurrenceMode } from './scheduleCronUtils';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  EditOutlined,
  DeleteOutlined,
  RollbackOutlined,
  ReloadOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import request from '@/utils/request';
import { jobApi } from '@/api/job';
import { processDefinitionApi } from '@/api/process-designer';
import type { JobListItem, JobExecution } from './types';

const { Title } = Typography;
const { TabPane } = Tabs;

const JobDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [job, setJob] = useState<JobListItem | null>(null);
  const [executions, setExecutions] = useState<JobExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [executionLoading, setExecutionLoading] = useState(false);
  const [convertModalVisible, setConvertModalVisible] = useState(false);
  const [convertForm] = Form.useForm();
  const [processHasPenetrationTest, setProcessHasPenetrationTest] = useState(false);

  // 获取作业详情
  const fetchJobDetail = async () => {
    try {
      setLoading(true);
      const response = await request.get(`/jobs/${id}`);
      setJob(response.data);
    } catch (error) {
      message.error('获取作业详情失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取执行历史
  const fetchExecutions = async () => {
    try {
      setExecutionLoading(true);
      const response = await request.get(`/jobs/${id}/executions`);
      setExecutions(response.data);
    } catch (error) {
      message.error('获取执行历史失败');
    } finally {
      setExecutionLoading(false);
    }
  };

  useEffect(() => {
    fetchJobDetail();
    fetchExecutions();
  }, [id]);

  useEffect(() => {
    if (!job?.process_definition_id) {
      setProcessHasPenetrationTest(false);
      return;
    }
    processDefinitionApi
      .getDetail(job.process_definition_id)
      .then((res: any) => {
        const data = res?.data ?? res;
        const nodes = data?.nodes ?? [];
        setProcessHasPenetrationTest(Array.isArray(nodes) && nodes.some((n: any) => n.type === 'penetrationTest'));
      })
      .catch(() => setProcessHasPenetrationTest(false));
  }, [job?.process_definition_id]);

  const tabFromUrl = searchParams.get('tab');
  const defaultActiveKey = tabFromUrl === 'executions' ? 'executions' : 'basic';

  useEffect(() => {
    if (searchParams.get('convert') === 'scheduled' && job?.run_type === 'once') {
      setConvertModalVisible(true);
    }
  }, [searchParams, job?.run_type]);

  // 打开转为定期弹窗时，若已有 schedule_config 则尝试回填预设
  useEffect(() => {
    if (!convertModalVisible || !job) return;
    const config = job.schedule_config;
    if (config?.type === 'cron' && config.cron_expression) {
      const preset = parseCronToPreset(config.cron_expression);
      if (preset) {
        const [h, m] = preset.timeHHmm.split(':').map(Number);
        convertForm.setFieldsValue({
          scheduleMode: preset.recurrence,
          executionTime: dayjs().hour(h).minute(m).second(0).millisecond(0),
          dayOfWeek: preset.dayOfWeek,
          dayOfMonth: preset.dayOfMonth,
          timezone: config.timezone || 'Asia/Shanghai',
        });
        return;
      }
      convertForm.setFieldsValue({
        scheduleMode: 'advanced',
        advancedType: 'cron',
        cron_expression: config.cron_expression,
        timezone: config.timezone || 'Asia/Shanghai',
      });
      return;
    }
    if (config?.type === 'interval') {
      convertForm.setFieldsValue({
        scheduleMode: 'advanced',
        advancedType: 'interval',
        interval_seconds: config.interval_seconds,
        timezone: config.timezone || 'Asia/Shanghai',
      });
      return;
    }
    convertForm.setFieldsValue({
      scheduleMode: 'daily',
      executionTime: dayjs().hour(14).minute(0).second(0).millisecond(0),
      dayOfWeek: 1,
      dayOfMonth: 1,
      timezone: 'Asia/Shanghai',
    });
  }, [convertModalVisible, job?.schedule_config, job?.id]);

  const handleConvertToScheduled = async () => {
    try {
      const values = await convertForm.validateFields();
      const timezone = values.timezone || 'Asia/Shanghai';
      let scheduleConfig: { enabled: boolean; type: string; cron_expression?: string; interval_seconds?: number; timezone: string };
      if (values.scheduleMode === 'advanced') {
        if (values.advancedType === 'interval') {
          scheduleConfig = {
            enabled: true,
            type: 'interval',
            interval_seconds: values.interval_seconds,
            timezone,
          };
        } else {
          scheduleConfig = {
            enabled: true,
            type: 'cron',
            cron_expression: values.cron_expression,
            timezone,
          };
        }
      } else {
        const mode = values.scheduleMode as RecurrenceMode;
        const timeHHmm = values.executionTime ? (values.executionTime as Dayjs).format('HH:mm') : '14:00';
        const cron_expression = buildCronExpression(
          mode,
          timeHHmm,
          values.dayOfWeek,
          values.dayOfMonth
        );
        scheduleConfig = {
          enabled: true,
          type: 'cron',
          cron_expression,
          timezone,
        };
      }
      await request.put(`/jobs/${id}`, {
        name: job?.name,
        job_type: job?.job_type ?? 'config_backup',
        run_type: 'scheduled',
        schedule_config: scheduleConfig,
      });
      message.success(job?.run_type === 'scheduled' ? '调度已更新' : '已转为定期作业');
      setConvertModalVisible(false);
      convertForm.resetFields();
      fetchJobDetail();
    } catch (e) {
      message.error('操作失败');
    }
  };

  // 执行历史表格列定义
  const executionColumns = [
    {
      title: '执行ID',
      dataIndex: 'id',
      key: 'id',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap = {
          running: { color: 'processing', text: '执行中' },
          completed: { color: 'success', text: '已完成' },
          failed: { color: 'error', text: '失败' },
        };
        const { color, text } = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (time: string) => formatBeijingToSecond(time),
    },
    {
      title: '结束时间',
      dataIndex: 'end_time',
      key: 'end_time',
      render: (time: string) => formatBeijingToSecond(time),
    },
    {
      title: '执行结果',
      dataIndex: 'result',
      key: 'result',
      render: (result: any) => result ? JSON.stringify(result) : '-',
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      render: (error: string) => error || '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: JobExecution) => (
        <Space size="middle">
          {!processHasPenetrationTest && (
            <Button
              type="link"
              onClick={() => handleViewLogs(record)}
              disabled={!record.logs}
            >
              查看日志
            </Button>
          )}
          {processHasPenetrationTest && (
            <Button
              type="link"
              onClick={() => navigate(`/rpa/task-job-management/penetration-reports?job_execution_id=${record.id}`)}
            >
              查看渗透测试报告
            </Button>
          )}
          {record.status === 'failed' && (
            <Button
              type="link"
              onClick={() => handleRetry(record.id)}
            >
              重试
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 操作处理函数
  const handleExecute = async () => {
    try {
      const timeout = jobApi.getExecuteTimeout(job?.job_type);
      await request.post(`/jobs/${id}/execute`, {}, { timeout });
      message.success('作业已开始执行');
      fetchJobDetail();
      fetchExecutions();
    } catch (error) {
      message.error('执行作业失败');
    }
  };

  const handlePause = async () => {
    try {
      await request.post(`/jobs/${id}/pause`);
      message.success('作业已暂停');
      fetchJobDetail();
    } catch (error) {
      message.error('暂停作业失败');
    }
  };

  const handleResume = async () => {
    try {
      await request.post(`/jobs/${id}/resume`);
      message.success('作业已恢复');
      fetchJobDetail();
    } catch (error) {
      message.error('恢复作业失败');
    }
  };

  const handleTerminate = async () => {
    try {
      await request.post(`/jobs/${id}/terminate`);
      message.success('作业已终止');
      fetchJobDetail();
    } catch (error) {
      message.error('终止作业失败');
    }
  };

  const handleDelete = () => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该作业吗？',
      onOk: async () => {
        try {
          await request.delete(`/jobs/${id}`);
          message.success('删除成功');
          navigate('/rpa/job-execution/jobs');
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const handleViewLogs = (execution: JobExecution) => {
    Modal.info({
      title: '执行日志',
      width: 800,
      content: (
        <pre style={{ maxHeight: '500px', overflow: 'auto' }}>
          {execution.logs}
        </pre>
      ),
    });
  };

  const handleRetry = async (executionId: number) => {
    try {
      await request.post(`/jobs/${id}/retry/${executionId}`);
      message.success('作业已开始重试');
      fetchJobDetail();
      fetchExecutions();
    } catch (error) {
      message.error('重试作业失败');
    }
  };

  if (!job) {
    return null;
  }

  return (
    <div>
      <Card
        title={
          <Space>
            <Title level={4}>{job.name}</Title>
            <Tag color="blue">{job.job_type}</Tag>
            <Tag
              color={
                job.status === 'active'
                  ? 'success'
                  : job.status === 'paused'
                  ? 'warning'
                  : job.status === 'terminated'
                  ? 'error'
                  : 'default'
              }
            >
              {job.status === 'active'
                ? '运行中'
                : job.status === 'paused'
                ? '已暂停'
                : job.status === 'terminated'
                ? '已终止'
                : '已创建'}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleExecute}
              disabled={job.status === 'active'}
            >
              执行
            </Button>
            {job.status === 'active' ? (
              <Button
                icon={<PauseCircleOutlined />}
                onClick={handlePause}
              >
                暂停
              </Button>
            ) : (
              <Button
                icon={<PlayCircleOutlined />}
                onClick={handleResume}
                disabled={job.status !== 'paused'}
              >
                恢复
              </Button>
            )}
            <Button
              danger
              icon={<StopOutlined />}
              onClick={handleTerminate}
              disabled={job.status === 'terminated'}
            >
              终止
            </Button>
            {job.run_type === 'once' && (
              <Button
                icon={<CalendarOutlined />}
                onClick={() => setConvertModalVisible(true)}
              >
                转为定期
              </Button>
            )}
            {job.run_type === 'scheduled' && (
              <Button
                icon={<CalendarOutlined />}
                onClick={() => setConvertModalVisible(true)}
              >
                编辑调度
              </Button>
            )}
            <Button
              icon={<EditOutlined />}
              onClick={() => navigate(`/rpa/job-execution/jobs/${id}/edit`)}
            >
              编辑
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleDelete}
            >
              删除
            </Button>
            <Button
              icon={<RollbackOutlined />}
              onClick={() => navigate('/rpa/task-job-management/job-execution')}
            >
              返回
            </Button>
          </Space>
        }
      >
        <Tabs defaultActiveKey={defaultActiveKey}>
          <TabPane tab="基本信息" key="basic">
            <Descriptions bordered>
              <Descriptions.Item label="作业名称">{job.name}</Descriptions.Item>
              <Descriptions.Item label="作业类型">
                {job.job_type === 'config_backup' ? '配置备份' : job.job_type === 'penetration_task' ? '渗透任务' : job.job_type}
              </Descriptions.Item>
              <Descriptions.Item label="运行类型">
                {job.run_type === 'scheduled' ? '定期作业' : '一次作业'}
              </Descriptions.Item>
              {job.process_definition_id && (
                <Descriptions.Item label="关联流程">
                  <a onClick={() => navigate(`/rpa/process-orchestration/visual-designer/${job.process_definition_id}`)}>
                    {job.process_definition_id}
                  </a>
                </Descriptions.Item>
              )}
              <Descriptions.Item label="状态">
                {job.status === 'active'
                  ? '运行中'
                  : job.status === 'paused'
                  ? '已暂停'
                  : job.status === 'terminated'
                  ? '已终止'
                  : '已创建'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {formatBeijingToSecond(job.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {formatBeijingToSecond(job.updated_at)}
              </Descriptions.Item>
              <Descriptions.Item label="最后执行时间">
                {formatBeijingToSecond(job.last_run_at)}
              </Descriptions.Item>
              <Descriptions.Item label="下次执行时间">
                {formatBeijingToSecond(job.next_run_at)}
              </Descriptions.Item>
              <Descriptions.Item label="创建人">{job.created_by}</Descriptions.Item>
              <Descriptions.Item label="更新人">{job.updated_by}</Descriptions.Item>
              <Descriptions.Item label="描述" span={3}>
                {job.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="执行参数" span={3}>
                <pre>{JSON.stringify(job.parameters || {}, null, 2)}</pre>
              </Descriptions.Item>
              <Descriptions.Item label="调度配置" span={3}>
                <div>
                  {job.schedule_config && (
                    <div style={{ marginBottom: 8 }}>
                      {formatScheduleSummary(job.schedule_config)}
                    </div>
                  )}
                  <pre style={{ marginBottom: 0, fontSize: 12 }}>{JSON.stringify(job.schedule_config || {}, null, 2)}</pre>
                </div>
              </Descriptions.Item>
            </Descriptions>
          </TabPane>
          <TabPane tab="执行历史" key="executions">
            <Table
              columns={executionColumns}
              dataSource={executions}
              rowKey="id"
              loading={executionLoading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条`,
              }}
            />
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title={job?.run_type === 'scheduled' ? '编辑调度' : '转为定期作业'}
        open={convertModalVisible}
        onOk={handleConvertToScheduled}
        onCancel={() => { setConvertModalVisible(false); convertForm.resetFields(); }}
        okText="确定"
        cancelText="取消"
      >
        <Form form={convertForm} layout="vertical" initialValues={{ scheduleMode: 'daily', timezone: 'Asia/Shanghai' }}>
          <Form.Item name="scheduleMode" label="调度类型" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '每天', value: 'daily' },
                { label: '每周', value: 'weekly' },
                { label: '每月', value: 'monthly' },
                { label: '高级', value: 'advanced' },
              ]}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.scheduleMode !== cur.scheduleMode}>
            {({ getFieldValue }) => {
              const mode = getFieldValue('scheduleMode');
              if (mode === 'advanced') {
                return (
                  <Collapse ghost>
                    <Collapse.Panel header="自定义调度" key="1">
                      <Form.Item name="advancedType" label="类型" rules={[{ required: true }]}>
                        <Select
                          options={[
                            { label: 'Cron 表达式', value: 'cron' },
                            { label: '固定间隔(秒)', value: 'interval' },
                          ]}
                        />
                      </Form.Item>
                      <Form.Item noStyle shouldUpdate={(p, c) => p.advancedType !== c.advancedType}>
                        {({ getFieldValue: gf }) =>
                          gf('advancedType') === 'cron' ? (
                            <Form.Item name="cron_expression" label="Cron 表达式" rules={[{ required: true, message: '请输入 cron 表达式' }]}>
                              <Input placeholder="如 0 14 * * * 表示每天 14:00" />
                            </Form.Item>
                          ) : (
                            <Form.Item name="interval_seconds" label="间隔(秒)" rules={[{ required: true, message: '请输入间隔秒数' }]}>
                              <Input type="number" placeholder="如 3600" />
                            </Form.Item>
                          )
                        }
                      </Form.Item>
                    </Collapse.Panel>
                  </Collapse>
                );
              }
              return (
                <>
                  <Form.Item name="executionTime" label="执行时间" rules={[{ required: true, message: '请选择执行时间' }]}>
                    <TimePicker format="HH:mm" style={{ width: '100%' }} />
                  </Form.Item>
                  {mode === 'weekly' && (
                    <Form.Item name="dayOfWeek" label="星期" rules={[{ required: true }]}>
                      <Select
                        options={[
                          { label: '周一', value: 1 },
                          { label: '周二', value: 2 },
                          { label: '周三', value: 3 },
                          { label: '周四', value: 4 },
                          { label: '周五', value: 5 },
                          { label: '周六', value: 6 },
                          { label: '周日', value: 7 },
                        ]}
                      />
                    </Form.Item>
                  )}
                  {mode === 'monthly' && (
                    <Form.Item name="dayOfMonth" label="日期(几号)" rules={[{ required: true }]}>
                      <Select
                        options={Array.from({ length: 31 }, (_, i) => ({ label: `${i + 1} 号`, value: i + 1 }))}
                      />
                    </Form.Item>
                  )}
                </>
              );
            }}
          </Form.Item>
          <Form.Item name="timezone" label="时区">
            <Input placeholder="如 Asia/Shanghai" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default JobDetail; 