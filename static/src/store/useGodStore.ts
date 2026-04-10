import { create } from 'zustand';
import { godApi } from '@/api';

// 移动方向 ref (用于客户端预测)
export const godMoveDirectionRef = { current: null as string | null };
// 受控 NPC 的前端预测位置 (用于退出控制时提交给后端)
export const godPredictedPositionRef = { current: null as { x: number; y: number } | null };

interface GodStore {
  selectedNPC: string | null;
  isGodMode: boolean;
  selectNPC: (name: string) => Promise<boolean>;
  deselectNPC: () => Promise<void>;
  move: (direction: 'up' | 'down' | 'left' | 'right') => Promise<void>;
  stop: () => Promise<void>;
  fetchStatus: () => Promise<void>;
}

export const useGodStore = create<GodStore>((set, get) => ({
  selectedNPC: null,
  isGodMode: false,

  selectNPC: async (name: string) => {
    try {
      const { data } = await godApi.select(name);
      if (data.status === 'ok') {
        set({ selectedNPC: name, isGodMode: true });
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },

  deselectNPC: async () => {
    try {
      // 获取前端预测位置并提交给后端
      const predictedPos = godPredictedPositionRef.current;
      await godApi.deselect(predictedPos?.x, predictedPos?.y);
      godMoveDirectionRef.current = null;
      godPredictedPositionRef.current = null;
      set({ selectedNPC: null, isGodMode: false });
    } catch (err) {
      console.error('Deselect failed:', err);
    }
  },

  move: async (direction) => {
    const { selectedNPC } = get();
    if (!selectedNPC) return;
    // 立即设置方向 (客户端预测，不等网络)
    godMoveDirectionRef.current = direction;
    try {
      await godApi.move(direction);
    } catch {
      // 网络失败不影响前端预测，后端校正会处理
    }
  },

  stop: async () => {
    // 立即清除方向 (客户端立刻停止)
    godMoveDirectionRef.current = null;
    try {
      await godApi.stop();
    } catch {
      // 同上
    }
  },

  fetchStatus: async () => {
    try {
      const { data } = await godApi.getStatus();
      set({
        selectedNPC: data.selected_npc,
        isGodMode: data.god_mode,
      });
    } catch (err) {
      console.error('Fetch god status failed:', err);
    }
  },
}));
