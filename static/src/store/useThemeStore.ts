import { create } from 'zustand';

type Theme = 'dark' | 'light';

interface ThemeStore {
  theme: Theme;
  toggle: () => void;
  init: () => void;
}

export const useThemeStore = create<ThemeStore>((set, get) => ({
  theme: 'dark',

  toggle: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('kuafu-theme', next);
    document.documentElement.setAttribute('data-theme', next);
    set({ theme: next });
  },

  init: () => {
    const saved = localStorage.getItem('kuafu-theme') as Theme | null;
    const theme = saved || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    set({ theme });
  },
}));
