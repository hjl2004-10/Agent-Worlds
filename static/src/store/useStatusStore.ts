import { create } from 'zustand';
import { statusApi } from '@/api';

interface StatusStore {
  tick: number;
  npcCount: number;
  date: string;
  time: string;
  period: string;
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

export const useStatusStore = create<StatusStore>((set) => ({
  tick: 0,
  npcCount: 0,
  date: '',
  time: '',
  period: '',
  loading: false,
  error: null,

  fetch: async () => {
    try {
      const { data } = await statusApi.getStatus();
      set({
        tick: data.tick,
        npcCount: data.npc_count,
        date: data.date,
        time: data.time,
        period: data.period,
        error: null,
      });
    } catch (err) {
      set({ error: '连接失败' });
    }
  },
}));
