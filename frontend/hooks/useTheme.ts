'use client';

import { useEffect } from 'react';
import { useStore } from '@/store/useStore';

export function useTheme() {
  const { theme, toggleTheme } = useStore();

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  return { theme, toggleTheme };
}
