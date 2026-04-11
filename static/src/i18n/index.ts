import { useLocaleStore } from '@/store/useLocaleStore';
import { zh } from './zh';
import { en } from './en';

const dictMap = { zh, en } as const;

export function useT() {
  const locale = useLocaleStore((s) => s.locale);
  const dict = dictMap[locale];
  return (key: string) => dict[key] ?? key;
}
