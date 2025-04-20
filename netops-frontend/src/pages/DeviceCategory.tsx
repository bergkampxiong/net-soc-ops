import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Space,
  Tag,
  message,
  Popconfirm,
  Select,
  Layout,
  Menu,
  Row,
  Col,
  Checkbox,
  List,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  AppstoreOutlined,
  TeamOutlined,
  UserOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import request from '../utils/request';

const { Sider, Content } = Layout;
const { Option } = Select;

interface DeviceGroup {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  device_count: number;
}

interface DeviceMember {
  id: number;
  group_id: number;
  device_id: number;
  device_name: string;
  ip_address: string;
  location: string;
  created_at: string;
  updated_at: string;
}

interface DeviceType {
  id: number;
  name: string;
  description?: string;
}

interface Location {
  id: number;
  name: string;
  description?: string;
}

interface Device {
  id: number;
  name: string;
  ip_address: string;
  device_type: string;
  location: string;
}

// 设备分类管理组件
const CategoryManagement: React.FC = () => {
  const [groups, setGroups] = useState<DeviceGroup[]>([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 获取设备分组列表
  const fetchGroups = async () => {
    setLoading(true);
    try {
      const response = await request.get('/api/device/category/groups');
      setGroups(response.data);
    } catch (error) {
      message.error('获取设备分组失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, []);

  // 创建设备分组
  const handleSubmit = async (values: any) => {
    try {
      await request.post('/api/device/category/groups', values);
      message.success('创建设备分组成功');
      setIsModalVisible(false);
      form.resetFields();
      fetchGroups();
    } catch (error) {
      message.error('创建设备分组失败');
    }
  };

  // 删除设备分组
  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/api/device/category/groups/${id}`);
      message.success('删除设备分组成功');
      fetchGroups();
    } catch (error) {
      message.error('删除设备分组失败');
    }
  };

  const columns = [
    {
      title: '分组名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '备注',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: DeviceGroup) => (
        <Popconfirm
          title="确定要删除这个分组吗？"
          onConfirm={() => handleDelete(record.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button type="link" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="设备分类"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              form.resetFields();
              setIsModalVisible(true);
            }}
          >
            新建分组
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={groups}
          rowKey="id"
          loading={loading}
        />
      </Card>

      <Modal
        title="新建设备分组"
        open={isModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
      >
        <Form
          form={form}
          onFinish={handleSubmit}
          layout="vertical"
        >
          <Form.Item
            name="name"
            label="分组名称"
            rules={[{ required: true, message: '请输入分组名称' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="description"
            label="备注"
          >
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

// 成员管理组件
const MemberManagement: React.FC = () => {
  const [deviceTypes, setDeviceTypes] = useState<DeviceType[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [selectedDevices, setSelectedDevices] = useState<number[]>([]);
  const [groups, setGroups] = useState<DeviceGroup[]>([]);
  const [addToGroupModalVisible, setAddToGroupModalVisible] = useState(false);
  
  // 设备类型和位置的映射缓存
  const [deviceTypeMap, setDeviceTypeMap] = useState<Record<string, string>>({});
  const [locationMap, setLocationMap] = useState<Record<string, string>>({});

  // 获取设备类型列表
  const fetchDeviceTypes = async () => {
    try {
      const response = await request.get('/api/device/category/device-types');
      console.log('获取到的设备类型列表:', response.data);
      // 过滤掉英文选项
      const filteredTypes = response.data.filter((type: DeviceType) => 
        !['Server', 'Network', 'K8S Node', 'K8S Cluster'].includes(type.name)
      );
      setDeviceTypes(filteredTypes);
      
      // 创建设备类型ID到名称的映射
      const typeMap: Record<string, string> = {};
      filteredTypes.forEach((type: DeviceType) => {
        // 确保ID作为字符串存储
        const typeId = String(type.id);
        typeMap[typeId] = type.name;
      });
      console.log('成员显示 - 创建设备类型映射:', typeMap);
      setDeviceTypeMap(typeMap);
    } catch (error) {
      console.error('获取设备类型列表失败:', error);
    }
  };

  // 获取位置列表
  const fetchLocations = async () => {
    try {
      const response = await request.get('/api/device/category/locations');
      console.log('获取到的位置列表:', response.data);
      setLocations(response.data);
      
      // 创建位置ID到名称的映射
      const locMap: Record<string, string> = {};
      response.data.forEach((location: Location) => {
        // 确保ID作为字符串存储
        const locationId = String(location.id);
        locMap[locationId] = location.name;
      });
      console.log('成员显示 - 创建位置映射:', locMap);
      setLocationMap(locMap);
    } catch (error) {
      console.error('获取位置列表失败:', error);
    }
  };

  // 获取设备分组列表
  const fetchGroups = async () => {
    try {
      const response = await request.get('/api/device/category/groups');
      setGroups(response.data);
    } catch (error) {
      message.error('获取设备分组失败');
    }
  };

  useEffect(() => {
    fetchDeviceTypes();
    fetchLocations();
    fetchGroups();
  }, []);

  // 当设备类型或位置映射更新时，重新处理设备列表
  useEffect(() => {
    if (devices.length > 0 && (Object.keys(deviceTypeMap).length > 0 || Object.keys(locationMap).length > 0)) {
      console.log('映射数据更新，重新处理设备列表');
      
      const processedDevices = devices.map((device: any) => {
        const result = { ...device };
        
        // 处理设备类型
        if (device.device_type && !device.device_type_obj) {
          const typeId = String(device.device_type);
          const typeName = deviceTypeMap[typeId];
          if (typeName) {
            result.device_type_obj = { 
              id: typeId, 
              name: typeName 
            };
          }
        }
        
        // 处理位置
        if (device.location && !device.location_obj) {
          const locationId = String(device.location);
          const locationName = locationMap[locationId];
          if (locationName) {
            result.location_obj = { 
              id: locationId, 
              name: locationName 
            };
          }
        }
        
        return result;
      });
      
      console.log('重新处理后的设备数据:', processedDevices);
      setDevices(processedDevices);
    }
  }, [deviceTypeMap, locationMap]);

  // 查询设备
  const handleSearch = async (values: any) => {
    setLoading(true);
    try {
      console.log('查询参数:', values);
      const response = await request.get('/api/device/category/cmdb-devices', {
        params: {
          name: values.name,
          ip_address: values.ip_address,
          device_type_id: values.device_type_id,
          location_id: values.location_id
        }
      });
      
      console.log('API返回的设备数据:', response.data);
      
      if (response.data.length > 0) {
        const firstDevice = response.data[0];
        console.log('第一个设备的数据结构:', {
          id: firstDevice.id,
          name: firstDevice.name,
          ip_address: firstDevice.ip_address,
          device_type: firstDevice.device_type,
          location: firstDevice.location,
          typeofDeviceType: typeof firstDevice.device_type,
          typeofLocation: typeof firstDevice.location
        });
      }
      
      // 处理设备数据，添加设备类型和位置对象
      const processedDevices = response.data.map((device: any) => {
        const result = { ...device };
        
        // 处理设备类型
        if (device.device_type) {
          const typeId = String(device.device_type);
          const typeName = deviceTypeMap[typeId];
          if (typeName) {
            result.device_type_obj = { 
              id: typeId, 
              name: typeName 
            };
          }
        }
        
        // 处理位置
        if (device.location) {
          const locationId = String(device.location);
          const locationName = locationMap[locationId];
          if (locationName) {
            result.location_obj = { 
              id: locationId, 
              name: locationName 
            };
          }
        }
        
        return result;
      });
      
      console.log('处理后的设备数据:', processedDevices);
      setDevices(processedDevices);
    } catch (error) {
      console.error('查询设备失败:', error);
      message.error('查询设备失败');
    } finally {
      setLoading(false);
    }
  };

  // 重置表单
  const handleReset = () => {
    form.resetFields();
    setDevices([]);
    setSelectedDevices([]);
  };

  // 检查设备是否已在分组中
  const checkDevicesInGroup = async (groupId: number): Promise<boolean> => {
    try {
      const response = await request.get(`/api/device/category/groups/${groupId}/members`);
      const groupMembers = response.data;
      
      // 获取组内设备的ID列表
      const groupDeviceIds = groupMembers.map((member: any) => member.device_id);
      
      // 检查选中的设备是否已在分组中
      const alreadyInGroup = selectedDevices.filter(id => groupDeviceIds.includes(id));
      
      if (alreadyInGroup.length > 0) {
        if (alreadyInGroup.length === selectedDevices.length) {
          message.warning('所选设备已全部在分组中');
          return false;
        } else {
          Modal.confirm({
            title: '部分设备已在分组中',
            content: `${alreadyInGroup.length}个设备已在分组中，是否继续添加其余${selectedDevices.length - alreadyInGroup.length}个设备？`,
            onOk: () => {
              // 过滤掉已在分组中的设备
              const newDevices = selectedDevices.filter(id => !groupDeviceIds.includes(id));
              addDevicesToGroup(groupId, newDevices);
            }
          });
          return false;
        }
      }
      
      return true;
    } catch (error) {
      message.error('检查设备状态失败');
      return false;
    }
  };
  
  // 实际添加设备到分组
  const addDevicesToGroup = async (groupId: number, deviceIds: number[]) => {
    try {
      await request.post(`/api/device/category/groups/${groupId}/members`, {
        device_ids: deviceIds
      });
      message.success('添加设备到分组成功');
      setAddToGroupModalVisible(false);
      setSelectedDevices([]);
    } catch (error: any) {
      // 显示服务器返回的错误信息
      if (error.response && error.response.data && error.response.data.detail) {
        message.error(error.response.data.detail);
      } else {
        message.error('添加设备到分组失败');
      }
    }
  };

  // 添加设备到分组
  const handleAddToGroup = async (groupId: number) => {
    const canProceed = await checkDevicesInGroup(groupId);
    if (canProceed) {
      addDevicesToGroup(groupId, selectedDevices);
    }
  };

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
      render: (text: any, record: any) => {
        // 尝试多种方式获取设备类型名称
        if (record.device_type_obj && record.device_type_obj.name) {
          return record.device_type_obj.name;
        }
        
        if (typeof text === 'object' && text && text.name) {
          return text.name;
        }
        
        if (text && typeof text !== 'object') {
          const typeId = String(text);
          return deviceTypeMap[typeId] || text;
        }
        
        return '';
      }
    },
    {
      title: '位置',
      dataIndex: 'location',
      key: 'location',
      render: (text: any, record: any) => {
        // 尝试多种方式获取位置名称
        if (record.location_obj && record.location_obj.name) {
          return record.location_obj.name;
        }
        
        if (typeof text === 'object' && text && text.name) {
          return text.name;
        }
        
        if (text && typeof text !== 'object') {
          const locationId = String(text);
          return locationMap[locationId] || text;
        }
        
        return '';
      }
    },
  ];

  return (
    <div>
      <Card title="设备筛选">
        <Form
          form={form}
          layout="inline"
          onFinish={handleSearch}
          style={{ marginBottom: 16 }}
        >
          <Form.Item name="name">
            <Input placeholder="设备名称" allowClear />
          </Form.Item>
          <Form.Item name="ip_address">
            <Input placeholder="IP地址" allowClear />
          </Form.Item>
          <Form.Item name="device_type_id">
            <Select
              placeholder="设备类型"
              allowClear
              style={{ width: 200 }}
            >
              {deviceTypes.map(type => (
                <Option key={type.id} value={type.id}>{type.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="location_id">
            <Select
              placeholder="位置"
              allowClear
              style={{ width: 200 }}
            >
              {locations.map(location => (
                <Option key={location.id} value={location.id}>{location.name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
                筛选
              </Button>
              <Button onClick={handleReset}>重置</Button>
              <Button
                type="primary"
                disabled={selectedDevices.length === 0}
                onClick={() => setAddToGroupModalVisible(true)}
                icon={<PlusOutlined />}
              >
                添加到分组
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={devices}
          loading={loading}
          rowSelection={{
            selectedRowKeys: selectedDevices,
            onChange: (selectedRowKeys) => {
              setSelectedDevices(selectedRowKeys as number[]);
            },
          }}
        />
      </Card>

      <Modal
        title="选择目标分组"
        open={addToGroupModalVisible}
        onCancel={() => setAddToGroupModalVisible(false)}
        footer={null}
      >
        <List
          dataSource={groups}
          renderItem={group => (
            <List.Item
              actions={[
                <Button
                  type="primary"
                  onClick={() => handleAddToGroup(group.id)}
                >
                  选择
                </Button>
              ]}
            >
              <List.Item.Meta
                title={group.name}
                description={group.description}
              />
            </List.Item>
          )}
        />
      </Modal>
    </div>
  );
};

// 成员显示组件
const MemberDisplay: React.FC = () => {
  const [members, setMembers] = useState<DeviceMember[]>([]);
  const [groups, setGroups] = useState<DeviceGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [deleteLoading, setDeleteLoading] = useState(false);
  
  // 设备类型和位置的映射缓存
  const [deviceTypes, setDeviceTypes] = useState<DeviceType[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [deviceTypeMap, setDeviceTypeMap] = useState<Record<string, string>>({});
  const [locationMap, setLocationMap] = useState<Record<string, string>>({});

  // 获取设备分组列表
  const fetchGroups = async () => {
    try {
      const response = await request.get('/api/device/category/groups');
      setGroups(response.data);
    } catch (error) {
      message.error('获取设备分组失败');
    }
  };
  
  // 获取设备类型列表
  const fetchDeviceTypes = async () => {
    try {
      const response = await request.get('/api/device/category/device-types');
      console.log('获取到的设备类型列表:', response.data);
      // 过滤掉英文选项
      const filteredTypes = response.data.filter((type: DeviceType) => 
        !['Server', 'Network', 'K8S Node', 'K8S Cluster'].includes(type.name)
      );
      setDeviceTypes(filteredTypes);
      
      // 创建设备类型ID到名称的映射
      const typeMap: Record<string, string> = {};
      filteredTypes.forEach((type: DeviceType) => {
        // 确保ID作为字符串存储
        const typeId = String(type.id);
        typeMap[typeId] = type.name;
      });
      console.log('成员显示 - 创建设备类型映射:', typeMap);
      setDeviceTypeMap(typeMap);
    } catch (error) {
      console.error('获取设备类型列表失败:', error);
    }
  };

  // 获取位置列表
  const fetchLocations = async () => {
    try {
      const response = await request.get('/api/device/category/locations');
      console.log('获取到的位置列表:', response.data);
      setLocations(response.data);
      
      // 创建位置ID到名称的映射
      const locMap: Record<string, string> = {};
      response.data.forEach((location: Location) => {
        // 确保ID作为字符串存储
        const locationId = String(location.id);
        locMap[locationId] = location.name;
      });
      console.log('成员显示 - 创建位置映射:', locMap);
      setLocationMap(locMap);
    } catch (error) {
      console.error('获取位置列表失败:', error);
    }
  };

  // 从CMDB获取设备详情
  const fetchDeviceDetails = async (deviceId: number) => {
    try {
      const response = await request.get(`/api/cmdb/assets/${deviceId}`);
      console.log(`获取设备${deviceId}详情:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`获取设备${deviceId}详情失败:`, error);
      return null;
    }
  };

  // 获取分组成员
  const fetchMembers = async (groupId: number) => {
    setLoading(true);
    try {
      const response = await request.get(`/api/device/category/groups/${groupId}/members`);
      console.log('获取到的分组成员数据:', response.data);
      
      if (response.data.length > 0) {
        const firstMember = response.data[0];
        console.log('第一个成员的数据结构:', {
          id: firstMember.id,
          device_id: firstMember.device_id,
          device_name: firstMember.device_name,
          device_type: firstMember.device_type,
          location: firstMember.location,
          typeofDeviceType: typeof firstMember.device_type,
          typeofLocation: typeof firstMember.location,
          hasDeviceType: 'device_type' in firstMember,
          hasLocation: 'location' in firstMember,
          allKeys: Object.keys(firstMember)
        });
      }
      
      // 处理成员数据，添加设备类型和位置对象
      const processedMembers = await Promise.all(response.data.map(async (member: any) => {
        const result = { ...member };
        
        // 检查是否有设备类型字段
        if ('device_type' in member && member.device_type) {
          const typeId = String(member.device_type);
          console.log(`成员设备类型ID: ${typeId}, 映射: ${deviceTypeMap[typeId]}`);
          
          // 尝试从映射中获取名称
          const typeName = deviceTypeMap[typeId];
          if (typeName) {
            result.device_type_obj = { 
              id: typeId, 
              name: typeName 
            };
            console.log(`设置成员设备类型对象:`, result.device_type_obj);
          }
        } else {
          console.log(`成员没有device_type字段或为空，尝试从CMDB获取设备详情`);
          
          // 尝试从CMDB获取设备详情
          const deviceDetails = await fetchDeviceDetails(member.device_id);
          if (deviceDetails && deviceDetails.device_type) {
            result.device_type = deviceDetails.device_type.id;
            result.device_type_obj = deviceDetails.device_type;
            console.log(`从CMDB获取到设备类型:`, result.device_type_obj);
          }
        }
        
        // 检查是否有位置字段
        if ('location' in member && member.location) {
          const locationId = String(member.location);
          console.log(`成员位置ID: ${locationId}, 映射: ${locationMap[locationId]}`);
          
          // 尝试从映射中获取名称
          const locationName = locationMap[locationId];
          if (locationName) {
            result.location_obj = { 
              id: locationId, 
              name: locationName 
            };
            console.log(`设置成员位置对象:`, result.location_obj);
          }
        } else {
          console.log(`成员没有location字段或为空，尝试从CMDB获取设备详情`);
          
          // 尝试从CMDB获取设备详情
          if (!result.device_type) { // 如果上面没有获取过设备详情
            const deviceDetails = await fetchDeviceDetails(member.device_id);
            if (deviceDetails && deviceDetails.location) {
              result.location = deviceDetails.location.id;
              result.location_obj = deviceDetails.location;
              console.log(`从CMDB获取到位置:`, result.location_obj);
            }
          }
        }
        
        return result;
      }));
      
      console.log('处理后的成员数据:', processedMembers);
      setMembers(processedMembers);
    } catch (error) {
      console.error('获取分组成员失败:', error);
      message.error('获取分组成员失败');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchGroups();
    fetchDeviceTypes();
    fetchLocations();
  }, []);

  useEffect(() => {
    if (selectedGroup !== null) {
      fetchMembers(selectedGroup);
    }
  }, [selectedGroup]);

  // 当设备类型或位置映射更新时，重新处理成员列表
  useEffect(() => {
    if (members.length > 0 && (Object.keys(deviceTypeMap).length > 0 || Object.keys(locationMap).length > 0)) {
      console.log('映射数据更新，重新处理成员列表');
      
      const processedMembers = members.map((member: any) => {
        const result = { ...member };
        
        // 处理设备类型
        if (member.device_type && !member.device_type_obj) {
          const typeId = String(member.device_type);
          const typeName = deviceTypeMap[typeId];
          if (typeName) {
            result.device_type_obj = { 
              id: typeId, 
              name: typeName 
            };
          }
        }
        
        // 处理位置
        if (member.location && !member.location_obj) {
          const locationId = String(member.location);
          const locationName = locationMap[locationId];
          if (locationName) {
            result.location_obj = { 
              id: locationId, 
              name: locationName 
            };
          }
        }
        
        return result;
      });
      
      console.log('重新处理后的成员数据:', processedMembers);
      setMembers(processedMembers);
    }
  }, [deviceTypeMap, locationMap]);

  // 删除分组成员
  const handleDeleteMember = async (memberId: number) => {
    if (!selectedGroup) return;
    
    try {
      await request.delete(`/api/device/category/groups/${selectedGroup}/members/${memberId}`);
      message.success('成员删除成功');
      // 重新获取成员列表
      fetchMembers(selectedGroup);
    } catch (error: any) {
      if (error.response && error.response.data && error.response.data.detail) {
        message.error(error.response.data.detail);
      } else {
        message.error('删除成员失败');
      }
    }
  };

  // 批量删除分组成员
  const handleBatchDelete = async () => {
    if (!selectedGroup || selectedRowKeys.length === 0) return;
    
    setDeleteLoading(true);
    try {
      // 获取选中行的设备ID
      const deviceIds = members
        .filter(member => selectedRowKeys.includes(member.id))
        .map(member => member.device_id);
      
      await request.delete(`/api/device/category/groups/${selectedGroup}/members`, {
        data: { device_ids: deviceIds }
      });
      
      message.success('批量删除成员成功');
      // 重新加载成员列表
      fetchMembers(selectedGroup);
      // 清除选择
      setSelectedRowKeys([]);
    } catch (error) {
      message.error('批量删除成员失败');
    } finally {
      setDeleteLoading(false);
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '设备名称',
      dataIndex: 'device_name',
      key: 'device_name',
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: '设备类型',
      key: 'device_type',
      render: (record: any) => {
        console.log('渲染设备类型:', record);
        
        // 尝试多种方式获取设备类型名称
        if (record.device_type_obj && record.device_type_obj.name) {
          return record.device_type_obj.name;
        }
        
        if (typeof record.device_type === 'object' && record.device_type && record.device_type.name) {
          return record.device_type.name;
        }
        
        if (record.device_type && typeof record.device_type !== 'object') {
          const typeId = String(record.device_type);
          const typeName = deviceTypeMap[typeId];
          if (typeName) {
            return typeName;
          }
          return record.device_type;
        }
        
        return '';
      }
    },
    {
      title: '位置',
      key: 'location',
      render: (record: any) => {
        // 尝试多种方式获取位置名称
        if (record.location_obj && record.location_obj.name) {
          return record.location_obj.name;
        }
        
        if (typeof record.location === 'object' && record.location && record.location.name) {
          return record.location.name;
        }
        
        if (record.location && typeof record.location !== 'object') {
          const locationId = String(record.location);
          const locationName = locationMap[locationId];
          if (locationName) {
            return locationName;
          }
          return record.location;
        }
        
        return '';
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: DeviceMember) => (
        <Popconfirm
          title="确定要从分组中移除此设备吗？"
          onConfirm={() => handleDeleteMember(record.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button type="link" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Card title="分组成员显示">
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Select
              placeholder="选择设备分组"
              style={{ width: '100%' }}
              onChange={(value) => setSelectedGroup(value as number)}
              value={selectedGroup}
            >
              {groups.map(group => (
                <Option key={group.id} value={group.id}>{group.name}</Option>
              ))}
            </Select>
          </Col>
          <Col span={16}>
            <Space>
              <Button
                type="primary"
                danger
                disabled={selectedRowKeys.length === 0}
                loading={deleteLoading}
                onClick={handleBatchDelete}
                icon={<DeleteOutlined />}
              >
                批量删除
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={members}
          loading={loading}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys),
          }}
        />
      </Card>
    </div>
  );
};

// 主设备分类页面组件
const DeviceCategory: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('category');
  const menuRef = useRef<any>(null);
  
  const handleTabChange = (key: string) => {
    setActiveTab(key);
  };
  
  return (
    <Layout style={{ minHeight: '100%' }}>
      <Sider width={200} theme="light">
        <Menu
          ref={menuRef}
          mode="inline"
          selectedKeys={[activeTab]}
          style={{ height: '100%' }}
          onClick={({ key }) => handleTabChange(key as string)}
          items={[
            {
              key: 'category',
              icon: <AppstoreOutlined />,
              label: '分类管理'
            },
            {
              key: 'member',
              icon: <TeamOutlined />,
              label: '成员管理'
            },
            {
              key: 'display',
              icon: <UserOutlined />,
              label: '成员显示'
            }
          ]}
        />
      </Sider>
      <Content style={{ padding: '0 24px', minHeight: 280 }}>
        {activeTab === 'category' && <CategoryManagement />}
        {activeTab === 'member' && <MemberManagement />}
        {activeTab === 'display' && <MemberDisplay />}
      </Content>
    </Layout>
  );
};

export default DeviceCategory;