import React, { useState, useEffect } from 'react';
import { 
  Card, Table, Button, Space, Tag, Typography, message, 
  Row, Col, Input, Modal, Form, Select, DatePicker, Statistic 
} from 'antd';
import { 
  SearchOutlined, ReloadOutlined, CheckCircleOutlined, 
  CloseCircleOutlined, WarningOutlined, SyncOutlined,
  FileExcelOutlined, CheckOutlined, ClockCircleOutlined
} from '@ant-design/icons';
import request from '../../utils/request';
import moment from 'moment';
import './Inventory.css';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

// 盘点状态定义
enum InventoryStatus {
  PENDING = 'pending',
  VERIFIED = 'verified',
  MISSING = 'missing',
  EXCEPTION = 'exception'
}

// 盘点状态颜色映射
const statusColors: Record<string, string> = {
  [InventoryStatus.PENDING]: 'default',
  [InventoryStatus.VERIFIED]: 'success',
  [InventoryStatus.MISSING]: 'error',
  [InventoryStatus.EXCEPTION]: 'warning'
};

// 盘点状态图标映射
const statusIcons: Record<string, React.ReactNode> = {
  [InventoryStatus.PENDING]: <ClockCircleOutlined />,
  [InventoryStatus.VERIFIED]: <CheckCircleOutlined />,
  [InventoryStatus.MISSING]: <CloseCircleOutlined />,
  [InventoryStatus.EXCEPTION]: <WarningOutlined />
};

// 盘点状态文本映射
const statusTexts: Record<string, string> = {
  [InventoryStatus.PENDING]: '待盘点',
  [InventoryStatus.VERIFIED]: '已确认',
  [InventoryStatus.MISSING]: '未找到',
  [InventoryStatus.EXCEPTION]: '异常'
};

/**
 * CMDB资产盘点组件
 */
