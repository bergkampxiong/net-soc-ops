/**
 * IPAM 表格导入：表头须与后端 services/ipam_csv_import.py 中 AGGREGATE_CSV_HEADERS / PREFIX_CSV_HEADERS 完全一致
 */
export const IPAM_AGGREGATE_CSV_HEADERS = ['网段', '分配机构', '分配日期', '描述'] as const;

export const IPAM_PREFIX_CSV_HEADERS = [
  '网段',
  '状态',
  '描述',
  '地址池',
  '标记已用',
  'VLAN',
  '位置',
  '所属聚合网段',
  '聚合ID',
] as const;

/** 下载 UTF-8 BOM CSV 模板（仅表头行） */
export function downloadIpamCsvTemplate(fileName: string, headers: readonly string[]): void {
  const BOM = '\ufeff';
  const blob = new Blob([BOM + headers.join(',') + '\n'], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(link.href);
}
