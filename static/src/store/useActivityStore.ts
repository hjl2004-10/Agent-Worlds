import { create } from 'zustand';
import { activityApi } from '@/api';
import type { ActivityEvent } from '@/api/activity';

interface ActivityStore {
  events: ActivityEvent[];
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

export const useActivityStore = create<ActivityStore>((set) => ({
  events: [],
  loading: false,
  error: null,

  fetch: async () => {
    try {
      const { data } = await activityApi.getEvents(50);
      if (data.status === 'ok') {
        set({ events: data.events, error: null });
      }
    } catch (err) {
      set({ error: '获取事件失败' });
    }
  },
}));
