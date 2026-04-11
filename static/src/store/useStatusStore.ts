import { create } from 'zustand';
import { statusApi } from '@/api';

interface StatusStore {
  tick: number;
  npcCount: number;
  date: string;
  dateIso: string;
  time: string;
  period: string;
  periodKey: string;
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

export const useStatusStore = create<StatusStore>((set) => ({
  tick: 0,
  npcCount: 0,
  date: '',
  dateIso: '',
  time: '',
  period: '',
  periodKey: '',
  loading: false,
  error: null,

  fetch: async () => {
    try {
      const { data } = await statusApi.getStatus();
      set({
        tick: data.tick,
        npcCount: data.npc_count,
        date: data.date,
        dateIso: data.date_iso || '',
        time: data.time,
        period: data.period,
        periodKey: data.period_key || '',
        error: null,
      });
    } catch (err) {
      set({ error: 'Connection failed' });
    }
  },
}));
