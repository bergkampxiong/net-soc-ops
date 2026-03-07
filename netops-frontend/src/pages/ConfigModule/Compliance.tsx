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
  message,
  Popconfirm,
  Tabs,
  Switch,
  Upload,
  Drawer,
} from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import request from '../../utils/request';

interface PolicyItem {
  id: number;
  name: string;
  rule_type: string;
  rule_content: string;
  device_type?: string;
  description?: string;
  group?: string;
  enabled?: boolean;
  created_at?: string;
}

interface ReportItem {
  id: number;
  name: string;
  group?: string;
  comments?: string;
  device_type?: string;
  enabled: boolean;
  policy_ids?: number[];
  policy_count?: number;
  created_at?: string;
  updated_at?: string;
}

interface ResultItem {
  id: number;
  policy_id: number;
  backup_id?: number;
  device_id?: string;
  report_id?: number | null;
  passed: boolean;
  detail?: string;
  executed_at?: string;
}

interface ScheduleItem {
  id: number;
  name: string;
  report_id: number;
  target_type: string;
  target_device_ids?: string | null;
  cron_expr?: string | null;
  interval_seconds?: number | null;
  enabled: boolean;
  last_run_at?: string | null;
  updated_at?: string;
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
  const [policyGroupFilter, setPolicyGroupFilter] = useState<string | undefined>(undefined);
  const [policyEnabledFilter, setPolicyEnabledFilter] = useState<boolean | undefined>(undefined);
  const [policySelectedRowKeys, setPolicySelectedRowKeys] = useState<React.Key[]>([]);
  const [policyModalVisible, setPolicyModalVisible] = useState(false);
  const [policyViewVisible, setPolicyViewVisible] = useState(false);
  const [policyViewRecord, setPolicyViewRecord] = useState<PolicyItem | null>(null);
  const [editingPolicyId, setEditingPolicyId] = useState<number | null>(null);
  const [policyForm] = Form.useForm();
  const [reportLoading, setReportLoading] = useState(false);
  const [reportList, setReportList] = useState<ReportItem[]>([]);
  const [reportTotal, setReportTotal] = useState(0);
  const [reportGroupFilter, setReportGroupFilter] = useState<string | undefined>(undefined);
  const [reportSelectedRowKeys, setReportSelectedRowKeys] = useState<React.Key[]>([]);
  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [reportViewVisible, setReportViewVisible] = useState(false);
  const [reportViewRecord, setReportViewRecord] = useState<ReportItem | null>(null);
  const [editingReportId, setEditingReportId] = useState<number | null>(null);
  const [reportForm] = Form.useForm();

  const [resultLoading, setResultLoading] = useState(false);
  const [resultList, setResultList] = useState<ResultItem[]>([]);
  const [resultTotal, setResultTotal] = useState(0);
  const [resultReportFilter, setResultReportFilter] = useState<number | undefined>(undefined);
  const [resultSelectedRowKeys, setResultSelectedRowKeys] = useState<React.Key[]>([]);
  const [resultViewVisible, setResultViewVisible] = useState(false);
  const [resultViewRecord, setResultViewRecord] = useState<ResultItem | null>(null);
  const [runModalVisible, setRunModalVisible] = useState(false);
  const [runForm] = Form.useForm();
  const [backupList, setBackupList] = useState<{ id: number; device_id: string }[]>([]);
  const [backupDevices, setBackupDevices] = useState<{ device_id: string; device_host?: string }[]>([]);
  const [scheduleList, setScheduleList] = useState<ScheduleItem[]>([]);
  const [scheduleModalVisible, setScheduleModalVisible] = useState(false);
  const [editingScheduleId, setEditingScheduleId] = useState<number | null>(null);
  const [scheduleForm] = Form.useForm();

