/**
 * useFormStore - 表单状态管理
 *
 * 管理待处理表单、当前表单、提交状态等
 */
import { create } from 'zustand';
import { formApi, type Form, type FormResponse } from '@/api';

interface FormState {
  // 状态
  forms: Form[];
  currentForm: Form | null;
  loading: boolean;
  error: string | null;
  pendingCount: number;

  // 操作
  fetchPendingForms: () => Promise<void>;
  getPendingCount: () => number;
  openForm: (form: Form) => void;
  closeForm: () => void;
  submitForm: (formId: string, response: FormResponse) => Promise<boolean>;
  cancelForm: (formId: string) => Promise<boolean>;
  clearError: () => void;
}

export const useFormStore = create<FormState>((set, get) => ({
  // 初始状态
  forms: [],
  currentForm: null,
  loading: false,
  error: null,
  pendingCount: 0,

  // 获取待处理表单
  fetchPendingForms: async () => {
    set({ loading: true, error: null });
    try {
      const { data } = await formApi.getPendingForms();
      if (data.status === 'ok') {
        set({
          forms: data.forms,
          pendingCount: data.count,
          loading: false,
        });
      } else {
        set({ loading: false, error: '获取表单失败' });
      }
    } catch (error) {
      set({ loading: false, error: String(error) });
    }
  },

  // 获取待处理数量
  getPendingCount: () => get().pendingCount,

  // 打开表单
  openForm: (form: Form) => {
    set({ currentForm: form });
  },

  // 关闭表单
  closeForm: () => {
    set({ currentForm: null });
  },

  // 提交表单
  submitForm: async (formId: string, response: FormResponse) => {
    set({ loading: true, error: null });
    try {
      const { data } = await formApi.submitForm(formId, response);
      if (data.status === 'ok') {
        // 从列表中移除已提交的表单
        const forms = get().forms.filter(f => f.id !== formId);
        set({
          forms,
          pendingCount: forms.length,
          currentForm: null,
          loading: false,
        });
        return true;
      } else {
        set({ loading: false, error: data.reason || '提交失败' });
        return false;
      }
    } catch (error) {
      set({ loading: false, error: String(error) });
      return false;
    }
  },

  // 取消表单
  cancelForm: async (formId: string) => {
    try {
      const { data } = await formApi.cancelForm(formId);
      if (data.status === 'ok') {
        const forms = get().forms.filter(f => f.id !== formId);
        set({
          forms,
          pendingCount: forms.length,
          currentForm: null,
        });
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },

  // 清除错误
  clearError: () => set({ error: null }),
}));
