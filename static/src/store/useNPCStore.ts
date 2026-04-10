import { create } from 'zustand';
import { npcApi } from '@/api';
import type { NPC } from '@/api/types';

interface NPCStore {
  npcs: NPC[];
  loading: boolean;
  error: string | null;
  fetch: () => Promise<void>;
}

export const useNPCStore = create<NPCStore>((set) => ({
  npcs: [],
  loading: false,
  error: null,

  fetch: async () => {
    try {
      const { data } = await npcApi.getAll();
      set({ npcs: data, error: null });
    } catch (err) {
      set({ error: '获取 NPC 列表失败' });
    }
  },
}));
