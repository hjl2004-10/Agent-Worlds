import { create } from 'zustand';
import { taskApi, toolsApi } from '@/api';
import type { Task, Tool } from '@/api/types';

interface TaskStore {
  // 状态
  tasks: Record<string, Task[]>; // npcName -> tasks
  tools: Record<string, Tool>;
  selectedNPC: string | null;
  loading: boolean;
  message: { type: 'success' | 'error'; text: string } | null;

  // 操作
  selectNPC: (npcName: string) => void;
  fetchTasks: (npcName: string) => Promise<void>;
  fetchTools: () => Promise<void>;
  assignTask: (target: string, hint: string, toolHint?: string) => Promise<boolean>;
  completeTask: (npcName: string, hint: string) => Promise<boolean>;
  deleteTask: (npcName: string, hint: string) => Promise<boolean>;
  clearMessage: () => void;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: {},
  tools: {},
  selectedNPC: null,
  loading: false,
  message: null,

  selectNPC: (npcName: string) => {
    set({ selectedNPC: npcName });
    get().fetchTasks(npcName);
  },

  fetchTasks: async (npcName: string) => {
    set({ loading: true });
    try {
      const { data } = await taskApi.getList(npcName);
      if (data.status === 'ok') {
        set((state) => ({
          tasks: { ...state.tasks, [npcName]: data.tasks },
        }));
      }
    } catch {
      set({ message: { type: 'error', text: '获取任务失败' } });
    } finally {
      set({ loading: false });
    }
  },

  fetchTools: async () => {
    try {
      const { data } = await toolsApi.getAll();
      if (data.status === 'ok') {
        set({ tools: data.tools });
      }
    } catch (err) {
      console.error('Fetch tools failed:', err);
    }
  },

  assignTask: async (target: string, hint: string, toolHint?: string) => {
    try {
      const { data } = await taskApi.assign({ target, hint, tool_hint: toolHint });
      if (data.status === 'ok') {
        set({ message: { type: 'success', text: `任务已下放给 ${target}` } });
        get().fetchTasks(target);
        return true;
      }
      set({ message: { type: 'error', text: data.message || '下放失败' } });
      return false;
    } catch {
      set({ message: { type: 'error', text: '网络错误' } });
      return false;
    }
  },

  completeTask: async (npcName: string, hint: string) => {
    try {
      const { data } = await taskApi.complete(npcName, hint);
      if (data.status === 'ok') {
        set({ message: { type: 'success', text: `已标记 ${data.completed} 个任务为完成` } });
        get().fetchTasks(npcName);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },

  deleteTask: async (npcName: string, hint: string) => {
    try {
      const { data } = await taskApi.delete(npcName, hint);
      if (data.status === 'ok') {
        set({ message: { type: 'success', text: `已删除 ${data.deleted} 个任务` } });
        get().fetchTasks(npcName);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },

  clearMessage: () => set({ message: null }),
}));
