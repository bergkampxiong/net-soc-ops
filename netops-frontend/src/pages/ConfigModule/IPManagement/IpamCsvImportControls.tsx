/**
 * IP 管理：CSV 表格导入控件（下载模板 + 上传导入 + 结果弹窗）
 */
import React, { useState } from 'react';
import { Button, Upload, Modal, Alert, Table, Space, message } from 'antd';
import { DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import request from '../../../utils/request';
import { downloadIpamCsvTemplate } from './ipamImportTemplates';

export interface IpamTableImportResult {
  imported: number;
  updated: number;
  failed: number;
  errors?: string[] | null;
}

interface IpamCsvImportControlsProps {
  importEndpoint: string;
  templateFileName: string;
  headers: readonly string[];
  onImported: () => void;
}

const IpamCsvImportControls: React.FC<IpamCsvImportControlsProps> = ({
  importEndpoint,
  templateFileName,
  headers,
  onImported,
}) => {
  const [importing, setImporting] = useState(false);
  const [resultOpen, setResultOpen] = useState(false);
  const [lastResult, setLastResult] = useState<IpamTableImportResult | null>(null);

  const uploadProps: UploadProps = {
    accept: '.csv',
    showUploadList: false,
    beforeUpload: (file) => {
      const reader = new FileReader();
      reader.onload = async () => {
        const text = reader.result as string;
        setImporting(true);
        try {
          const res = await request.post(importEndpoint, { content: text });
          const data = (res.data?.data ?? res.data) as IpamTableImportResult;
          setLastResult(data);
          setResultOpen(true);
          message.success(`导入完成：新增 ${data?.imported ?? 0}，更新 ${data?.updated ?? 0}，失败 ${data?.failed ?? 0}`);
          onImported();
        } catch (e: unknown) {
          const err = e as { response?: { data?: { detail?: string } } };
          message.error(err?.response?.data?.detail || '导入失败');
        } finally {
          setImporting(false);
        }
      };
      reader.readAsText(file, 'UTF-8');
      return false;
    },
  };

  return (
    <>
      <Space wrap>
        <Button icon={<DownloadOutlined />} onClick={() => downloadIpamCsvTemplate(templateFileName, headers)}>
          下载导入模板
        </Button>
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />} loading={importing}>
            表格导入
          </Button>
        </Upload>
      </Space>
      <Modal
        title="导入结果"
        open={resultOpen}
        onCancel={() => setResultOpen(false)}
        footer={null}
        width={720}
        destroyOnClose
      >
        {lastResult && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Alert
              type={lastResult.failed > 0 ? 'warning' : 'success'}
              message={`新增 ${lastResult.imported} 条，更新 ${lastResult.updated} 条，失败 ${lastResult.failed} 条`}
            />
            {lastResult.errors && lastResult.errors.length > 0 && (
              <Table
                size="small"
                pagination={{ pageSize: 8 }}
                rowKey={(_, i) => String(i)}
                dataSource={lastResult.errors.map((t, i) => ({ key: i, text: t }))}
                columns={[{ title: '说明', dataIndex: 'text', ellipsis: true }]}
              />
            )}
          </Space>
        )}
      </Modal>
    </>
  );
};

export default IpamCsvImportControls;
