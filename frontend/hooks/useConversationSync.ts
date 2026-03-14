'use client';

import { useEffect, useRef } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useStore, type Chat } from '@/store/useStore';
import { getConversations, getMessages } from '@/lib/conversations';

/**
 * Loads conversations from Supabase on mount (when user is authenticated)
 * and syncs them into the Zustand store.
 */
export function useConversationSync() {
  const { user, loading: authLoading } = useAuth();
  const { loadChats } = useStore();
  const hasSynced = useRef(false);

  useEffect(() => {
    if (authLoading || !user || hasSynced.current) return;

    async function sync() {
      const dbConversations = await getConversations(user!.id);

      if (dbConversations.length === 0) return;

      // Load all conversations with their messages in parallel
      const chats: Chat[] = await Promise.all(
        dbConversations.map(async (convo) => {
          const messages = await getMessages(convo.id);
          return {
            id: convo.id, // Use the Supabase ID as the local ID too
            dbId: convo.id,
            title: convo.title,
            messages,
            updatedAt: new Date(convo.updated_at).getTime(),
          };
        })
      );

      // Merge: keep Supabase as source of truth
      loadChats(chats);
      hasSynced.current = true;
    }

    sync();
  }, [user, authLoading, loadChats]);
}
