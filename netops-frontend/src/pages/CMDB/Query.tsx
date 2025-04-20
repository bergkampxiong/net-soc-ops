import React, { useEffect, useRef, useState } from 'react';
import { Button, Card, Input, Space, Table, Tag, Typography, message, Row, Upload, Modal, Form, Select, Popconfirm, Col, DatePicker, Alert, Spin, InputNumber } from 'antd';
import type { InputRef } from 'antd';
import type { ColumnType, FilterConfirmProps, FilterDropdownProps } from 'antd/es/table/interface';
import { 
  SearchOutlined, DownloadOutlined, FilterOutlined, 
  ReloadOutlined, DatabaseOutlined, LaptopOutlined, 
  CloudServerOutlined, UploadOutlined, QuestionCircleOutlined,
  PlusOutlined, DeleteOutlined, EditOutlined
} from '@ant-design/icons';
import request from '../../utils/request';
import './Query.css';
import moment from 'moment';

const { Title, Text } = Typography;
const { Option } = Select;

// 设备类型标签颜色映射
const deviceTypeColors: Record<string, string> = {
  'Server': 'blue',
  'Network': 'green',
  'K8S Node': 'orange',
  'K8S Cluster': 'lime'
};

// 状态标签颜色映射
const statusColors: Record<string, string> = {
  '在线': 'green',
  '离线': 'red',
  '维护中': 'orange'
};

// 系统类型标签颜色映射
const systemTypeColors: Record<string, string> = {
  'cisco_ios': 'blue',
  'huawei_vrp': 'red',
  'ruijie_os_telnet': 'purple',
  'HPE Comware7': 'cyan',
  'cisco_nxos': 'geekblue',
  'cisco_xe': 'blue',
  'cisco_xr': 'blue',
  'huawei_vrpv8': 'red',
  'linux': 'green',
  'paloalto_panos': 'orange',
  'ruijie_os': 'purple',
  'hp_comware_telnet': 'cyan',
  'huawei_telnet': 'red',
  '其他': 'default'
};

interface ImportResponse {
  imported: number;
  failed: number;
  errors?: string[];
}

/**
 * CMDB资产查询组件
 */
