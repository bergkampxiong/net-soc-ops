import React, { useState, useEffect } from 'react';
import { Table, Button, Space, Input, Tag, message, Modal } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { processDefinitionApi } from '../../../api/process-designer';
import type { ProcessDefinition } from '../../../types/process-designer/pd-types';

const { Search } = Input;

export const ProcessList: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ProcessDefinition[]>([]);
  const [total, setTotal] = useState(0);
  const [current, setCurrent] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [keyword, setKeyword] = useState('');

  useEffect(() => {
    fetchData();
  }, [current, pageSize, keyword]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await processDefinitionApi.getList({
        page: current,
        pageSize,
        keyword,
      });
      setData(response.data.data || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      message.error('获取流程列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该流程定义吗？',
      onOk: async () => {
        try {
          await processDefinitionApi.delete(id);
          message.success('删除成功');
          fetchData();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap = {
          draft: { color: 'default', text: '草稿' },
          published: { color: 'success', text: '已发布' },
          disabled: { color: 'error', text: '已停用' },
        } as const;
        const { color, text } = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ProcessDefinition) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/process-designer/view/${record.id}`)}
          >
            查看
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/process-designer/edit/${record.id}`)}
          >
            编辑
          </Button>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => navigate(`/process-designer/execute/${record.id}`)}
          >
            执行
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="process-list">
      <div className="process-list-header">
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/process-designer/edit')}
          >
            新建流程
          </Button>
          <Search
            placeholder="搜索流程"
            allowClear
            onSearch={setKeyword}
            style={{ width: 200 }}
          />
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{
          current,
          pageSize,
          total,
          onChange: (page, size) => {
            setCurrent(page);
            setPageSize(size);
          },
        }}
      />
    </div>
  );
}; 