import request from '../utils/request';

/**
 * 流程代码生成API
 */
export const processCodeGeneratorApi = {
  /**
   * 生成流程代码
   * @param processId 流程ID
   * @returns 生成的代码文件
   */
  generate: (processId: string) => {
    return request({
      url: `/process-definitions/${processId}/generate-code`,
      method: 'post',
      responseType: 'blob'
    });
  }
}; 