const CMDBQuery: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [assets, setAssets] = useState<any[]>([]);
  const [searchParams, setSearchParams] = useState<Record<string, any>>({});
  const searchInput = useRef<InputRef>(null);
  const [importModalVisible, setImportModalVisible] = useState<boolean>(false);
  const [csvTemplateModalVisible, setCsvTemplateModalVisible] = useState<boolean>(false);
  const [importLoading, setImportLoading] = useState<boolean>(false);
  const [systemTypes, setSystemTypes] = useState<any[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [addDeviceModalVisible, setAddDeviceModalVisible] = useState<boolean>(false);
  const [deviceTypeOptions, setDeviceTypeOptions] = useState<any[]>([]);
  const [vendorOptions, setVendorOptions] = useState<any[]>([]);
  const [statusOptions, setStatusOptions] = useState<any[]>([]);
  const [locationOptions, setLocationOptions] = useState<any[]>([]);
  const [form] = Form.useForm();
  const [deleteLoading, setDeleteLoading] = useState<boolean>(false);
  const [addDeviceLoading, setAddDeviceLoading] = useState<boolean>(false);
  
  // 新增编辑相关状态
  const [editDeviceModalVisible, setEditDeviceModalVisible] = useState<boolean>(false);
  const [currentDevice, setCurrentDevice] = useState<any>(null);
  const [editDeviceForm] = Form.useForm();
  const [editDeviceLoading, setEditDeviceLoading] = useState<boolean>(false);

  // 组件挂载时获取数据
  useEffect(() => {
    fetchAssets();
    fetchSystemTypes();
    fetchReferenceData();
  }, [searchParams]);

  // 获取参考数据（设备类型、厂商、状态、位置）
  const fetchReferenceData = async () => {
    try {
      const [deviceTypesRes, vendorsRes, statusesRes, locationsRes] = await Promise.all([
        request.get('/cmdb/device-types'),
        request.get('/cmdb/vendors'),
        request.get('/cmdb/asset-statuses'),
        request.get('/cmdb/locations')
      ]);
      
      setDeviceTypeOptions(deviceTypesRes.data);
      setVendorOptions(vendorsRes.data);
      setStatusOptions(statusesRes.data);
      setLocationOptions(locationsRes.data);
    } catch (error) {
      console.error('获取参考数据失败:', error);
    }
  };

  // 获取系统类型数据
  const fetchSystemTypes = async () => {
    try {
      const response = await request.get('/cmdb/system-types');
      setSystemTypes(response.data);
    } catch (error) {
      console.error('获取系统类型数据失败:', error);
    }
  };

  // 获取资产数据
  const fetchAssets = async () => {
    setLoading(true);
    try {
      const response = await request.post('/cmdb/assets/query', {
        skip: 0,
        limit: 100,
        ...searchParams
      });
      
      if (response.data && Array.isArray(response.data)) {
        // 处理数据，确保所有字段都有值
        const processedData = response.data.map((asset: any) => ({
          ...asset,
          model: asset.model || '-',
          serial_number: asset.serial_number || '-',
          owner: asset.owner || '-',
          purchase_cost: asset.purchase_cost !== null ? Number(asset.purchase_cost) : '-',
          current_value: asset.current_value !== null ? Number(asset.current_value) : '-',
          online_date: asset.online_date || '-',
          device_type: asset.device_type || { name: '-' },
          vendor: asset.vendor || { name: '-' },
          department: asset.department || { name: '-' },
          location: asset.location || { name: '-' },
          status: asset.status || { name: '-' },
          system_type: asset.system_type || { name: '-' }
        }));
        setAssets(processedData);
        console.log('Processed assets:', processedData); // 添加处理后的数据日志
      } else {
        setAssets([]);
        message.warning('未获取到数据');
      }
    } catch (error: any) {
      console.error('获取资产数据失败:', error);
      message.error(error.response?.data?.detail || '获取资产数据失败');
      setAssets([]);
    } finally {
      setLoading(false);
    }
  };

  // 查询资产
  const handleSearch = async () => {
    setLoading(true);
    try {
      // 移除空值并转换数字类型
      const queryParams = Object.fromEntries(
        Object.entries(searchParams)
          .filter(([_, v]) => v !== undefined && v !== '')
          .map(([key, value]) => {
            // 转换数字类型的字段
            if (['device_type_id', 'vendor_id', 'department_id', 'location_id', 'status_id', 'system_type_id'].includes(key)) {
              return [key, parseInt(value as string)];
            }
            return [key, value];
          })
      );

      // 发送查询请求
      const response = await request.post('/cmdb/assets/query', queryParams);
      
      if (response.data && Array.isArray(response.data)) {
        // 处理数据，确保所有字段都有值
        const processedData = response.data.map((asset: any) => ({
          ...asset,
          model: asset.model || '-',
          serial_number: asset.serial_number || '-',
          owner: asset.owner || '-',
          purchase_cost: asset.purchase_cost !== null ? Number(asset.purchase_cost) : '-',
          current_value: asset.current_value !== null ? Number(asset.current_value) : '-',
          online_date: asset.online_date || '-',
          device_type: asset.device_type || { name: '-' },
          vendor: asset.vendor || { name: '-' },
          department: asset.department || { name: '-' },
          location: asset.location || { name: '-' },
          status: asset.status || { name: '-' },
          system_type: asset.system_type || { name: '-' }
        }));
        setAssets(processedData);
        message.success(`查询到 ${processedData.length} 条记录`);
        console.log('Processed search results:', processedData); // 添加处理后的数据日志
      } else {
        setAssets([]);
        message.warning('未查询到数据');
      }
    } catch (error: any) {
      console.error('Search failed:', error);
      message.error(error.response?.data?.detail || '查询失败');
      setAssets([]);
    } finally {
      setLoading(false);
    }
  };

  // 重置筛选
  const handleReset = () => {
    setSearchParams({});
    fetchAssets();
  };

  // 导出数据
  const handleExport = () => {
    if (assets.length === 0) {
      message.warning('没有数据可导出');
      return;
    }

    // 定义允许的设备类型和系统类型
    const allowedDeviceTypes = [
      'Server',
      'Network',
      'K8S Node',
      'K8S Cluster',
      'Router',
      'Switch',
      'Firewall',
      'Virtual Machine'
    ];

    const allowedSystemTypes = [
      'cisco_ios',
      'cisco_nxos',
      'cisco_xe',
      'cisco_xr',
      'huawei_vrpv8',
      'linux',
      'paloalto_panos',
      'ruijie_os',
      'hp_comware',
      'huawei',
      'fortinet'
    ];

    // 创建CSV内容
    const columnsWithDataIndex = columns.filter(col => col.dataIndex !== undefined && col.dataIndex !== 'action');
    
    const headers = columnsWithDataIndex.map(col => col.title);
    
    const rows = assets.map((asset: any) => 
      columnsWithDataIndex.map(col => {
        const dataIndex = col.dataIndex as string;
        let value = '';
        
        // 处理嵌套对象
        if (dataIndex.includes('.')) {
          const parts = dataIndex.split('.');
          let obj = asset;
          for (const part of parts) {
            obj = obj?.[part];
            if (obj === undefined) break;
          }
          value = obj || '';
        } else if (typeof asset[dataIndex] === 'object' && asset[dataIndex] !== null) {
          // 处理对象类型的字段，如device_type, vendor等
          value = asset[dataIndex]?.name || '';
        } else {
          value = asset[dataIndex] || '';
        }

        // 验证设备类型和系统类型
        if (dataIndex === 'device_type' && !allowedDeviceTypes.includes(value)) {
          value = ''; // 如果设备类型不在允许列表中，设置为空
        }
        if (dataIndex === 'system_type' && !allowedSystemTypes.includes(value)) {
          value = ''; // 如果系统类型不在允许列表中，设置为空
        }
        
        // 如果值包含逗号、引号或换行符，用双引号包裹并处理内部引号
        if (String(value).includes(',') || String(value).includes('"') || String(value).includes('\n')) {
          return `"${String(value).replace(/"/g, '""')}"`;
        }
        return String(value);
      })
    );

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    // 添加BOM标记，确保Excel正确识别UTF-8编码
    const BOM = "\uFEFF";
    const csvContentWithBOM = BOM + csvContent;

    // 创建下载链接
    const blob = new Blob([csvContentWithBOM], { type: 'application/vnd.ms-excel;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `资产列表_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url); // 释放URL对象
  };

  // 处理筛选确认
  const handleFilterConfirm = (field: string) => (selectedKeys: React.Key[], confirm: (param?: FilterConfirmProps) => void) => {
    setSearchParams((prev: Record<string, any>) => ({
      ...prev,
      [field]: selectedKeys[0]
    }));
    confirm();
  };

  // 处理筛选重置
  const handleFilterReset = (field: string) => (clearFilters: (() => void) | undefined) => {
    if (clearFilters) clearFilters();
    setSearchParams((prev: Record<string, any>) => {
      const newParams = { ...prev };
      delete newParams[field];
      return newParams;
    });
  };

  // 获取文本筛选下拉菜单
  const getTextFilterDropdown = (field: string) => (props: FilterDropdownProps) => {
    const { setSelectedKeys, selectedKeys, confirm, clearFilters } = props;
    return (
      <div style={{ padding: 8 }}>
        <Input
          ref={searchInput}
          placeholder={`搜索${field}`}
          value={selectedKeys[0]}
          onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleFilterConfirm(field)(selectedKeys, confirm)}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => handleFilterConfirm(field)(selectedKeys, confirm)}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            搜索
          </Button>
          <Button
            onClick={() => handleFilterReset(field)(clearFilters)}
            size="small"
            style={{ width: 90 }}
          >
            重置
          </Button>
        </Space>
      </div>
    );
  };

  // 获取选择筛选下拉菜单
  const getSelectFilterDropdown = (field: string, options: { text: string; value: string }[]) => (props: FilterDropdownProps) => {
    const { setSelectedKeys, selectedKeys, confirm, clearFilters } = props;
    return (
      <div style={{ padding: 8 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          {options.map(option => (
            <Button
              key={option.value}
              onClick={() => {
                setSelectedKeys([option.value]);
                handleFilterConfirm(field)([option.value], confirm);
              }}
              style={{ width: '100%', textAlign: 'left' }}
              type={selectedKeys[0] === option.value ? 'primary' : 'default'}
            >
              {option.text}
            </Button>
          ))}
          <Button
            onClick={() => handleFilterReset(field)(clearFilters)}
            size="small"
            style={{ width: '100%' }}
          >
            重置
          </Button>
        </Space>
      </div>
    );
  };

  // 筛选图标
  const getFilterIcon = (filtered: boolean) => (
    <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
  );

  // 处理行选择变化
  const onSelectChange = (newSelectedRowKeys: React.Key[]) => {
    setSelectedRowKeys(newSelectedRowKeys);
  };

  // 行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: onSelectChange,
    selections: [
      Table.SELECTION_ALL,
      Table.SELECTION_INVERT,
      Table.SELECTION_NONE,
    ],
  };

  // 处理添加设备
  const handleAddDevice = async (values: any) => {
    setAddDeviceLoading(true);
    try {
      // 处理日期字段
      const formattedValues = {
        ...values,
        purchase_date: values.purchase_date ? values.purchase_date.format('YYYY-MM-DD') : null,
        online_date: values.online_date ? values.online_date.format('YYYY-MM-DD') : null,
        warranty_expiry: values.warranty_expiry ? values.warranty_expiry.format('YYYY-MM-DD') : null,
      };
      
      await request.post('/cmdb/assets', formattedValues);
      message.success('设备添加成功');
      setAddDeviceModalVisible(false);
      form.resetFields();
      fetchAssets(); // 刷新数据
    } catch (error) {
      console.error('添加设备失败:', error);
      message.error('添加设备失败');
    } finally {
      setAddDeviceLoading(false);
    }
  };

  // 处理删除设备
  const handleDeleteDevices = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要删除的设备');
      return;
    }

    setDeleteLoading(true);
    try {
      await request.post('/cmdb/assets/delete', { ids: selectedRowKeys });
      message.success(`成功删除 ${selectedRowKeys.length} 台设备`);
      setSelectedRowKeys([]);
      fetchAssets(); // 刷新数据
    } catch (error) {
      console.error('删除设备失败:', error);
      message.error('删除设备失败');
    } finally {
      setDeleteLoading(false);
    }
  };

  // 处理编辑设备
  const handleEditDevice = async (values: any) => {
    if (!currentDevice) return;
    
    setEditDeviceLoading(true);
    try {
      // 处理日期字段和数据类型转换
      const formattedValues = {
        ...values,
        // 确保ID字段为整数类型
        device_type_id: values.device_type_id ? parseInt(values.device_type_id) : null,
        vendor_id: values.vendor_id ? parseInt(values.vendor_id) : null,
        location_id: values.location_id ? parseInt(values.location_id) : null,
        status_id: values.status_id ? parseInt(values.status_id) : null,
        system_type_id: values.system_type_id ? parseInt(values.system_type_id) : null,
        // 处理日期字段
        purchase_date: values.purchase_date ? values.purchase_date.format('YYYY-MM-DD') : null,
        online_date: values.online_date ? values.online_date.format('YYYY-MM-DD') : null,
        warranty_expiry: values.warranty_expiry ? values.warranty_expiry.format('YYYY-MM-DD') : null,
        // 处理数值字段
        purchase_cost: values.purchase_cost ? parseFloat(values.purchase_cost) : null,
        current_value: values.current_value ? parseFloat(values.current_value) : null,
      };
      
      await request.put(`/cmdb/assets/${currentDevice.id}`, formattedValues);
      message.success('设备更新成功');
      setEditDeviceModalVisible(false);
      fetchAssets(); // 刷新数据
    } catch (error) {
      console.error('更新设备失败:', error);
      message.error('更新设备失败');
    } finally {
      setEditDeviceLoading(false);
    }
  };

  // 打开编辑设备模态框
  const showEditDeviceModal = (device: any) => {
    setCurrentDevice(device);
    
    // 处理日期字段，将字符串转换为moment对象
    const formValues = {
      name: device.name,
      asset_tag: device.asset_tag,
      ip_address: device.ip_address,
      serial_number: device.serial_number,
      device_type_id: device.device_type?.id,
      vendor_id: device.vendor?.id,
      department_id: device.department?.id,
      location_id: device.location?.id,
      status_id: device.status?.id,
      system_type_id: device.system_type?.id,
      owner: device.owner,
      model: device.model,
      purchase_cost: device.purchase_cost,
      current_value: device.current_value,
      notes: device.notes,
      // 日期字段处理
      purchase_date: device.purchase_date ? moment(device.purchase_date) : null,
      online_date: device.online_date ? moment(device.online_date) : null,
      warranty_expiry: device.warranty_expiry ? moment(device.warranty_expiry) : null,
    };
    
    editDeviceForm.setFieldsValue(formValues);
    setEditDeviceModalVisible(true);
  };

  // 表格列定义
  const columns: ColumnType<any>[] = [
    {
      title: '设备名称',
      dataIndex: 'name',
      key: 'name',
      filterDropdown: getTextFilterDropdown('name'),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      ellipsis: true,
      width: 150,
    },
    {
      title: '资产标签',
      dataIndex: 'asset_tag',
      key: 'asset_tag',
      filterDropdown: getTextFilterDropdown('asset_tag'),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 120,
    },
    {
      title: '设备类型',
      dataIndex: ['device_type', 'name'],
      key: 'device_type',
      render: (text) => text && (
        <Tag color={deviceTypeColors[text] || 'default'}>
          {text}
        </Tag>
      ),
      filterDropdown: getSelectFilterDropdown('device_type_id', deviceTypeOptions.map(type => ({
        text: type.name,
        value: type.id.toString()
      }))),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 120,
    },
    {
      title: '厂商',
      dataIndex: ['vendor', 'name'],
      key: 'vendor',
      filterDropdown: getSelectFilterDropdown('vendor_id', vendorOptions.map(vendor => ({
        text: vendor.name,
        value: vendor.id.toString()
      }))),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 120,
      ellipsis: true,
    },
    {
      title: '型号',
      dataIndex: 'model',
      key: 'model',
      filterDropdown: getTextFilterDropdown('model'),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 120,
      ellipsis: true,
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      filterDropdown: getTextFilterDropdown('ip_address'),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 130,
    },
    {
      title: 'SN码',
      dataIndex: 'serial_number',
      key: 'serial_number',
      filterDropdown: getTextFilterDropdown('serial_number'),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 150,
      ellipsis: true,
    },
    {
      title: '系统类型',
      dataIndex: ['system_type', 'name'],
      key: 'system_type',
      render: (text) => text && (
        <Tag color={systemTypeColors[text] || 'default'}>
          {text}
        </Tag>
      ),
      filterDropdown: getSelectFilterDropdown('system_type_id', 
        systemTypes.map(st => ({ text: st.name, value: st.id.toString() }))
      ),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 130,
    },
    {
      title: '状态',
      dataIndex: ['status', 'name'],
      key: 'status',
      render: (text) => text && (
        <Tag color={statusColors[text] || 'default'}>
          {text}
        </Tag>
      ),
      filterDropdown: getSelectFilterDropdown('status_id', statusOptions.map(status => ({
        text: status.name,
        value: status.id.toString()
      }))),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 100,
    },
    {
      title: '位置',
      dataIndex: ['location', 'name'],
      key: 'location',
      filterDropdown: getSelectFilterDropdown('location_id', 
        locationOptions.map(location => ({ text: location.name, value: location.id.toString() }))
      ),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 120,
      ellipsis: true,
    },
    {
      title: '所有者',
      dataIndex: 'owner',
      key: 'owner',
      filterDropdown: getTextFilterDropdown('owner'),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 100,
      ellipsis: true,
    },
    {
      title: '所属部门',
      dataIndex: ['department', 'name'],
      key: 'department',
      filterDropdown: getSelectFilterDropdown('department_id', 
        locationOptions.map(location => ({ text: location.name, value: location.id.toString() }))
      ),
      filterIcon: (filtered) => <FilterOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
      width: 120,
      ellipsis: true,
    },
    {
      title: '上线时间',
      dataIndex: 'online_date',
      key: 'online_date',
      render: (date) => date && date !== '-' ? moment(date).format('YYYY-MM-DD') : '-',
      width: 120,
    },
    {
      title: '购买成本',
      dataIndex: 'purchase_cost',
      key: 'purchase_cost',
      render: (cost) => cost && cost !== '-' ? `¥${Number(cost).toLocaleString()}` : '-',
      width: 100,
    },
    {
      title: '当前价值',
      dataIndex: 'current_value',
      key: 'current_value',
      render: (value) => value && value !== '-' ? `¥${Number(value).toLocaleString()}` : '-',
      width: 100,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => moment(date).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      width: 150,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date) => moment(date).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      width: 150,
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Button 
            type="text" 
            icon={<EditOutlined />} 
            onClick={() => showEditDeviceModal(record)}
          />
          <Popconfirm
            title="确定要删除此资产吗?"
            onConfirm={() => handleDeleteDevices()}
            okText="确定"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 根据设备类型获取图标
  const getDeviceIcon = (deviceType: string) => {
    if (!deviceType) return <DatabaseOutlined />;
    
    if (['Huawei', 'H3C', 'Ruijie', 'Cisco', 'Fortinet', 'Palo Alto'].includes(deviceType)) {
      return <DatabaseOutlined style={{ color: deviceTypeColors[deviceType as keyof typeof deviceTypeColors] || 'black' }} />;
    }
    
    if (['Physical Server', 'Virtual Machine', 'Cloud Host'].includes(deviceType)) {
      return <LaptopOutlined style={{ color: deviceTypeColors[deviceType as keyof typeof deviceTypeColors] || 'black' }} />;
    }
    
    if (deviceType === 'K8S Cluster') {
      return <CloudServerOutlined style={{ color: deviceTypeColors[deviceType as keyof typeof deviceTypeColors] || 'black' }} />;
    }
    
    return <DatabaseOutlined />;
  };

  // 处理CSV导入
  const handleImport = async (file: File) => {
    try {
      // 读取CSV文件内容
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const csvContent = e.target?.result as string;
          // 发送CSV内容为JSON对象
          const response = await request.post<ImportResponse>('/cmdb/assets/import', { content: csvContent });
          message.success(`导入成功: ${response.data.imported}条记录已导入, ${response.data.failed}条记录失败`);
          if (response.data.errors && response.data.errors.length > 0) {
            console.error('导入错误:', response.data.errors);
            message.warning(`导入过程中有${response.data.errors.length}个错误，请查看控制台`);
          }
          fetchAssets();
          setImportModalVisible(false);
        } catch (error: any) {
          console.error('导入失败:', error);
          message.error('导入失败: ' + (error.response?.data?.detail || '未知错误'));
        }
      };
      reader.onerror = () => {
        message.error('读取文件失败');
      };
      reader.readAsText(file, 'UTF-8');
    } catch (error: any) {
      console.error('导入失败:', error);
      message.error('导入失败: ' + (error.response?.data?.detail || '未知错误'));
    }
  };

  // CSV模板示例数据
  const csvTemplateData = `设备名称,资产标签,设备类型,厂商,型号,IP地址,SN码,系统类型,状态,位置,所有者,所属部门,上线时间,购买成本,当前价值,购买日期,保修到期,备注
Server001,SVR001,Server,Dell,PowerEdge R740,192.168.1.101,ABCD1234,linux,在线,机房A,张三,IT部门,2023-01-15,15000,12000,2023-01-01,2024-12-31,测试服务器
Switch001,SW001,Switch,Cisco,Catalyst 9300,192.168.1.1,XYZ9876,cisco_ios,在线,机房B,李四,运维部门,2023-02-20,8000,7500,2023-02-01,2024-12-31,核心交换机
K8SNode001,K8S001,K8S Node,HP,ProLiant DL380,192.168.2.101,HP12345,linux,在线,机房A,王五,研发部门,2023-03-10,12000,11000,2023-03-01,2024-12-31,K8S节点
K8SCluster001,K8SC001,K8S Cluster,,,192.168.3.0/24,,linux,在线,机房C,赵六,研发部门,2023-04-05,,,2023-04-01,2024-12-31,K8S集群`;

  // CSV模板示例模态框
  const renderCsvTemplateModal = () => (
    <Modal
      title="CSV模板示例"
      open={csvTemplateModalVisible}
      onCancel={() => setCsvTemplateModalVisible(false)}
      width={800}
      styles={{
        body: { padding: 24 }
      }}
      footer={[
        <Button 
          key="download" 
          type="primary"
          onClick={() => {
            // 添加BOM标记，确保Excel正确识别UTF-8编码
            const BOM = "\uFEFF";
            const csvContentWithBOM = BOM + csvTemplateData;
            const blob = new Blob([csvContentWithBOM], { type: 'application/vnd.ms-excel;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'cmdb_import_template.csv';
            link.click();
            URL.revokeObjectURL(link.href);
          }}
        >
          下载模板
        </Button>
      ]}
    >
      <div className="csv-template-container">
        <Alert
          message="CSV文件格式说明"
          description={
            <ul>
              <li>文件必须是UTF-8编码的CSV格式</li>
              <li>第一行必须是表头，列名必须与模板一致</li>
              <li>必填字段：设备名称、资产标签、设备类型、IP地址、系统类型</li>
              <li>日期格式：YYYY-MM-DD（例如：2023-01-01）</li>
              <li>金额格式：纯数字，不要包含货币符号（例如：10000）</li>
              <li>状态字段：默认为"在线"，可选值包括"在线"、"离线"、"维护中"等</li>
              <li>系统类型：常用值包括 linux、windows、cisco_ios 等</li>
            </ul>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Table
          dataSource={csvTemplateData.split('\n').slice(1).map((line, index) => {
            const values = line.split(',');
            return {
              key: index,
              name: values[0],
              asset_tag: values[1],
              device_type: values[2],
              vendor: values[3],
              model: values[4],
              ip_address: values[5],
              serial_number: values[6],
              system_type: values[7],
              status: values[8],
              location: values[9],
              owner: values[10],
              department: values[11],
              online_date: values[12],
              purchase_cost: values[13],
              current_value: values[14],
              purchase_date: values[15],
              warranty_expiry: values[16],
              notes: values[17]
            };
          })}
          columns={[
            { title: '设备名称', dataIndex: 'name', key: 'name' },
            { title: '资产标签', dataIndex: 'asset_tag', key: 'asset_tag' },
            { title: '设备类型', dataIndex: 'device_type', key: 'device_type' },
            { title: '厂商', dataIndex: 'vendor', key: 'vendor' },
            { title: '型号', dataIndex: 'model', key: 'model' },
            { title: 'IP地址', dataIndex: 'ip_address', key: 'ip_address' },
            { title: 'SN码', dataIndex: 'serial_number', key: 'serial_number' },
            { title: '系统类型', dataIndex: 'system_type', key: 'system_type' },
            { title: '状态', dataIndex: 'status', key: 'status' },
            { title: '位置', dataIndex: 'location', key: 'location' },
            { title: '所有者', dataIndex: 'owner', key: 'owner' },
            { title: '所属部门', dataIndex: 'department', key: 'department' },
            { title: '上线时间', dataIndex: 'online_date', key: 'online_date' },
            { title: '购买成本', dataIndex: 'purchase_cost', key: 'purchase_cost' },
            { title: '当前价值', dataIndex: 'current_value', key: 'current_value' },
            { title: '购买日期', dataIndex: 'purchase_date', key: 'purchase_date' },
            { title: '保修到期', dataIndex: 'warranty_expiry', key: 'warranty_expiry' },
            { title: '备注', dataIndex: 'notes', key: 'notes' }
          ]}
          scroll={{ x: true }}
          size="small"
          pagination={false}
        />
      </div>
    </Modal>
  );

  // 渲染筛选标签
  const renderFilterTags = () => {
    if (Object.keys(searchParams).length === 0) return null;

    return (
      <div style={{ marginBottom: 16 }}>
        {Object.entries(searchParams).map(([key, value]) => {
          let tagText = `${key}: ${value}`;
          
          // 根据不同的字段类型显示不同的标签文本
          if (key === 'device_type_id') {
            const deviceType = deviceTypeOptions.find(t => t.id.toString() === value);
            tagText = `设备类型: ${deviceType?.name || value}`;
          } else if (key === 'vendor_id') {
            const vendor = vendorOptions.find(v => v.id.toString() === value);
            tagText = `厂商: ${vendor?.name || value}`;
          } else if (key === 'system_type_id') {
            const systemType = systemTypes.find(s => s.id.toString() === value);
            tagText = `系统类型: ${systemType?.name || value}`;
          } else if (key === 'status_id') {
            const status = statusOptions.find(s => s.id.toString() === value);
            tagText = `状态: ${status?.name || value}`;
          } else if (key === 'location_id') {
            const location = locationOptions.find(l => l.id.toString() === value);
            tagText = `位置: ${location?.name || value}`;
          } else if (key === 'name') {
            tagText = `设备名称: ${value}`;
          } else if (key === 'ip_address') {
            tagText = `IP地址: ${value}`;
          } else if (key === 'asset_tag') {
            tagText = `资产标签: ${value}`;
          } else if (key === 'serial_number') {
            tagText = `SN码: ${value}`;
          } else if (key === 'model') {
            tagText = `型号: ${value}`;
          } else if (key === 'owner') {
            tagText = `所有者: ${value}`;
          }

          return (
            <Tag
              key={key}
              closable
              onClose={() => {
                setSearchParams((prev: Record<string, any>) => {
                  const newParams = { ...prev };
                  delete newParams[key];
                  return newParams;
                });
              }}
              style={{ marginRight: 8 }}
            >
              {tagText}
            </Tag>
          );
        })}
        <Button type="link" size="small" onClick={handleReset}>
          清除所有筛选
        </Button>
      </div>
    );
  };

  // CSV导入模态框内容
  const renderImportModal = () => (
    <Modal
      title="导入设备数据"
      open={importModalVisible}
      onCancel={() => setImportModalVisible(false)}
      footer={null}
      width={600}
      styles={{
        body: { padding: 24 }
      }}
    >
      <div style={{ marginBottom: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Text>请上传符合格式的CSV文件，文件大小不超过10MB。</Text>
          <Alert
            message="导入说明"
            description={
              <ul style={{ margin: 0, paddingLeft: 16 }}>
                <li>CSV文件必须包含表头行，且列名必须与模板一致</li>
                <li>必填字段：设备名称、资产标签、设备类型、IP地址、系统类型</li>
                <li>日期格式：YYYY-MM-DD</li>
                <li>金额格式：纯数字，不需要包含货币符号</li>
              </ul>
            }
            type="info"
            showIcon
          />
          <Button 
            type="link" 
            icon={<QuestionCircleOutlined />}
            onClick={() => setCsvTemplateModalVisible(true)}
          >
            查看CSV模板示例
          </Button>
        </Space>
      </div>
      <Upload.Dragger
        name="file"
        accept=".csv"
        beforeUpload={handleImport}
        showUploadList={false}
        disabled={importLoading}
      >
        <p className="ant-upload-drag-icon">
          <UploadOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">支持单个CSV文件上传</p>
        {importLoading && (
          <Spin>
            <div style={{ padding: '24px 0' }}>正在导入...</div>
          </Spin>
        )}
      </Upload.Dragger>
    </Modal>
  );

  return (
    <div className="cmdb-query-page">
      {/* 操作按钮 */}
      <Card title="资产查询" className="cmdb-query-card">
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={24} md={12} lg={12}>
            <Space wrap>
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={() => setAddDeviceModalVisible(true)}
              >
                添加设备
              </Button>
              <Popconfirm
                title={`确定要删除选中的 ${selectedRowKeys.length} 台设备吗?`}
                onConfirm={handleDeleteDevices}
                okText="确定"
                cancelText="取消"
                disabled={selectedRowKeys.length === 0}
              >
                <Button 
                  danger 
                  icon={<DeleteOutlined />} 
                  disabled={selectedRowKeys.length === 0}
                  loading={deleteLoading}
                >
                  删除选中 ({selectedRowKeys.length})
                </Button>
              </Popconfirm>
            </Space>
          </Col>
          <Col xs={24} sm={24} md={12} lg={12} style={{ textAlign: 'right' }}>
            <Space wrap>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={handleReset}
              >
                重置
              </Button>
              <Button 
                icon={<UploadOutlined />}
                onClick={() => setImportModalVisible(true)}
              >
                导入
              </Button>
              <Button 
                type="primary" 
                icon={<DownloadOutlined />} 
                onClick={handleExport}
                disabled={assets.length === 0}
              >
                导出
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 添加筛选标签显示 */}
        {renderFilterTags()}

        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={assets}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
            defaultPageSize: 10,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          scroll={{ x: 'max-content', y: 'calc(100vh - 300px)' }}
          size="middle"
          bordered
        />
      </Card>

      {/* CSV模板示例模态框 */}
      {renderCsvTemplateModal()}

      {/* 添加设备模态框 */}
      <Modal
        title="添加设备"
        open={addDeviceModalVisible}
        onCancel={() => {
          setAddDeviceModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={800}
        styles={{
          body: { maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }
        }}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleAddDevice}
          initialValues={{
            api_type: 'netmiko',
            device_type: 'cisco_ios',
            timeout: 30,
            retry_count: 3,
            retry_delay: 5,
            port: 22,
            auth_type: 'password'
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="name"
                label="设备名称"
                rules={[{ required: true, message: '请输入设备名称' }]}
              >
                <Input placeholder="请输入设备名称" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="asset_tag"
                label="资产标签"
                rules={[{ required: true, message: '请输入资产标签' }]}
              >
                <Input placeholder="请输入资产标签" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="ip_address"
                label="IP地址"
                rules={[{ required: true, message: '请输入IP地址' }]}
              >
                <Input placeholder="请输入IP地址" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="device_type_id"
                label="设备类型"
                rules={[{ required: true, message: '请选择设备类型' }]}
              >
                <Select placeholder="请选择设备类型">
                  {deviceTypeOptions.map(type => (
                    <Option key={type.id} value={type.id}>{type.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="vendor_id"
                label="厂商"
              >
                <Select placeholder="请选择厂商" allowClear>
                  {vendorOptions.map(vendor => (
                    <Option key={vendor.id} value={vendor.id}>{vendor.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="model"
                label="型号"
              >
                <Input placeholder="请输入设备型号" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="serial_number"
                label="SN码"
              >
                <Input placeholder="请输入序列号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="system_type_id"
                label="系统类型"
                rules={[{ required: true, message: '请选择系统类型' }]}
              >
                <Select placeholder="请选择系统类型">
                  {systemTypes.map(type => (
                    <Option key={type.id} value={type.id}>{type.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="status_id"
                label="状态"
                initialValue={1} // 默认为"在线"
              >
                <Select placeholder="请选择状态">
                  {statusOptions.map(status => (
                    <Option key={status.id} value={status.id}>{status.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="location_id"
                label="位置"
              >
                <Select placeholder="请选择位置" allowClear>
                  {locationOptions.map(location => (
                    <Option key={location.id} value={location.id}>{location.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="owner"
                label="所有者"
              >
                <Input placeholder="请输入所有者" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="department_id"
                label="所属部门"
              >
                <Select placeholder="请选择部门" allowClear>
                  {/* 这里需要添加部门选项，如果后端有提供部门API */}
                  <Option value={1}>IT部门</Option>
                  <Option value={2}>研发部门</Option>
                  <Option value={3}>运维部门</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="purchase_date"
                label="购买日期"
              >
                <DatePicker style={{ width: '100%' }} placeholder="选择购买日期" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="online_date"
                label="上线时间"
              >
                <DatePicker style={{ width: '100%' }} placeholder="选择上线时间" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="warranty_expiry"
                label="保修到期"
              >
                <DatePicker style={{ width: '100%' }} placeholder="选择保修到期日期" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="purchase_cost"
                label="购买成本"
              >
                <Input prefix="¥" placeholder="请输入购买成本" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="current_value"
                label="当前价值"
              >
                <Input prefix="¥" placeholder="请输入当前价值" />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item
            name="notes"
            label="备注"
          >
            <Input.TextArea rows={4} placeholder="请输入备注信息" />
          </Form.Item>
          
          <Form.Item>
            <Row justify="end">
              <Space>
                <Button 
                  onClick={() => {
                    setAddDeviceModalVisible(false);
                    form.resetFields();
                  }}
                >
                  取消
                </Button>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  loading={addDeviceLoading}
                >
                  添加
                </Button>
              </Space>
            </Row>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑设备模态框 */}
      <Modal
        title="编辑设备"
        open={editDeviceModalVisible}
        onCancel={() => {
          setEditDeviceModalVisible(false);
          setCurrentDevice(null);
        }}
        footer={null}
        width={1200}
        styles={{
          body: { maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }
        }}
      >
        <Form
          form={editDeviceForm}
          layout="vertical"
          onFinish={handleEditDevice}
        >
          <Row gutter={[24, 24]}>
            <Col span={8}>
              <Form.Item
                name="name"
                label="设备名称"
                rules={[{ required: true, message: '请输入设备名称' }]}
              >
                <Input placeholder="请输入设备名称" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="asset_tag"
                label="资产标签"
                rules={[{ required: true, message: '请输入资产标签' }]}
              >
                <Input placeholder="请输入资产标签" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="ip_address"
                label="IP地址"
                rules={[{ required: true, message: '请输入IP地址' }]}
              >
                <Input placeholder="请输入IP地址" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[24, 24]}>
            <Col span={8}>
              <Form.Item
                name="device_type_id"
                label="设备类型"
                rules={[{ required: true, message: '请选择设备类型' }]}
              >
                <Select placeholder="请选择设备类型">
                  {deviceTypeOptions.map(option => (
                    <Option key={option.id} value={option.id}>{option.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="vendor_id"
                label="厂商"
              >
                <Select placeholder="请选择厂商">
                  {vendorOptions.map(option => (
                    <Option key={option.id} value={option.id}>{option.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="system_type_id"
                label="系统类型"
                rules={[{ required: true, message: '请选择系统类型' }]}
              >
                <Select placeholder="请选择系统类型">
                  {systemTypes.map(type => (
                    <Option key={type.id} value={type.id}>{type.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[24, 24]}>
            <Col span={8}>
              <Form.Item
                name="location_id"
                label="位置"
              >
                <Select placeholder="请选择位置">
                  {locationOptions.map(option => (
                    <Option key={option.id} value={option.id}>{option.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="status_id"
                label="状态"
              >
                <Select placeholder="请选择状态">
                  {statusOptions.map(option => (
                    <Option key={option.id} value={option.id}>{option.name}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="owner"
                label="所有者"
              >
                <Input placeholder="请输入所有者" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[24, 24]}>
            <Col span={8}>
              <Form.Item
                name="purchase_date"
                label="购买日期"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="purchase_cost"
                label="购买成本"
              >
                <InputNumber style={{ width: '100%' }} placeholder="请输入购买成本" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="current_value"
                label="当前价值"
              >
                <InputNumber style={{ width: '100%' }} placeholder="请输入当前价值" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[24, 24]}>
            <Col span={8}>
              <Form.Item
                name="online_date"
                label="上线时间"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="warranty_expiry"
                label="保修到期"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="serial_number"
                label="SN码"
              >
                <Input placeholder="请输入SN码" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={[24, 24]}>
            <Col span={24}>
              <Form.Item
                name="notes"
                label="备注"
              >
                <Input.TextArea rows={4} placeholder="请输入备注信息" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Row justify="end">
              <Space>
                <Button 
                  onClick={() => {
                    setEditDeviceModalVisible(false);
                    setCurrentDevice(null);
                  }}
                >
                  取消
                </Button>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  loading={editDeviceLoading}
                >
                  保存
                </Button>
              </Space>
            </Row>
          </Form.Item>
        </Form>
      </Modal>

      {/* CSV导入模态框 */}
      {renderImportModal()}
    </div>
  );
};

export default CMDBQuery; 