  const loadPolicies = async () => {
    setPolicyLoading(true);
    try {
      const res = await request.get('/config-module/compliance/policies?limit=500');
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

  /** 按分组聚合：一个文件一组，用于「每组一行、统一开关」展示。未分组用「未分组」显示；空组不展示 */
  const policyGroupList = React.useMemo(() => {
    const map = new Map<string, PolicyItem[]>();
    policyList.forEach((p) => {
      const key = p.group != null && p.group !== '' ? p.group : '\0'; // \0 表示未分组
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(p);
    });
    return Array.from(map.entries())
      .filter(([, policies]) => policies.length > 0)
      .map(([key, policies]) => ({
        groupKey: key,
        groupName: key === '\0' ? '未分组' : key,
        policies,
      }));
  }, [policyList]);

  const setGroupEnabled = async (groupKey: string, enabled: boolean) => {
    try {
      const group = groupKey === '\0' ? undefined : groupKey;
      await request.patch('/config-module/compliance/policies/bulk-enabled-by-group', { group: group ?? null, enabled });
      message.success(enabled ? '已启用该组' : '已停用该组');
      loadPolicies();
    } catch (e) {
      message.error('操作失败');
    }
  };

  const deleteGroup = async (groupKey: string) => {
    try {
      const group = groupKey === '\0' ? undefined : groupKey;
      const res = await request.delete(`/config-module/compliance/policies/by-group${group != null ? `?group=${encodeURIComponent(group)}` : ''}`);
      const deleted = (res?.data?.data ?? res?.data)?.deleted ?? 0;
      message.success(`已删除该组，共 ${deleted} 条`);
      loadPolicies();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const loadReports = async () => {
    setReportLoading(true);
    try {
      let url = '/config-module/compliance/reports?limit=200';
      if (reportGroupFilter != null && reportGroupFilter !== '') url += `&group=${encodeURIComponent(reportGroupFilter)}`;
      const res = await request.get(url);
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? data ?? [];
      const tot = data?.total ?? 0;
      setReportList(Array.isArray(items) ? items : []);
      setReportTotal(typeof tot === 'number' ? tot : 0);
    } catch (e) {
      message.error('加载报告列表失败');
      setReportList([]);
    } finally {
      setReportLoading(false);
    }
  };

  const loadResults = async (page = 1, pageSize = 20) => {
    setResultLoading(true);
    try {
      let url = `/config-module/compliance/results?skip=${(page - 1) * pageSize}&limit=${pageSize}`;
      if (resultReportFilter != null && resultReportFilter > 0) url += `&report_id=${resultReportFilter}`;
      const res = await request.get(url);
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

  const loadSchedules = async () => {
    try {
      const res = await request.get('/config-module/compliance/schedules?limit=100');
      const data = res.data?.data ?? res.data;
      const items = data?.items ?? data ?? [];
      setScheduleList(Array.isArray(items) ? items : []);
    } catch (_) {
      setScheduleList([]);
    }
  };

  useEffect(() => { loadPolicies(); }, []);
  useEffect(() => { loadReports(); }, [reportGroupFilter]);
  useEffect(() => { loadResults(1, 20); }, [resultReportFilter]);

  const openAddPolicy = () => {
    setEditingPolicyId(null);
    policyForm.resetFields();
    policyForm.setFieldsValue({ enabled: true });
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
      group: record.group,
      enabled: record.enabled !== false,
    });
    setPolicyModalVisible(true);
  };

  const openViewPolicy = (record: PolicyItem) => {
    setPolicyViewRecord(record);
    setPolicyViewVisible(true);
  };

  const onTogglePolicyEnabled = async (record: PolicyItem) => {
    try {
      await request.patch(`/config-module/compliance/policies/${record.id}/enabled`, { enabled: !record.enabled });
      message.success(record.enabled ? '已禁用' : '已启用');
      loadPolicies();
    } catch (e) {
      message.error('操作失败');
    }
  };

  const batchSetPolicyEnabled = async (enabled: boolean) => {
    if (!policySelectedRowKeys.length) { message.warning('请先选择策略'); return; }
    try {
      for (const id of policySelectedRowKeys) {
        await request.patch(`/config-module/compliance/policies/${id}/enabled`, { enabled });
      }
      message.success(`已${enabled ? '启用' : '停用'} ${policySelectedRowKeys.length} 条`);
      setPolicySelectedRowKeys([]);
      loadPolicies();
    } catch (e) {
      message.error('操作失败');
    }
  };

  const policyExport = async () => {
    try {
      const ids = policySelectedRowKeys.length ? (policySelectedRowKeys as number[]).join(',') : '';
      const url = `/api/config-module/compliance/policies/export${ids ? `?ids=${ids}` : ''}`;
      const token = localStorage.getItem('token');
      const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data?.data ?? data, null, 2)], { type: 'application/json' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'compliance_policies.json'; a.click();
      message.success('导出成功');
    } catch (e) {
      message.error('导出失败');
    }
  };

  const policyImport = async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/config-module/compliance/policies/import', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        message.error((data?.detail ?? data?.message) || '导入失败');
        return false;
      }
      const created = (data?.data ?? data)?.created ?? 0;
      message.success(created > 0 ? `导入完成，新增 ${created} 条策略` : '导入完成，未解析到有效策略（请检查文件格式：JSON 需含 policies 数组，XML 需含 Policy 节点）');
      loadPolicies();
    } catch (e) {
      message.error('导入失败');
    }
    return false; // 阻止默认上传
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

  const openAddReport = () => {
    setEditingReportId(null);
    reportForm.resetFields();
    reportForm.setFieldsValue({ enabled: true });
    setReportModalVisible(true);
  };

  const openEditReport = (record: ReportItem) => {
    setEditingReportId(record.id);
    reportForm.setFieldsValue({
      name: record.name,
      group: record.group,
      comments: record.comments,
      device_type: record.device_type,
      enabled: record.enabled,
      policy_ids: record.policy_ids ?? [],
    });
    setReportModalVisible(true);
  };

  const handleReportSubmit = async () => {
    try {
      const v = await reportForm.validateFields();
      const payload = {
        name: v.name,
        group: v.group || undefined,
        comments: v.comments || undefined,
        device_type: v.device_type || undefined,
        enabled: v.enabled !== false,
        policy_ids: v.policy_ids,
      };
      if (editingReportId != null) {
        await request.put(`/config-module/compliance/reports/${editingReportId}`, payload);
        message.success('报告更新成功');
      } else {
        await request.post('/config-module/compliance/reports', payload);
        message.success('报告新增成功');
      }
      setReportModalVisible(false);
      loadReports();
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error('保存失败');
    }
  };

  const onDeleteReport = async (id: number) => {
    try {
      await request.delete(`/config-module/compliance/reports/${id}`);
      message.success('已删除');
      loadReports();
    } catch (e) {
      message.error('删除失败');
    }
  };

  const onToggleReportEnabled = async (record: ReportItem) => {
    try {
      await request.patch(`/config-module/compliance/reports/${record.id}/enabled`, { enabled: !record.enabled });
      message.success(record.enabled ? '已禁用' : '已启用');
      loadReports();
    } catch (e) {
      message.error('操作失败');
    }
  };

  const openViewReport = (record: ReportItem) => { setReportViewRecord(record); setReportViewVisible(true); };

  const batchSetReportEnabled = async (enabled: boolean) => {
    if (!reportSelectedRowKeys.length) { message.warning('请先选择报告'); return; }
    try {
      for (const id of reportSelectedRowKeys) {
        await request.patch(`/config-module/compliance/reports/${id}/enabled`, { enabled });
      }
      message.success(`已${enabled ? '启用' : '停用'} ${reportSelectedRowKeys.length} 条`);
      setReportSelectedRowKeys([]);
      loadReports();
    } catch (e) {
      message.error('操作失败');
    }
  };

  const reportExport = async (reportId: number) => {
    try {
      const res = await request.get(`/config-module/compliance/reports/${reportId}/export`);
      const data = res.data?.data ?? res.data;
      const xml = typeof data?.xml === 'string' ? data.xml : JSON.stringify(data);
      const blob = new Blob([xml], { type: 'application/xml' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = data?.filename || `report_${reportId}.xml`; a.click();
      message.success('导出成功');
    } catch (e) {
      message.error('导出失败');
    }
  };

  const reportImport = async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    try {
      const token = localStorage.getItem('token');
      await fetch('/api/config-module/compliance/reports/import', { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: form });
      message.success('导入成功');
      loadReports();
    } catch (e) {
      message.error('导入失败');
    }
    return false;
  };

  const openRun = async () => {
    try {
      const [backupRes, devicesRes] = await Promise.all([
        request.get('/config-module/backups?limit=500'),
        request.get('/config-module/backups/devices'),
      ]);
      const backupData = backupRes.data?.data ?? backupRes.data;
      const backupItems = backupData?.items ?? backupData ?? [];
      setBackupList(Array.isArray(backupItems) ? backupItems.map((x: { id: number; device_id: string }) => ({ id: x.id, device_id: x.device_id })) : []);
      const devData = devicesRes.data?.data ?? devicesRes.data;
      const devItems = devData?.items ?? devData ?? [];
      setBackupDevices(Array.isArray(devItems) ? devItems.map((d: { device_id: string; device_host?: string }) => ({ device_id: d.device_id, device_host: d.device_host })) : []);
    } catch (_) {
      setBackupList([]);
      setBackupDevices([]);
    }
    runForm.resetFields();
    setRunModalVisible(true);
  };

  const handleRun = async () => {
    try {
      const v = await runForm.validateFields();
      const body: { backup_id?: number; device_id?: string; device_ids?: string[]; policy_ids?: number[]; report_id?: number; target_by_device_type?: boolean } = {};
      if (v.report_id) {
        body.report_id = v.report_id;
        if (v.run_target === 'by_device_type') body.target_by_device_type = true;
        else if (v.run_target === 'backup' && v.backup_id) body.backup_id = v.backup_id;
        else if (v.run_target === 'device' && v.device_id) body.device_id = v.device_id;
        else if (v.run_target === 'devices' && v.device_ids?.length) body.device_ids = v.device_ids;
      } else {
        if (v.target_type === 'backup' && v.backup_id) body.backup_id = v.backup_id;
        if (v.target_type === 'device' && v.device_id) body.device_id = v.device_id;
        if (v.policy_ids?.length) body.policy_ids = v.policy_ids;
      }
      const res = await request.post('/config-module/compliance/run', body);
      const data = res.data?.data ?? res.data;
      message.success(data?.device_count != null ? `执行完成，共 ${data.device_count} 台设备` : '合规检查已执行');
      setRunModalVisible(false);
      loadResults(1, 20);
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      const err = e as { response?: { data?: { detail?: string } } };
      message.error(err?.response?.data?.detail ?? '执行失败');
    }
  };

  const enabledReports = reportList.filter((r) => r.enabled);

  const resultExport = async () => {
    let url = `/api/config-module/compliance/results/export?limit=5000`;
    if (resultReportFilter) url += `&report_id=${resultReportFilter}`;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      const blob = await res.blob();
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'compliance_results.csv'; a.click();
      message.success('导出成功');
    } catch (e) {
      message.error('导出失败');
    }
  };

  const batchDeleteResults = async () => {
    if (!resultSelectedRowKeys.length) { message.warning('请先选择结果'); return; }
    try {
      const res = await request.post('/config-module/compliance/results/batch-delete', { ids: resultSelectedRowKeys });
      const data = res.data?.data ?? res.data;
      message.success(`已删除 ${data?.deleted ?? 0} 条`);
      setResultSelectedRowKeys([]);
      loadResults(1, 20);
    } catch (e) {
      message.error('删除失败');
    }
  };

  const openViewResult = (record: ResultItem) => { setResultViewRecord(record); setResultViewVisible(true); };

  const runScheduleNow = async (id: number) => {
    try {
      await request.post(`/config-module/compliance/schedules/${id}/run`);
      message.success('已触发执行');
      loadSchedules();
      loadResults(1, 20);
    } catch (e) {
      message.error('执行失败');
    }
  };

  const openAddSchedule = () => {
    setEditingScheduleId(null);
    scheduleForm.resetFields();
    scheduleForm.setFieldsValue({ target_type: 'by_device_type', enabled: true });
    setScheduleModalVisible(true);
  };

  const openEditSchedule = (record: ScheduleItem) => {
    setEditingScheduleId(record.id);
    try {
      const deviceIds = record.target_device_ids ? JSON.parse(record.target_device_ids as unknown as string) : undefined;
      scheduleForm.setFieldsValue({
        name: record.name,
        report_id: record.report_id,
        target_type: record.target_type,
        target_device_ids: deviceIds,
        cron_expr: record.cron_expr,
        interval_seconds: record.interval_seconds,
        enabled: record.enabled,
      });
    } catch (_) {
      scheduleForm.setFieldsValue({ name: record.name, report_id: record.report_id, target_type: record.target_type, enabled: record.enabled });
    }
    setScheduleModalVisible(true);
  };

  const handleScheduleSubmit = async () => {
    try {
      const v = await scheduleForm.validateFields();
      const payload = {
        name: v.name,
        report_id: v.report_id,
        target_type: v.target_type,
        target_device_ids: v.target_type === 'device_ids' ? v.target_device_ids : undefined,
        cron_expr: v.cron_expr || undefined,
        interval_seconds: v.interval_seconds || undefined,
        enabled: v.enabled !== false,
      };
      if (editingScheduleId != null) {
        await request.put(`/config-module/compliance/schedules/${editingScheduleId}`, payload);
        message.success('计划已更新');
      } else {
        await request.post('/config-module/compliance/schedules', payload);
        message.success('计划已创建');
      }
      setScheduleModalVisible(false);
      loadSchedules();
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return;
      message.error('保存失败');
    }
  };

  const onDeleteSchedule = async (id: number) => {
    try {
      await request.delete(`/config-module/compliance/schedules/${id}`);
      message.success('已删除');
      loadSchedules();
    } catch (e) {
      message.error('删除失败');
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 24 }}>合规检查</h2>
      <Tabs
        defaultActiveKey="policies"
        items={[
          {
            key: 'policies',
            label: '策略管理',
            children: (
              <Card>
                <div style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <Button type="primary" onClick={openAddPolicy}>新增</Button>
                    <Upload accept=".json,.xml" showUploadList={false} beforeUpload={(f) => { policyImport(f); return false; }}>
                      <Button>导入</Button>
                    </Upload>
                    <Button onClick={policyExport}>导出</Button>
                  </Space>
                  <div style={{ marginTop: 6, color: '#666', fontSize: 12 }}>按文件导入为一组，每组一行、统一启用/停用；展开可查看、编辑单条规则。</div>
                </div>
                <Table
                  loading={policyLoading}
                  dataSource={policyGroupList}
                  rowKey="groupKey"
                  size="small"
                  pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 组` }}
                  expandable={{
                    expandedRowRender: (record: { groupKey: string; groupName: string; policies: PolicyItem[] }) => (
                      <Table
                        size="small"
                        dataSource={record.policies}
                        rowKey="id"
                        pagination={false}
                        columns={[
                          { title: 'ID', dataIndex: 'id', width: 60 },
                          { title: '名称', dataIndex: 'name', width: 160 },
                          { title: '规则类型', dataIndex: 'rule_type', width: 90, render: (t: string) => RULE_TYPES.find(r => r.value === t)?.label ?? t },
                          { title: '规则内容', dataIndex: 'rule_content', ellipsis: true },
                          {
                            title: '操作',
                            key: 'action',
                            width: 150,
                            render: (_: unknown, row: PolicyItem) => (
                              <Space>
                                <a onClick={() => openViewPolicy(row)}>查看</a>
                                <a onClick={() => openEditPolicy(row)}>编辑</a>
                                <Popconfirm title="确定删除该条规则？" onConfirm={() => onDeletePolicy(row.id)}>
                                  <a style={{ color: '#ff4d4f' }}>删除</a>
                                </Popconfirm>
                              </Space>
                            ),
                          },
                        ]}
                      />
                    ),
                  }}
                  columns={[
                    { title: '分组名称', dataIndex: 'groupName', width: 220 },
                    { title: '策略数', dataIndex: 'policies', width: 80, render: (p: PolicyItem[]) => p?.length ?? 0 },
                    {
                      title: '启用',
                      width: 80,
                      render: (_: unknown, record: { groupKey: string; groupName: string; policies: PolicyItem[] }) => {
                        const allEnabled = record.policies.length > 0 && record.policies.every((p) => p.enabled !== false);
                        return (
                          <Switch
                            size="small"
                            checked={allEnabled}
                            onChange={(checked) => setGroupEnabled(record.groupKey, checked)}
                          />
                        );
                      },
                    },
                    {
                      title: '操作',
                      key: 'action',
                      width: 120,
                      render: (_: unknown, record: { groupKey: string; groupName: string; policies: PolicyItem[] }) => (
                        <Popconfirm title={`确定删除整组「${record.groupName}」？共 ${record.policies.length} 条规则。`} onConfirm={() => deleteGroup(record.groupKey)}>
                          <a style={{ color: '#ff4d4f' }}>删除整组</a>
                        </Popconfirm>
                      ),
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'reports',
            label: '报告管理',
            children: (
              <Card>
                <div style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <Button type="primary" onClick={openAddReport}>新建</Button>
                    <Button onClick={() => reportSelectedRowKeys.length === 1 && openViewReport(reportList.find(r => r.id === reportSelectedRowKeys[0])!)}
                      disabled={reportSelectedRowKeys.length !== 1}>查看</Button>
                    <Button onClick={() => reportSelectedRowKeys.length === 1 && openEditReport(reportList.find(r => r.id === reportSelectedRowKeys[0])!)}
                      disabled={reportSelectedRowKeys.length !== 1}>编辑</Button>
                    <Button onClick={() => batchSetReportEnabled(true)} disabled={!reportSelectedRowKeys.length}>批量启用</Button>
                    <Button onClick={() => batchSetReportEnabled(false)} disabled={!reportSelectedRowKeys.length}>批量停用</Button>
                    <Upload accept=".xml" showUploadList={false} beforeUpload={(f) => { reportImport(f); return false; }}>
                      <Button>导入</Button>
                    </Upload>
                    <Button onClick={() => reportSelectedRowKeys.length === 1 && reportExport(reportSelectedRowKeys[0] as number)} disabled={reportSelectedRowKeys.length !== 1}>导出</Button>
                    <Popconfirm title="确定删除所选？" onConfirm={async () => { for (const id of reportSelectedRowKeys) await request.delete(`/config-module/compliance/reports/${id}`); setReportSelectedRowKeys([]); loadReports(); message.success('已删除'); }}
                      disabled={!reportSelectedRowKeys.length}>
                      <Button danger disabled={!reportSelectedRowKeys.length}>删除选中</Button>
                    </Popconfirm>
                    <Select placeholder="按分组" allowClear style={{ width: 160 }} value={reportGroupFilter} onChange={(val) => setReportGroupFilter(val)}
                      options={Array.from(new Set(reportList.map(r => r.group).filter(Boolean))).map(g => ({ value: g!, label: g }))} />
                  </Space>
                </div>
                <Table
                  loading={reportLoading}
                  dataSource={reportList}
                  rowKey="id"
                  size="small"
                  rowSelection={{ selectedRowKeys: reportSelectedRowKeys, onChange: setReportSelectedRowKeys }}
                  pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '名称', dataIndex: 'name', width: 160 },
                    { title: '分组', dataIndex: 'group', width: 120 },
                    { title: '策略数', dataIndex: 'policy_count', width: 80 },
                    { title: '启用', dataIndex: 'enabled', width: 70, render: (v: boolean, record: ReportItem) => <Switch size="small" checked={v} onChange={() => onToggleReportEnabled(record)} /> },
                    { title: '更新时间', dataIndex: 'updated_at', width: 180 },
                    {
                      title: '操作',
                      key: 'action',
                      width: 180,
                      render: (_: unknown, record: ReportItem) => (
                        <Space>
                          <a onClick={() => openViewReport(record)}>查看</a>
                          <a onClick={() => openEditReport(record)}>编辑</a>
                          <a onClick={() => reportExport(record.id)}>导出</a>
                          <Popconfirm title="确定删除？" onConfirm={() => onDeleteReport(record.id)}>
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
                <div style={{ marginBottom: 16 }}>
                  <Space>
                    <Button type="primary" onClick={openRun}>立即执行（手动）</Button>
                    <Button onClick={loadSchedules}>刷新计划</Button>
                  </Space>
                </div>
                <p style={{ color: '#666', marginBottom: 16 }}>可按报告执行（选择已启用报告并指定本次目标），或不选报告时按备份/设备+策略执行。下方为执行计划，启用后可按计划自动执行（需调度支持）；可点击「立即执行」手动触发一次。</p>
                <Table
                  dataSource={scheduleList}
                  rowKey="id"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: '名称', dataIndex: 'name', width: 140 },
                    { title: '报告ID', dataIndex: 'report_id', width: 80 },
                    { title: '目标', dataIndex: 'target_type', width: 120, render: (t: string) => t === 'by_device_type' ? '按设备类型' : '指定设备' },
                    { title: 'Cron/间隔', dataIndex: 'cron_expr', width: 120, render: (_: unknown, r: ScheduleItem) => r.cron_expr || (r.interval_seconds ? `${r.interval_seconds}秒` : '—') },
                    { title: '启用', dataIndex: 'enabled', width: 70, render: (v: boolean) => v ? '是' : '否' },
                    { title: '上次执行', dataIndex: 'last_run_at', width: 160 },
                    { title: '操作', key: 'action', render: (_: unknown, record: ScheduleItem) => <Button size="small" onClick={() => runScheduleNow(record.id)}>立即执行</Button> },
                  ]}
                />
                {scheduleList.length === 0 && <p style={{ color: '#999', marginTop: 12 }}>暂无执行计划，可联系管理员配置。</p>}
              </Card>
            ),
          },
          {
            key: 'results',
            label: '结果列表',
            children: (
              <Card>
                <div style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <Button onClick={() => loadResults(1, 20)}>刷新</Button>
                    <Button onClick={resultExport}>导出 CSV</Button>
                    <Popconfirm title="确定删除所选结果？" onConfirm={batchDeleteResults} disabled={!resultSelectedRowKeys.length}>
                      <Button danger disabled={!resultSelectedRowKeys.length}>删除选中</Button>
                    </Popconfirm>
                    <Select placeholder="按报告筛选" allowClear style={{ width: 200 }} value={resultReportFilter} onChange={(val) => setResultReportFilter(val)}
                      options={[{ value: undefined, label: '全部' }, ...reportList.map(r => ({ value: r.id, label: r.name }))]} />
                  </Space>
                </div>
                <Table
                  loading={resultLoading}
                  dataSource={resultList}
                  rowKey="id"
                  size="small"
                  rowSelection={{ selectedRowKeys: resultSelectedRowKeys, onChange: setResultSelectedRowKeys }}
                  pagination={{ total: resultTotal, pageSize: 20, showTotal: (t) => `共 ${t} 条`, onChange: (p, ps) => loadResults(p, ps || 20) }}
                  columns={[
                    { title: 'ID', dataIndex: 'id', width: 70 },
                    { title: '策略ID', dataIndex: 'policy_id', width: 80 },
                    { title: '设备', dataIndex: 'device_id', width: 120 },
                    { title: '备份ID', dataIndex: 'backup_id', width: 80 },
                    { title: '报告', dataIndex: 'report_id', width: 120, render: (rid: number | null) => (rid ? reportList.find(r => r.id === rid)?.name ?? `#${rid}` : '—') },
                    { title: '通过', dataIndex: 'passed', width: 70, render: (v: boolean) => (v ? '是' : '否') },
                    { title: '说明', dataIndex: 'detail', ellipsis: true },
                    { title: '执行时间', dataIndex: 'executed_at', width: 180 },
                    { title: '操作', key: 'action', width: 80, render: (_: unknown, record: ResultItem) => <a onClick={() => openViewResult(record)}>查看</a> },
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
          <Form.Item name="group" label="分组">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <Input placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="策略详情" open={policyViewVisible} onClose={() => setPolicyViewVisible(false)} width={520}>
        {policyViewRecord && (
          <div>
            <p><strong>名称</strong>：{policyViewRecord.name}</p>
            <p><strong>分组</strong>：{policyViewRecord.group ?? '—'}</p>
            <p><strong>规则类型</strong>：{RULE_TYPES.find(r => r.value === policyViewRecord.rule_type)?.label ?? policyViewRecord.rule_type}</p>
            <p><strong>规则内容</strong>：<pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 8 }}>{policyViewRecord.rule_content}</pre></p>
            <p><strong>设备类型</strong>：{policyViewRecord.device_type ?? '—'}</p>
            <p><strong>启用</strong>：{policyViewRecord.enabled !== false ? '是' : '否'}</p>
            <p><strong>说明</strong>：{policyViewRecord.description ?? '—'}</p>
          </div>
        )}
      </Drawer>

      <Modal
        title={editingReportId != null ? '编辑报告' : '新建报告'}
        open={reportModalVisible}
        onOk={handleReportSubmit}
        onCancel={() => setReportModalVisible(false)}
        width={560}
        destroyOnClose
      >
        <Form form={reportForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="报告名称" rules={[{ required: true }]}>
            <Input placeholder="名称" />
          </Form.Item>
          <Form.Item name="group" label="分组（文件夹）">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item name="comments" label="说明">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
          <Form.Item name="device_type" label="适用设备类型">
            <Input placeholder="可选，执行时可按设备类型纳入目标" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="policy_ids" label="关联策略">
            <Select
              mode="multiple"
              placeholder="选择策略"
              options={policyList.map((p) => ({ value: p.id, label: `${p.name} (${p.rule_type})` }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="报告详情" open={reportViewVisible} onClose={() => setReportViewVisible(false)} width={520}>
        {reportViewRecord && (
          <div>
            <p><strong>名称</strong>：{reportViewRecord.name}</p>
            <p><strong>分组</strong>：{reportViewRecord.group ?? '—'}</p>
            <p><strong>说明</strong>：{reportViewRecord.comments ?? '—'}</p>
            <p><strong>适用设备类型</strong>：{reportViewRecord.device_type ?? '—'}</p>
            <p><strong>启用</strong>：{reportViewRecord.enabled ? '是' : '否'}</p>
            <p><strong>关联策略数</strong>：{reportViewRecord.policy_count ?? 0}</p>
          </div>
        )}
      </Drawer>

      <Modal
        title="执行合规检查"
        open={runModalVisible}
        onOk={handleRun}
        onCancel={() => setRunModalVisible(false)}
        width={520}
      >
        <Form form={runForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="report_id" label="按报告执行（可选）">
            <Select
              allowClear
              placeholder="不选则按下方备份/设备+策略执行"
              options={enabledReports.map((r) => ({ value: r.id, label: `${r.name}${r.device_type ? ` [${r.device_type}]` : ''}` }))}
            />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.report_id !== cur.report_id}>
            {({ getFieldValue }) => {
              const reportId = getFieldValue('report_id');
              const report = reportId ? enabledReports.find((r) => r.id === reportId) : null;
              if (reportId && report) {
                return (
                  <>
                    <Form.Item name="run_target" label="本次执行目标" rules={[{ required: true }]}>
                      <Select
                        options={[
                          ...(report.device_type ? [{ value: 'by_device_type', label: `按设备类型（${report.device_type}）` }] : []),
                          { value: 'backup', label: '指定备份' },
                          { value: 'device', label: '指定设备（取最新备份）' },
                          { value: 'devices', label: '多台设备（取各设备最新备份）' },
                        ]}
                        placeholder="选择目标"
                      />
                    </Form.Item>
                    <Form.Item noStyle shouldUpdate={(prev, cur) => prev.run_target !== cur.run_target}>
                      {({ getFieldValue: g }) => {
                        const target = g('run_target');
                        if (target === 'backup') {
                          return (
                            <Form.Item name="backup_id" label="备份" rules={[{ required: true }]}>
                              <Select
                                placeholder="选择备份"
                                showSearch
                                optionFilterProp="label"
                                options={backupList.map((b) => ({ value: b.id, label: `#${b.id} ${b.device_id}` }))}
                              />
                            </Form.Item>
                          );
                        }
                        if (target === 'device') {
                          return (
                            <Form.Item name="device_id" label="设备标识" rules={[{ required: true }]}>
                              <Select
                                placeholder="选择或输入设备"
                                showSearch
                                optionFilterProp="label"
                                options={backupDevices.map((d) => ({ value: d.device_id, label: d.device_host || d.device_id }))}
                              />
                            </Form.Item>
                          );
                        }
                        if (target === 'devices') {
                          return (
                            <Form.Item name="device_ids" label="设备（多选）" rules={[{ required: true }]}>
                              <Select
                                mode="multiple"
                                placeholder="选择设备"
                                showSearch
                                optionFilterProp="label"
                                options={backupDevices.map((d) => ({ value: d.device_id, label: d.device_host || d.device_id }))}
                              />
                            </Form.Item>
                          );
                        }
                        return null;
                      }}
                    </Form.Item>
                  </>
                );
              }
              return (
                <>
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
                            options={backupList.map((b) => ({ value: b.id, label: `#${b.id} ${b.device_id}` }))}
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
                      options={policyList.map((p) => ({ value: p.id, label: `${p.name} (${p.rule_type})` }))}
                    />
                  </Form.Item>
                </>
              );
            }}
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={editingScheduleId != null ? '编辑执行计划' : '新增执行计划'} open={scheduleModalVisible} onOk={handleScheduleSubmit} onCancel={() => setScheduleModalVisible(false)} width={480}>
        <Form form={scheduleForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="计划名称" rules={[{ required: true }]}>
            <Input placeholder="名称" />
          </Form.Item>
          <Form.Item name="report_id" label="报告" rules={[{ required: true }]}>
            <Select options={reportList.filter(r => r.enabled).map(r => ({ value: r.id, label: r.name }))} placeholder="选择报告" />
          </Form.Item>
          <Form.Item name="target_type" label="目标类型" rules={[{ required: true }]}>
            <Select options={[{ value: 'by_device_type', label: '按设备类型' }, { value: 'device_ids', label: '指定设备' }]} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.target_type !== cur.target_type}>
            {({ getFieldValue }) => getFieldValue('target_type') === 'device_ids' && (
              <Form.Item name="target_device_ids" label="设备ID列表">
                <Select mode="tags" placeholder="输入或选择设备ID" options={backupDevices.map(d => ({ value: d.device_id, label: d.device_host || d.device_id }))} />
              </Form.Item>
            )}
          </Form.Item>
          <Form.Item name="cron_expr" label="Cron 表达式">
            <Input placeholder="如 0 0 * * * 每天零点" />
          </Form.Item>
          <Form.Item name="interval_seconds" label="执行间隔（秒）">
            <Input type="number" placeholder="与 Cron 二选一" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="结果详情" open={resultViewVisible} onClose={() => setResultViewVisible(false)} width={480}>
        {resultViewRecord && (
          <div>
            <p><strong>ID</strong>：{resultViewRecord.id}</p>
            <p><strong>策略ID</strong>：{resultViewRecord.policy_id}</p>
            <p><strong>设备</strong>：{resultViewRecord.device_id ?? '—'}</p>
            <p><strong>备份ID</strong>：{resultViewRecord.backup_id ?? '—'}</p>
            <p><strong>报告</strong>：{resultViewRecord.report_id ? (reportList.find(r => r.id === resultViewRecord.report_id)?.name ?? `#${resultViewRecord.report_id}`) : '—'}</p>
            <p><strong>通过</strong>：{resultViewRecord.passed ? '是' : '否'}</p>
            <p><strong>说明</strong>：{resultViewRecord.detail ?? '—'}</p>
            <p><strong>执行时间</strong>：{resultViewRecord.executed_at ?? '—'}</p>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default ConfigModuleCompliance;
