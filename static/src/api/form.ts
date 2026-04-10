import client from './client';

// ========== Types ==========

export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'multiselect' | 'number' | 'checkbox';
  required?: boolean;
  options?: Array<{ label: string; value: string }>;
  default?: string | number | boolean;
  placeholder?: string;
}

export interface Form {
  id: string;
  title: string;
  description: string;
  fields: FormField[];
  from_npc: string;
  created_at: string;
  timeout: number;
  expires_at: number;
}

export interface FormResponse {
  [fieldName: string]: string | number | boolean | string[];
}

export interface PendingFormsResponse {
  status: string;
  forms: Form[];
  count: number;
}

export interface FormDetailResponse {
  status: string;
  form: Form;
}

export interface SubmitResponse {
  status: string;
  message?: string;
  reason?: string;
}

// ========== API ==========

export const formApi = {
  /**
   * 获取待处理的表单列表
   */
  getPendingForms: () =>
    client.get<PendingFormsResponse>('/form/pending'),

  /**
   * 获取指定表单详情
   */
  getForm: (formId: string) =>
    client.get<FormDetailResponse>(`/form/${formId}`),

  /**
   * 提交表单响应
   */
  submitForm: (formId: string, response: FormResponse) =>
    client.post<SubmitResponse>(`/form/${formId}/submit`, response),

  /**
   * 取消表单
   */
  cancelForm: (formId: string) =>
    client.post<SubmitResponse>(`/form/${formId}/cancel`),
};
