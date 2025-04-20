import React, { useState, useEffect } from 'react';
import { Card, Typography, Form, Input, Button, Space, message, Table, Modal, Select, Tag, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined, CopyOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import styles from './index.module.less';
import request from '../../../../utils/request';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

// 配置 dayjs 插件
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('Asia/Shanghai');

const { Title } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface ConfigFile {
  id: number;
  name: string;
  template_type: string;
  content: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
  device_type: string;
  status: string;
  description?: string;
  tags?: string[];
  versions?: Array<{
    version: number;
    content: string;
    comment: string;
    created_at: string;
    created_by: string;
  }>;
}

type TemplateType = 'jinja2' | 'textfsm' | 'job';

interface TemplateTypeInfo {
  color: string;
  text: string;
}

const TEMPLATE_TYPE_MAP: Record<TemplateType, TemplateTypeInfo> = {
  'jinja2': { color: 'blue', text: 'Jinja2 模板' },
  'textfsm': { color: 'green', text: 'TextFSM 模板' },
  'job': { color: 'orange', text: '作业配置' }
};

const getTemplateTypeInfo = (type: string): TemplateTypeInfo => {
  // 确保type是有效的模板类型
  const validType = type as TemplateType;
  return TEMPLATE_TYPE_MAP[validType] || { color: 'purple', text: '其他' };
};

const ConfigManagement: React.FC = () => {
  const [form] = Form.useForm();
  const [configs, setConfigs] = useState<ConfigFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ConfigFile | null>(null);
  const [searchText, setSearchText] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [currentType, setCurrentType] = useState<string>('jinja2');

  // 监听表单类型变化
  const handleTypeChange = (value: string) => {
    setCurrentType(value);
    form.setFieldsValue({ content: '' }); // 清空内容，避免格式不匹配
  };

  // 加载配置列表
  const fetchConfigs = async () => {
    setLoading(true);
    try {
      console.log('开始请求配置列表...');
      const response = await request.get('/api/config/files');
      console.log('收到API响应:', response);
      
      if (!response || !response.data) {
        console.error('API响应数据为空');
        return;
      }
      
      // 检查数据中的 template_type
      if (Array.isArray(response.data)) {
        console.log('配置列表数据:', response.data);
        response.data.forEach((item: any) => {
          console.log('配置项详情:', {
            id: item.id,
            name: item.name,
            template_type: item.template_type,
            device_type: item.device_type,
            status: item.status
          });
        });
      } else {
        console.error('API响应数据不是数组:', response.data);
      }
      
      setConfigs(response.data);
    } catch (error: any) {
      console.error('加载配置列表失败:', error);
      message.error('加载配置列表失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 组件加载时获取数据
  useEffect(() => {
    console.log('组件加载，开始获取配置列表');
    fetchConfigs();
  }, []);

  // 监听 configs 变化
  useEffect(() => {
    console.log('配置列表状态更新:', configs);
  }, [configs]);

  // 表格列定义
  const columns: ColumnsType<ConfigFile> = [
    {
      title: '配置名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => (
        <Tooltip title={text}>
          <span className={styles.configName}>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '配置类型',
      dataIndex: 'template_type',
      key: 'template_type',
      render: (type: string) => {
        const typeInfo = getTemplateTypeInfo(type);
        return (
          <Tag color={typeInfo.color}>
            {typeInfo.text}
          </Tag>
        );
      },
    },
    {
      title: '设备类型',
      dataIndex: 'device_type',
      key: 'device_type',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="编辑">
            <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Tooltip title="复制">
            <Button type="link" icon={<CopyOutlined />} onClick={() => handleCopy(record)} />
          </Tooltip>
          <Tooltip title="删除">
            <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 处理函数
  const handleAdd = () => {
    setEditingConfig(null);
    form.resetFields();
    setCurrentType('jinja2');
    form.setFieldsValue({ 
      template_type: 'jinja2',
      device_type: 'cisco_ios',
      status: 'draft'
    });
    setModalVisible(true);
  };

  const handleEdit = (record: ConfigFile) => {
    setEditingConfig(record);
    setCurrentType(record.template_type);
    form.setFieldsValue({
      name: record.name,
      template_type: record.template_type,
      device_type: record.device_type,
      content: record.content,
      status: record.status
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个配置吗？此操作不可恢复。',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await request.delete(`/api/config/files/${id}`);
          message.success('删除成功');
          setConfigs(configs.filter(config => config.id !== id));
        } catch (error: any) {
          message.error('删除失败: ' + (error.response?.data?.detail || error.message));
        }
      },
    });
  };

  const handleCopy = async (record: ConfigFile) => {
    try {
      const { id, ...copyData } = record;
      const response = await request.post('/api/config/files', {
        ...copyData,
        name: `${record.name}_copy`,
      });
      message.success('复制成功');
      setConfigs([...configs, response.data]);
    } catch (error: any) {
      message.error('复制失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      // 如果是作业配置，验证JSON格式
      if (values.template_type === 'job') {
        try {
          const jobConfig = JSON.parse(values.content);
          if (!jobConfig.name || !Array.isArray(jobConfig.steps)) {
            message.error('作业配置格式不正确');
            return;
          }
        } catch (e) {
          message.error('作业配置JSON格式不正确');
          return;
        }
      }

      if (editingConfig) {
        // 更新配置
        const response = await request.put(`/api/config/files/${editingConfig.id}`, {
          name: values.name,
          template_type: values.template_type,
          content: values.content,
          device_type: values.device_type,
          status: values.status || 'draft',
          description: values.description || null,
          tags: values.tags || []
        });
        
        message.success('更新成功');
        setConfigs(configs.map(config => 
          config.id === editingConfig.id ? response.data : config
        ));
      } else {
        // 创建新配置
        const response = await request.post('/api/config/files', {
          name: values.name,
          template_type: values.template_type,
          content: values.content,
          device_type: values.device_type,
          status: values.status || 'draft',
          description: values.description || null,
          tags: values.tags || []
        });
        
        setConfigs([...configs, response.data]);
        message.success('创建成功');
      }
      setModalVisible(false);
      form.resetFields();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || '操作失败';
      message.error(`操作失败: ${errorMessage}`);
    }
  };

  const handleModalCancel = () => {
    setModalVisible(false);
    form.resetFields();
    setEditingConfig(null);
  };

  const filteredConfigs = configs.filter(config => {
    const matchesSearch = config.name.toLowerCase().includes(searchText.toLowerCase());
    const matchesType = selectedType === 'all' || config.template_type === selectedType;
    return matchesSearch && matchesType;
  });

  return (
    <div className={styles.configManagement}>
      <Card className={styles.mainCard}>
        <div className={styles.header}>
          <Title level={4}>配置管理</Title>
        </div>

        <div className={styles.searchBar}>
          <Space>
            <Input
              placeholder="搜索配置名称"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              style={{ width: 300 }}
            />
            <Select
              value={selectedType}
              onChange={setSelectedType}
              style={{ width: 120 }}
              options={[
                { value: 'all', label: '全部类型' },
                { value: 'jinja2', label: 'Jinja2 模板' },
                { value: 'textfsm', label: 'TextFSM 模板' },
                { value: 'job', label: '作业配置' }
              ]}
            />
            <Button icon={<ReloadOutlined />} onClick={() => {
              setSearchText('');
              setSelectedType('all');
            }}>
              重置
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              新增配置
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={filteredConfigs}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1000 }}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      <Modal
        title={editingConfig ? "编辑配置" : "新增配置"}
        open={modalVisible}
        onOk={form.submit}
        onCancel={handleModalCancel}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            template_type: 'jinja2',
            device_type: 'cisco_ios',
            status: 'draft'
          }}
        >
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="请输入配置名称" />
          </Form.Item>

          <Form.Item
            name="template_type"
            label="模板类型"
            rules={[{ required: true, message: '请选择模板类型' }]}
          >
            <Select 
              onChange={handleTypeChange}
              options={[
                { value: 'jinja2', label: 'Jinja2 模板' },
                { value: 'textfsm', label: 'TextFSM 模板' },
                { value: 'job', label: '作业配置' }
              ]}
            />
          </Form.Item>

          <Form.Item
            name="device_type"
            label="设备类型"
            rules={[{ required: true, message: '请选择设备类型' }]}
          >
            <Select>
              <Option value="cisco_ios">Cisco IOS</Option>
              <Option value="huawei_vrp">Huawei VRP</Option>
              <Option value="h3c_comware">H3C Comware</Option>
              <Option value="ruijie_os">Ruijie OS</Option>
              <Option value="cisco_nxos">Cisco NXOS</Option>
              <Option value="cisco_xe">Cisco XE</Option>
              <Option value="cisco_xr">Cisco XR</Option>
              <Option value="linux">Linux</Option>
              <Option value="paloalto_panos">PaloAlto PANOS</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="content"
            label="配置内容"
            rules={[{ required: true, message: '请输入配置内容' }]}
            extra={currentType === 'job' ? '请输入JSON格式的作业配置，例如：\n{\n  "name": "示例作业",\n  "steps": [\n    {\n      "type": "command",\n      "command": "show version"\n    }\n  ]\n}' : undefined}
          >
            <TextArea 
              rows={15} 
              placeholder={currentType === 'job' ? 
                '请输入JSON格式的作业配置' : 
                '请输入配置内容'
              } 
            />
          </Form.Item>

          <Form.Item
            name="status"
            label="状态"
            rules={[{ required: true, message: '请选择状态' }]}
          >
            <Select>
              <Option value="draft">草稿</Option>
              <Option value="published">已发布</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigManagement; 