import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Tag, Space, message, Upload, DatePicker, Row, Col, Tooltip, Drawer } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, HistoryOutlined, CopyOutlined, ImportOutlined, ExportOutlined, SearchOutlined, RollbackOutlined, DiffOutlined, FormatPainterOutlined } from '@ant-design/icons';
import MonacoEditor from '@monaco-editor/react';
import request from '../../utils/request';
import type { RangePickerProps } from 'antd/es/date-picker';
import moment from 'moment';
import ConfigEditor from '../../components/ConfigEditor';
import ConfigVersionDiff from '../../components/ConfigVersionDiff';

const { Option } = Select;
const { RangePicker } = DatePicker;

interface ConfigFile {
  id: string;
  name: string;
  device_type: string;
  content: string;
  description: string;
  tags: string[];
  status: string;
  template_type: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}

interface Version {
  id: string;
  version: number;
  content: string;
  created_at: string;
  created_by: string;
}

interface SearchParams {
  name?: string;
  device_type?: string;
  tags?: string[];
  status?: string;
  dateRange?: [string, string];
}

const ConfigManagement: React.FC = () => {
  const [configs, setConfigs] = useState<ConfigFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ConfigFile | null>(null);
  const [form] = Form.useForm();
  const [versionModalVisible, setVersionModalVisible] = useState(false);
  const [versions, setVersions] = useState<Version[]>([]);
  const [searchParams, setSearchParams] = useState<SearchParams>({});
  const [searchForm] = Form.useForm();
  const [diffModalVisible, setDiffModalVisible] = useState(false);
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);
  const [versionDiffData, setVersionDiffData] = useState<{original: string, modified: string}>({ original: '', modified: '' });
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [previewDrawerVisible, setPreviewDrawerVisible] = useState(false);
  const [previewData, setPreviewData] = useState({ content: '', deviceType: '' });

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const response = await request.get('/api/config/files');
      setConfigs(response.data);
    } catch (error) {
      message.error('获取配置列表失败');
    }
    setLoading(false);
  };

  const handleCreate = () => {
    form.resetFields();
    setEditingConfig(null);
    setModalVisible(true);
  };

  const handleEdit = (record: ConfigFile) => {
    setEditingConfig(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await request.delete(`/api/config/files/${id}`);
      message.success('删除成功');
      fetchConfigs();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleViewVersions = async (id: string) => {
    try {
      const response = await request.get(`/api/config/files/${id}/versions`);
      setVersions(response.data);
      setVersionModalVisible(true);
    } catch (error) {
      message.error('获取版本历史失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingConfig) {
        await request.put(`/api/config/files/${editingConfig.id}`, values);
        message.success('更新成功');
      } else {
        await request.post('/api/config/files', values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchConfigs();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleCopy = async (record: ConfigFile) => {
    try {
      const newConfig = {
        ...record,
        name: `${record.name}_copy`,
        id: undefined,
        created_at: undefined,
        updated_at: undefined,
      };
      await request.post('/api/config/files', newConfig);
      message.success('复制成功');
      fetchConfigs();
    } catch (error) {
      message.error('复制失败');
    }
  };

  const handleExport = async (record: ConfigFile) => {
    try {
      const response = await request.get(`/api/config/files/${record.id}/export`, {
        responseType: 'blob'
      });
      const blob = new Blob([response.data], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${record.name}.txt`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      message.error('导出失败');
    }
  };

  const handleImport = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      await request.post('/api/config/files/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      message.success('导入成功');
      fetchConfigs();
      return false; // 阻止自动上传
    } catch (error) {
      message.error('导入失败');
      return false;
    }
  };

  const handleSearch = async (values: SearchParams) => {
    setSearchParams(values);
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (values.name) params.append('name', values.name);
      if (values.device_type) params.append('device_type', values.device_type);
      if (values.tags?.length) params.append('tags', values.tags.join(','));
      if (values.status) params.append('status', values.status);
      if (values.dateRange) {
        params.append('start_date', values.dateRange[0]);
        params.append('end_date', values.dateRange[1]);
      }
      const response = await request.get(`/api/config/files?${params.toString()}`);
      setConfigs(response.data);
    } catch (error) {
      message.error('搜索失败');
    }
    setLoading(false);
  };

  const handleVersionCompare = () => {
    if (selectedVersions.length !== 2) {
      message.warning('请选择两个版本进行比较');
      return;
    }
    const [v1, v2] = selectedVersions;
    setVersionDiffData({
      original: versions.find(v => v.id === v1)?.content || '',
      modified: versions.find(v => v.id === v2)?.content || ''
    });
    setDiffModalVisible(true);
  };

  const handleVersionRollback = async (versionId: string) => {
    try {
      const version = versions.find(v => v.id === versionId);
      if (!version) return;

      await request.put(`/api/config/files/${editingConfig?.id}`, {
        content: version.content
      });
      message.success('回滚成功');
      setVersionModalVisible(false);
      fetchConfigs();
    } catch (error) {
      message.error('回滚失败');
    }
  };

  const handlePreview = (version: Version) => {
    setPreviewData({
      content: version.content,
      deviceType: editingConfig?.device_type || ''
    });
    setPreviewDrawerVisible(true);
  };

  const configColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '设备类型',
      dataIndex: 'device_type',
      key: 'device_type',
    },
    {
      title: '模板类型',
      dataIndex: 'template_type',
      key: 'template_type',
      render: (type: string) => (
        <Tag color={type === 'jinja2' ? 'blue' : 'purple'}>
          {type === 'jinja2' ? 'Jinja2' : 'TextFSM'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'published' ? 'green' : 'orange'}>
          {status === 'published' ? '已发布' : '草稿'}
        </Tag>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ConfigFile) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="text"
            icon={<CopyOutlined />}
            onClick={() => handleCopy(record)}
          >
            复制
          </Button>
          <Button
            type="text"
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

  const versionColumns = [
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Version) => (
        <Space>
          <Button
            type="link"
            onClick={() => handleVersionRollback(record.id)}
            icon={<RollbackOutlined />}
          >
            回滚
          </Button>
          <Button
            type="link"
            onClick={() => handlePreview(record)}
            icon={<SearchOutlined />}
          >
            预览
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="config-management">
      <Card>
        <Form
          form={searchForm}
          layout="horizontal"
          onFinish={handleSearch}
          style={{ marginBottom: 16 }}
        >
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="name" label="配置名称">
                <Input placeholder="请输入配置名称" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="device_type" label="设备类型">
                <Select allowClear placeholder="请选择设备类型">
                  <Option value="cisco_ios">Cisco IOS</Option>
                  <Option value="huawei_vrp">Huawei VRP</Option>
                  <Option value="hpe_comware7">HPE Comware7</Option>
                  <Option value="ruijie_os">Ruijie OS</Option>
                  <Option value="cisco_nxos">Cisco NXOS</Option>
                  <Option value="cisco_xe">Cisco XE</Option>
                  <Option value="cisco_xr">Cisco XR</Option>
                  <Option value="linux">Linux</Option>
                  <Option value="paloalto_panos">PaloAlto PANOS</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="status" label="状态">
                <Select allowClear placeholder="请选择状态">
                  <Option value="draft">草稿</Option>
                  <Option value="published">已发布</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="dateRange" label="时间范围">
                <RangePicker />
              </Form.Item>
            </Col>
          </Row>
          <Row>
            <Col span={24} style={{ textAlign: 'right' }}>
              <Space>
                <Button type="primary" icon={<SearchOutlined />} htmlType="submit">
                  搜索
                </Button>
                <Button onClick={() => searchForm.resetFields()}>
                  重置
                </Button>
                <Upload
                  accept=".txt,.cfg"
                  showUploadList={false}
                  beforeUpload={handleImport}
                >
                  <Button icon={<ImportOutlined />}>
                    导入配置
                  </Button>
                </Upload>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  新建配置
                </Button>
              </Space>
            </Col>
          </Row>
        </Form>

        <Table
          columns={configColumns}
          dataSource={configs}
          loading={loading}
          rowKey="id"
        />
      </Card>

      <Modal
        title={editingConfig ? '编辑配置' : '新建配置'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={1200}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="template_type"
            label="模板类型"
            rules={[{ required: true }]}
            initialValue="jinja2"
          >
            <Select>
              <Option value="jinja2">Jinja2 模板</Option>
              <Option value="textfsm">TextFSM 模板</Option>
              <Option value="job">作业配置</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="device_type"
            label="设备类型"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="cisco_ios">Cisco IOS</Option>
              <Option value="huawei_vrp">Huawei VRP</Option>
              <Option value="hpe_comware7">HPE Comware7</Option>
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
            rules={[{ required: true }]}
          >
            <ConfigEditor
              value={form.getFieldValue('content') || ''}
              onChange={(value) => form.setFieldsValue({ content: value })}
              deviceType={form.getFieldValue('device_type') || ''}
              templateType={form.getFieldValue('template_type') || 'jinja2'}
              height="400px"
            />
          </Form.Item>
          <Form.Item
            name="status"
            label="状态"
            initialValue="draft"
          >
            <Select>
              <Option value="draft">草稿</Option>
              <Option value="published">已发布</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="版本比较"
        open={diffModalVisible}
        onCancel={() => setDiffModalVisible(false)}
        width={1200}
        footer={null}
      >
        <ConfigVersionDiff
          originalContent={versionDiffData.original}
          modifiedContent={versionDiffData.modified}
          height="600px"
        />
      </Modal>

      <Drawer
        title="变更预览"
        placement="right"
        width={800}
        onClose={() => setPreviewDrawerVisible(false)}
        open={previewDrawerVisible}
      >
        <ConfigEditor
          value={previewData.content}
          onChange={() => {}}
          deviceType={previewData.deviceType}
          templateType={editingConfig?.template_type || 'jinja2'}
          readOnly
        />
      </Drawer>

      <Modal
        title="版本历史"
        open={versionModalVisible}
        onCancel={() => setVersionModalVisible(false)}
        width={1000}
        footer={null}
      >
        <Table
          rowSelection={{
            type: 'checkbox',
            selectedRowKeys: selectedVersions,
            onChange: (selectedRowKeys) => setSelectedVersions(selectedRowKeys as string[])
          }}
          columns={versionColumns}
          dataSource={versions}
          rowKey="id"
        />
      </Modal>
    </div>
  );
};

export default ConfigManagement; 