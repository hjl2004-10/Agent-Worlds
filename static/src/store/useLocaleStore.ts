import { create } from 'zustand';

export type Locale = 'zh' | 'en';

interface LocaleStore {
  locale: Locale;
  setLocale: (l: Locale) => void;
  toggle: () => void;
  init: () => void;
}

export const useLocaleStore = create<LocaleStore>((set, get) => ({
  locale: 'zh',

  setLocale: (locale: Locale) => {
    localStorage.setItem('kuafu-locale', locale);
    set({ locale });
  },

  toggle: () => {
    const next = get().locale === 'zh' ? 'en' : 'zh';
    localStorage.setItem('kuafu-locale', next);
    set({ locale: next as Locale });
  },

  init: () => {
    const saved = localStorage.getItem('kuafu-locale') as Locale | null;
    if (saved && (saved === 'zh' || saved === 'en')) {
      set({ locale: saved });
    }
  },
}));