const CMDBInventory: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [assets, setAssets] = useState<any[]>([]);
  const [filteredAssets, setFilteredAssets] = useState<any[]>([]);
  const [searchText, setSearchText] = useState<string>('');
  const [inventoryStatus, setInventoryStatus] = useState<Record<number, InventoryStatus>>({});
  const [inventoryNotes, setInventoryNotes] = useState<Record<number, string>>({});
  const [inventoryDate, setInventoryDate] = useState<string>(moment().format('YYYY-MM-DD'));
  const [verifyModalVisible, setVerifyModalVisible] = useState<boolean>(false);
  const [currentAsset, setCurrentAsset] = useState<any>(null);
  const [form] = Form.useForm();
  const [inventoryStats, setInventoryStats] = useState({
    total: 0,
    verified: 0,
    missing: 0,
    exception: 0,
    pending: 0
  });

  // 组件挂载时获取数据
  useEffect(() => {
    fetchAssets();
  }, []);

  // 当资产或状态变化时，更新过滤后的资产和统计数据
  useEffect(() => {
    filterAssets();
    updateStats();
  }, [assets, inventoryStatus, searchText]);

  // 获取资产数据
  const fetchAssets = async () => {
    setLoading(true);
    try {
      const response = await request.get('/api/cmdb/assets');
      setAssets(response.data);
      
      // 初始化盘点状态
      const initialStatus: Record<number, InventoryStatus> = {};
      response.data.forEach((asset: any) => {
        initialStatus[asset.id] = InventoryStatus.PENDING;
      });
      setInventoryStatus(initialStatus);
      
    } catch (error) {
      console.error('获取资产数据失败:', error);
      message.error('获取资产数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 过滤资产
  const filterAssets = () => {
    if (!searchText) {
      setFilteredAssets(assets);
      return;
    }

    const filtered = assets.filter(asset => {
      const searchLower = searchText.toLowerCase();
      return (
        (asset.name && asset.name.toLowerCase().includes(searchLower)) ||
        (asset.ip_address && asset.ip_address.toLowerCase().includes(searchLower)) ||
        (asset.device_type && asset.device_type.name.toLowerCase().includes(searchLower)) ||
        (asset.vendor && asset.vendor.name && asset.vendor.name.toLowerCase().includes(searchLower)) ||
        (asset.location && asset.location.name && asset.location.name.toLowerCase().includes(searchLower))
      );
    });

    setFilteredAssets(filtered);
  };

  // 更新统计数据
  const updateStats = () => {
    const stats = {
      total: assets.length,
      verified: 0,
      missing: 0,
      exception: 0,
      pending: 0
    };

    Object.values(inventoryStatus).forEach(status => {
      switch (status) {
        case InventoryStatus.VERIFIED:
          stats.verified++;
          break;
        case InventoryStatus.MISSING:
          stats.missing++;
          break;
        case InventoryStatus.EXCEPTION:
          stats.exception++;
          break;
        case InventoryStatus.PENDING:
          stats.pending++;
          break;
      }
    });

    setInventoryStats(stats);
  };

  // 处理搜索
  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  // 打开验证模态框
  const showVerifyModal = (asset: any) => {
    setCurrentAsset(asset);
    form.setFieldsValue({
      status: inventoryStatus[asset.id] || InventoryStatus.PENDING,
      notes: inventoryNotes[asset.id] || ''
    });
    setVerifyModalVisible(true);
  };

  // 处理验证提交
  const handleVerifySubmit = () => {
    form.validateFields().then(values => {
      if (!currentAsset) return;

      // 更新状态和备注
      setInventoryStatus(prev => ({
        ...prev,
        [currentAsset.id]: values.status
      }));

      setInventoryNotes(prev => ({
        ...prev,
        [currentAsset.id]: values.notes
      }));

      setVerifyModalVisible(false);
      message.success(`设备 ${currentAsset.name} 盘点状态已更新`);
    });
  };

  // 导出盘点结果
  const exportInventory = () => {
    // 创建CSV内容
    const headers = ['设备名称', 'IP地址', '设备类型', '厂商', '位置', '盘点状态', '盘点备注'];
    
    const rows = assets.map(asset => [
      asset.name || '',
      asset.ip_address || '',
      asset.device_type?.name || '',
      asset.vendor?.name || '',
      asset.location?.name || '',
      statusTexts[inventoryStatus[asset.id] || InventoryStatus.PENDING],
      inventoryNotes[asset.id] || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => {
        // 如果值包含逗号，用双引号包裹
        if (String(cell).includes(',')) {
          return `"${cell}"`;
        }
        return String(cell);
      }).join(','))
    ].join('\n');

    // 添加BOM标记，确保Excel正确识别UTF-8编码
    const BOM = "\uFEFF";
    const csvContentWithBOM = BOM + csvContent;

    // 创建下载链接
    const blob = new Blob([csvContentWithBOM], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `资产盘点结果_${inventoryDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 重置盘点状态
  const resetInventory = () => {
    Modal.confirm({
      title: '确定要重置所有盘点状态吗?',
      content: '这将把所有设备的盘点状态重置为"待盘点"',
      onOk: () => {
        const resetStatus: Record<number, InventoryStatus> = {};
        assets.forEach(asset => {
          resetStatus[asset.id] = InventoryStatus.PENDING;
        });
        setInventoryStatus(resetStatus);
        setInventoryNotes({});
        message.success('盘点状态已重置');
      }
    });
  };

  // 表格列定义
  const columns = [
    {
      title: '设备名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: '设备类型',
      dataIndex: 'device_type',
      key: 'device_type',
      render: (deviceType: any) => deviceType?.name || '-',
    },
    {
      title: '厂商',
      dataIndex: 'vendor',
      key: 'vendor',
      render: (vendor: any) => vendor?.name || '-',
    },
    {
      title: '位置',
      dataIndex: 'location',
      key: 'location',
      render: (location: any) => location?.name || '-',
    },
    {
      title: '盘点状态',
      key: 'inventory_status',
      render: (_: any, record: any) => {
        const status = inventoryStatus[record.id] || InventoryStatus.PENDING;
        return (
          <Tag icon={statusIcons[status]} color={statusColors[status]}>
            {statusTexts[status]}
          </Tag>
        );
      },
      filters: [
        { text: '待盘点', value: InventoryStatus.PENDING },
        { text: '已确认', value: InventoryStatus.VERIFIED },
        { text: '未找到', value: InventoryStatus.MISSING },
        { text: '异常', value: InventoryStatus.EXCEPTION },
      ],
      onFilter: (value: any, record: any) => 
        (inventoryStatus[record.id] || InventoryStatus.PENDING) === value,
    },
    {
      title: '盘点备注',
      key: 'inventory_notes',
      render: (_: any, record: any) => inventoryNotes[record.id] || '-',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button 
          type="primary" 
          size="small" 
          icon={<CheckOutlined />}
          onClick={() => showVerifyModal(record)}
        >
          盘点
        </Button>
      ),
    },
  ];

  return (
    <div className="cmdb-inventory-page">
      <Card title="资产盘点" className="inventory-card">
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Paragraph>
              当前盘点日期: <Text strong>{inventoryDate}</Text>
            </Paragraph>
          </Col>
          
          <Col xs={24} sm={12} md={6}>
            <Statistic 
              title="总设备数" 
              value={inventoryStats.total} 
              prefix={<SyncOutlined />} 
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic 
              title="已确认" 
              value={inventoryStats.verified} 
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />} 
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic 
              title="未找到" 
              value={inventoryStats.missing} 
              valueStyle={{ color: '#f5222d' }}
              prefix={<CloseCircleOutlined />} 
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic 
              title="异常" 
              value={inventoryStats.exception} 
              valueStyle={{ color: '#faad14' }}
              prefix={<WarningOutlined />} 
            />
          </Col>
          
          <Col span={24}>
            <Row justify="space-between" align="middle">
              <Col>
                <Space>
                  <Input.Search
                    placeholder="搜索设备名称、IP地址、类型..."
                    allowClear
                    enterButton
                    onSearch={handleSearch}
                    style={{ width: 300 }}
                  />
                  <Button 
                    icon={<ReloadOutlined />} 
                    onClick={() => {
                      setSearchText('');
                      fetchAssets();
                    }}
                  >
                    刷新
                  </Button>
                </Space>
              </Col>
              <Col>
                <Space>
                  <Button 
                    icon={<ReloadOutlined />} 
                    onClick={resetInventory}
                  >
                    重置盘点
                  </Button>
                  <Button 
                    type="primary" 
                    icon={<FileExcelOutlined />} 
                    onClick={exportInventory}
                    disabled={assets.length === 0}
                  >
                    导出盘点结果
                  </Button>
                </Space>
              </Col>
            </Row>
          </Col>
          
          <Col span={24}>
            <Table
              columns={columns}
              dataSource={filteredAssets}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
            />
          </Col>
        </Row>
      </Card>

      {/* 盘点验证模态框 */}
      <Modal
        title={`盘点设备: ${currentAsset?.name || ''}`}
        open={verifyModalVisible}
        onCancel={() => setVerifyModalVisible(false)}
        onOk={handleVerifySubmit}
        okText="确认"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="status"
            label="盘点状态"
            rules={[{ required: true, message: '请选择盘点状态' }]}
          >
            <Select>
              <Option value={InventoryStatus.VERIFIED}>
                <Tag icon={statusIcons[InventoryStatus.VERIFIED]} color={statusColors[InventoryStatus.VERIFIED]}>
                  已确认
                </Tag>
              </Option>
              <Option value={InventoryStatus.MISSING}>
                <Tag icon={statusIcons[InventoryStatus.MISSING]} color={statusColors[InventoryStatus.MISSING]}>
                  未找到
                </Tag>
              </Option>
              <Option value={InventoryStatus.EXCEPTION}>
                <Tag icon={statusIcons[InventoryStatus.EXCEPTION]} color={statusColors[InventoryStatus.EXCEPTION]}>
                  异常
                </Tag>
              </Option>
              <Option value={InventoryStatus.PENDING}>
                <Tag icon={statusIcons[InventoryStatus.PENDING]} color={statusColors[InventoryStatus.PENDING]}>
                  待盘点
                </Tag>
              </Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="notes"
            label="盘点备注"
          >
            <TextArea rows={4} placeholder="请输入盘点备注信息" />
          </Form.Item>
          
          {currentAsset && (
            <div className="asset-info">
              <Title level={5}>设备信息</Title>
              <Row gutter={[16, 8]}>
                <Col span={12}>
                  <Text strong>设备名称:</Text> {currentAsset.name}
                </Col>
                <Col span={12}>
                  <Text strong>IP地址:</Text> {currentAsset.ip_address}
                </Col>
                <Col span={12}>
                  <Text strong>设备类型:</Text> {currentAsset.device_type?.name || '-'}
                </Col>
                <Col span={12}>
                  <Text strong>厂商:</Text> {currentAsset.vendor?.name || '-'}
                </Col>
                <Col span={12}>
                  <Text strong>位置:</Text> {currentAsset.location?.name || '-'}
                </Col>
                <Col span={12}>
                  <Text strong>状态:</Text> {currentAsset.status?.name || '-'}
                </Col>
              </Row>
            </div>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default CMDBInventory; 