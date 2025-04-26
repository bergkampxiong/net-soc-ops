import request from '../../utils/request';

// 获取作业模板列表
export const getJobTemplates = () => {
  return request.get('/config-generator/job-templates');
}; 