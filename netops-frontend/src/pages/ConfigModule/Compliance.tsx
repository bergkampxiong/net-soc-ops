import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Form,
  Input,
  Button,
  Space,
  Modal,
  Select,
  Spin,
  message,
  Popconfirm,
  Tabs,
} from 'antd';
import request from '../../utils/request';

interface PolicyItem {
  id: number;
  name: string;
  rule_type: string;
  rule_content: string;
  device_type?: string;
  description?: string;
  created_at?: string;
}

interface ResultItem {
  id: number;
  policy_id: number;
  backup_id?: number;
  device_id?: string;
  passed: boolean;
  detail?: string;
  executed_at?: string;
}

const RULE_TYPES = [
  { value: 'must_contain', label: '必须包含' },
  { value: 'must_not_contain', label: '禁止包含' },
  { value: 'regex', label: '正则' },
];

const ConfigModuleCompliance: React.FC = () => {
  const [policyLoading, setPolicyLoading] = useState(false);
  const [policyList, setPolicyList] = useState<PolicyItem[]>([]);
  const [policyTotal, setPolicyTotal] = useState(0);
  const [policyModalVisible, setPolicyModalVisible] = useState(false);
  const [editingPolicyId, setEditingPolicyId] = useState<number | null>(null);
  const [policyForm] = Form.useForm();

  const [resultLoading, setResultLoading] = useState(false);
  const [resultList, setResultList] = useState<ResultItem[]>([]);
  const [resultTotal, setResultTotal] = useState(0);
  const [runModalVisible, setRunModalVisible] = useState(false);
  const [runForm] = Form.useForm();
  const [backupList, setBackupList] = useState<{ id: number; device_id: string }[]>([]);

  const loadPolicies = async () => {
    setPolicyLoading(true);
    try {
      const res = await request.get('/config-module/compliance/policies?limit=200');
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? data ?? [];
      const tot = data?.total ?? 0;
      setPolicyList(Array.isArray(items) ? items : []);
      setPolicyTotal(typeof tot === 'number' ? tot : 0);
    } catch (e) {
      message.error('加载策略列表失败');
      setPolicyList([]);
    } finally {
      setPolicyLoading(false);
    }
  };

  const loadResults = async (page = 1, pageSize = 20) => {
    setResultLoading(true);
    try {
      const res = await request.get(
        `/config-module/compliance/results?skip=${(page - 1) * pageSize}&limit=${pageSize}`
      );
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? data ?? [];
      const tot = data?.total ?? 0;
      setResultList(Array.isArray(items) ? items : []);
      setResultTotal(typeof tot === 'number' ? tot : 0);
    } catch (e) {
      message.error('加载结果列表失败');
      setResultList([]);
    } finally {
      setResultLoading(false);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, []);

  useEffect(() => {
    loadResults(1, 20);
  }, []);

  const openAddPolicy = () => {
    setEditingPolicyId(null);
    policyForm.resetFields();
    setPolicyModalVisible(true);
  };

  const openEditPolicy = (record: PolicyItem) => {
    setEditingPolicyId(record.id);
    policyForm.setFieldsValue({
      name: record.name,
      rule_type: record.rule_type,
      rule_content: record.rule_content,
      device_type: record.device_type,
      description: record.description,
    });
    setPolicyModalVisible(true);
  };

  const handlePolicySubmit = async () => {
    try {
      const v = await policyForm.validateFields();
      if (editingPolicyId != null) {
        await request.put(`/config-module/compliance/policies/${editingPolicyId}`, v);
        message.success('策略更新成功');
      } else {
        await request.post('/config-module/compliance/policies', v);
        message.success('策略新增成功');
      }
      setPolicyModalVisible(false);
      loadPolicies();
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error('保存失败');
    }
  };

  const onDeletePolicy = async (id: number) => {
    try {
      await request.delete(`/config-module/compliance/policies/${id}`);
      message.success('已删除');
      loadPolicies();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const openRun = async () => {
    try {
      const res = await request.get('/config-module/backups?limit=100');
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? [];
      setBackupList(Array.isArray(items) ? items.map((x: { id: number; device_id: string }) => ({ id: x.id, device_id: x.device_id })) : []);
    } catch (_) {
      setBackupList([]);
    }
    runForm.resetFields();
    setRunModalVisible(true);
  };

  const handleRun = async () => {
    try {
      const v = await runForm.validateFields();
      const body: { backup_id?: number; device_id?: string; policy_ids?: number[] } = {};
      if (v.target_type === 'backup' && v.backup_id) body.backup_id = v.backup_id;
      if (v.target_type === 'device' && v.device_id) body.device_id = v.device_id;
      if (v.policy_ids?.length) body.policy_ids = v.policy_ids;
      await request.post('/config-module/compliance/run', body);
      message.success('合规检查已执行');
      setRunModalVisible(false);
      loadResults(1, 20);
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error('执行失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>合规</h2>
      <Tabs
        defaultActiveKey="policies"
        items={[
          {
            key: 'policies',
            label: '策略管理',
            children: (
              <Card>
                <div style={{ marginBottom: 16 }}>
                  <Space>
                    <Button type="primary" onClick={openAddPolicy}>新增策略</Button>
                  </Space>
                </div>
                <Table
                  loading={policyLoading}
                  dataSource={policyList}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '名称', dataIndex: 'name', width: 140 },
                    { title: '规则类型', dataIndex: 'rule_type', width: 100, render: (t) => RULE_TYPES.find(r => r.value === t)?.label ?? t },
                    { title: '规则内容', dataIndex: 'rule_content', ellipsis: true },
                    { title: '设备类型', dataIndex: 'device_type', width: 100 },
                    {
                      title: '操作',
                      key: 'action',
                      width: 140,
                      render: (_, record) => (
                        <Space>
                          <a onClick={() => openEditPolicy(record)}>编辑</a>
                          <Popconfirm title="确定删除？" onConfirm={() => onDeletePolicy(record.id)}>
                            <a style={{ color: '#ff4d4f' }}>删除</a>
                          </Popconfirm>
                        </Space>
                      ),
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'run',
            label: '执行检查',
            children: (
              <Card>
                <Button type="primary" onClick={openRun} style={{ marginBottom: 16 }}>执行合规检查</Button>
                <p style={{ color: '#666' }}>选择备份或设备（取最新备份），选择策略后执行，结果在「结果列表」中查看。</p>
              </Card>
            ),
          },
          {
            key: 'results',
            label: '结果列表',
            children: (
              <Card>
                <Button onClick={() => loadResults(1, 20)} style={{ marginBottom: 16 }}>刷新</Button>
                <Table
                  loading={resultLoading}
                  dataSource={resultList}
                  rowKey="id"
                  size="small"
                  pagination={{
                    total: resultTotal,
                    pageSize: 20,
                    showTotal: (t) => `共 ${t} 条`,
                    onChange: (p, ps) => loadResults(p, ps || 20),
                  }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '策略ID', dataIndex: 'policy_id', width: 80 },
                    { title: '设备', dataIndex: 'device_id', width: 120 },
                    { title: '备份ID', dataIndex: 'backup_id', width: 80 },
                    { title: '通过', dataIndex: 'passed', width: 70, render: (v) => v ? '是' : '否' },
                    { title: '说明', dataIndex: 'detail', ellipsis: true },
                    { title: '执行时间', dataIndex: 'executed_at', width: 180 },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />

      <Modal
        title={editingPolicyId != null ? '编辑策略' : '新增策略'}
        open={policyModalVisible}
        onOk={handlePolicySubmit}
        onCancel={() => setPolicyModalVisible(false)}
        width={560}
        destroyOnClose
      >
        <Form form={policyForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="策略名称" rules={[{ required: true }]}>
            <Input placeholder="名称" />
          </Form.Item>
          <Form.Item name="rule_type" label="规则类型" rules={[{ required: true }]}>
            <Select options={RULE_TYPES} placeholder="选择类型" />
          </Form.Item>
          <Form.Item name="rule_content" label="规则内容" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="必须包含/禁止包含的字符串，或正则表达式" />
          </Form.Item>
          <Form.Item name="device_type" label="适用设备类型">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="执行合规检查"
        open={runModalVisible}
        onOk={handleRun}
        onCancel={() => setRunModalVisible(false)}
        width={480}
      >
        <Form form={runForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="target_type" label="检查对象" initialValue="backup" rules={[{ required: true }]}>
            <Select options={[
              { value: 'backup', label: '指定备份' },
              { value: 'device', label: '按设备（取最新备份）' },
            ]} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.target_type !== cur.target_type}>
            {({ getFieldValue }) =>
              getFieldValue('target_type') === 'backup' ? (
                <Form.Item name="backup_id" label="备份ID" rules={[{ required: true }]}>
                  <Select
                    placeholder="选择备份"
                    showSearch
                    optionFilterProp="label"
                    options={backupList.map(b => ({ value: b.id, label: `#${b.id} ${b.device_id}` }))}
                  />
                </Form.Item>
              ) : (
                <Form.Item name="device_id" label="设备标识" rules={[{ required: true }]}>
                  <Input placeholder="设备ID" />
                </Form.Item>
              )
            }
          </Form.Item>
          <Form.Item name="policy_ids" label="策略（不选则执行全部）">
            <Select
              mode="multiple"
              placeholder="选择策略"
              options={policyList.map(p => ({ value: p.id, label: `${p.name} (${p.rule_type})` }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigModuleCompliance;
