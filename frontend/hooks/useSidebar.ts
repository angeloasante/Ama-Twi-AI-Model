'use client';

import { useEffect, useCallback } from 'react';
import { useStore } from '@/store/useStore';

export function useSidebar() {
  const { sidebarOpen, toggleSidebar } = useStore();

  // Close sidebar on mobile when selecting a chat
  const closeMobile = useCallback(() => {
    if (window.innerWidth < 768) {
      useStore.getState().toggleSidebar();
    }
  }, []);

  // Handle keyboard shortcut (Ctrl+B)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggleSidebar]);

  return { sidebarOpen, toggleSidebar, closeMobile };
}
