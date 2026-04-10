/**
 * 世界状态管理 Store
 * 管理 world + scene 双层状态驱动
 */

import { create } from 'zustand';

export interface WorldInfo {
  world_id: string;
  display_name: string;
  genre: string;
  description: string;
  available_scenes: string[];
  default_scene: string;
}

export interface SceneInfo {
  scene_id: string;
  display_name: string;
  description: string;
  map: {
    width: number;
    height: number;
  };
}

interface WorldState {
  // 当前状态
  currentWorld: string;
  currentScene: string;

  // 可用列表
  availableWorlds: WorldInfo[];
  currentWorldInfo: WorldInfo | null;
  currentSceneInfo: SceneInfo | null;

  // 加载状态
  loading: boolean;
  error: string | null;

  // Actions
  fetchCurrentState: () => Promise<void>;
  fetchAvailableWorlds: () => Promise<void>;
  switchWorld: (worldId: string) => Promise<void>;
  switchScene: (sceneId: string) => Promise<void>;
}

export const useWorldStore = create<WorldState>((set) => ({
  currentWorld: 'modern',
  currentScene: 'office',
  availableWorlds: [],
  currentWorldInfo: null,
  currentSceneInfo: null,
  loading: false,
  error: null,

  fetchCurrentState: async () => {
    try {
      const res = await fetch('/api/world/current');
      const data = await res.json();
      if (data.status === 'ok') {
        set({
          currentWorld: data.current_world,
          currentScene: data.current_scene,
          currentWorldInfo: data.world_info || null,
          currentSceneInfo: data.scene_info || null,
        });
      }
    } catch (err) {
      console.error('[WorldStore] 获取当前状态失败:', err);
    }
  },

  fetchAvailableWorlds: async () => {
    try {
      const res = await fetch('/api/worlds');
      const data = await res.json();
      if (data.status === 'ok') {
        set({ availableWorlds: data.worlds || [] });
      }
    } catch (err) {
      console.error('[WorldStore] 获取世界列表失败:', err);
    }
  },

  switchWorld: async (worldId: string) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch('/api/world/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ world_id: worldId }),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        set({
          currentWorld: worldId,
          currentScene: data.current_scene || data.default_scene || 'default',
          currentWorldInfo: data.world_info || null,
          currentSceneInfo: data.scene_info || null,
        });
        // 切换世界后刷新页面数据
        window.location.reload();
      } else {
        set({ error: data.message || '切换失败' });
      }
    } catch (err) {
      set({ error: '切换世界失败' });
      console.error('[WorldStore] 切换世界失败:', err);
    } finally {
      set({ loading: false });
    }
  },

  switchScene: async (sceneId: string) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch('/api/scene/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_id: sceneId }),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        set({
          currentScene: sceneId,
          currentSceneInfo: data.scene_info || null,
        });
        // 切换场景后刷新页面数据
        window.location.reload();
      } else {
        set({ error: data.message || '切换失败' });
      }
    } catch (err) {
      set({ error: '切换场景失败' });
      console.error('[WorldStore] 切换场景失败:', err);
    } finally {
      set({ loading: false });
    }
  },
}));
