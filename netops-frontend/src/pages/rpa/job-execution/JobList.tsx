import React, { useState, useEffect } from 'react';
import { Table, Card, Button, Space, Tag, message, Modal, Form, Input, Select, DatePicker } from 'antd';
import { ReloadOutlined, DeleteOutlined, PlayCircleOutlined, PauseCircleOutlined, StopOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import request from '@/utils/request';
import { jobApi } from '@/api/job';
import type { Job } from './types';

const { RangePicker } = DatePicker;

const JobList: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [searchForm] = Form.useForm();
  const navigate = useNavigate();

  // 获取作业列表
  const fetchJobs = async (params: any = {}) => {
    try {
      setLoading(true);
      const reqParams = { skip: 0, limit: 100, ...params };
      const response = await request.get('/jobs', { params: reqParams });
      setJobs(response.data ?? []);
    } catch (error) {
      message.error('获取作业列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  // 表格列定义
  const columns = [
    {
      title: '作业名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Job) => (
        <a onClick={() => navigate(`/rpa/job-execution/jobs/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '作业类型',
      dataIndex: 'job_type',
      key: 'job_type',
      render: (v: string) => (v === 'config_backup' ? '配置备份' : v === 'penetration_task' ? '渗透任务' : v),
    },
    {
      title: '运行类型',
      dataIndex: 'run_type',
      key: 'run_type',
      render: (v: string) => (v === 'scheduled' ? '定期作业' : '一次作业'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap = {
          created: { color: 'default', text: '已创建' },
          active: { color: 'success', text: '运行中' },
          paused: { color: 'warning', text: '已暂停' },
          terminated: { color: 'error', text: '已终止' },
        };
        const { color, text } = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '最后执行时间',
      dataIndex: 'last_run_at',
      key: 'last_run_at',
      render: (time: string) => time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Job) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleExecute(record.id, record.job_type)}
            disabled={record.status === 'active'}
          >
            执行
          </Button>
          {record.status === 'active' ? (
            <Button
              type="link"
              icon={<PauseCircleOutlined />}
              onClick={() => handlePause(record.id)}
            >
              暂停
            </Button>
          ) : (
            <Button
              type="link"
              icon={<PlayCircleOutlined />}
              onClick={() => handleResume(record.id)}
              disabled={record.status !== 'paused'}
            >
              恢复
            </Button>
          )}
          <Button
            type="link"
            danger
            icon={<StopOutlined />}
            onClick={() => handleTerminate(record.id)}
            disabled={record.status === 'terminated'}
          >
            终止
          </Button>
          {record.run_type === 'once' && (
            <Button type="link" onClick={() => navigate(`/rpa/job-execution/jobs/${record.id}?convert=scheduled`)}>
              转为定期
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 操作处理函数
  const handleExecute = async (id: number, jobType?: string) => {
    try {
      const timeout = jobApi.getExecuteTimeout(jobType);
      await request.post(`/jobs/${id}/execute`, {}, { timeout });
      message.success('作业已开始执行');
      fetchJobs();
    } catch (error) {
      message.error('执行作业失败');
    }
  };

  const handlePause = async (id: number) => {
    try {
      await request.post(`/jobs/${id}/pause`);
      message.success('作业已暂停');
      fetchJobs();
    } catch (error) {
      message.error('暂停作业失败');
    }
  };

  const handleResume = async (id: number) => {
    try {
      await request.post(`/jobs/${id}/resume`);
      message.success('作业已恢复');
      fetchJobs();
    } catch (error) {
      message.error('恢复作业失败');
    }
  };

  const handleTerminate = async (id: number) => {
    try {
      await request.post(`/jobs/${id}/terminate`);
      message.success('作业已终止');
      fetchJobs();
    } catch (error) {
      message.error('终止作业失败');
    }
  };

  const handleBatchDelete = async () => {
    if (!selectedRowKeys.length) {
      message.warning('请选择要删除的作业');
      return;
    }

    Modal.confirm({
      title: '确认删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 个作业吗？`,
      onOk: async () => {
        try {
          await Promise.all(
            selectedRowKeys.map((id) => request.delete(`/jobs/${id}`))
          );
          message.success('删除成功');
          setSelectedRowKeys([]);
          fetchJobs();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const handleSearch = (values: any) => {
    const params: any = {};
    if (values.name) params.name = values.name;
    if (values.job_type) params.job_type = values.job_type;
    if (values.status) params.status = values.status;
    if (values.run_type) params.run_type = values.run_type;
    if (values.timeRange?.length === 2) {
      params.start_time = values.timeRange[0].toISOString();
      params.end_time = values.timeRange[1].toISOString();
    }
    fetchJobs(params);
  };

  return (
    <Card>
      <Form
        form={searchForm}
        onFinish={handleSearch}
        layout="inline"
        style={{ marginBottom: 16 }}
      >
        <Form.Item name="name">
          <Input placeholder="作业名称" allowClear />
        </Form.Item>
        <Form.Item name="job_type">
          <Select
            placeholder="作业类型"
            allowClear
            style={{ width: 120 }}
            options={[
              { label: '网络配置', value: 'network_config' },
              { label: '设备巡检', value: 'device_check' },
              { label: '数据采集', value: 'data_collection' },
            ]}
          />
        </Form.Item>
        <Form.Item name="status">
          <Select
            placeholder="状态"
            allowClear
            style={{ width: 120 }}
            options={[
              { label: '已创建', value: 'created' },
              { label: '运行中', value: 'active' },
              { label: '已暂停', value: 'paused' },
              { label: '已终止', value: 'terminated' },
            ]}
          />
        </Form.Item>
        <Form.Item name="run_type">
          <Select
            placeholder="运行类型"
            allowClear
            style={{ width: 120 }}
            options={[
              { label: '一次作业', value: 'once' },
              { label: '定期作业', value: 'scheduled' },
            ]}
          />
        </Form.Item>
        <Form.Item name="timeRange">
          <RangePicker showTime />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit">
              搜索
            </Button>
            <Button onClick={() => searchForm.resetFields()}>重置</Button>
          </Space>
        </Form.Item>
      </Form>

      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchJobs()}
          >
            刷新
          </Button>
          <Button
            danger
            icon={<DeleteOutlined />}
            onClick={handleBatchDelete}
            disabled={!selectedRowKeys.length}
          >
            批量删除
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={jobs}
        rowKey="id"
        loading={loading}
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />
    </Card>
  );
};

export default JobList; 