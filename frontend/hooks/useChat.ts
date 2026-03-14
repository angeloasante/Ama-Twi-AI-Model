'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useStore, type Message } from '@/store/useStore';
import { generateId } from '@/lib/utils';
import { generateTitle } from '@/lib/generateTitle';
import { useAuth } from '@/hooks/useAuth';
import {
  createConversation,
  saveMessage,
  updateConversationTitle,
  deleteMessage as deleteDbMessage,
} from '@/lib/conversations';
import {
  buildAmaContext,
  storeEmbedding,
  refreshUserProfile,
} from '@/lib/memory';

const CHAT_API = '/api/chat';

export function useChat() {
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const { user } = useAuth();
  const { 
    chats, activeChatId, addMessage, createNewChat, updateChatTitle,
    timezone, preferredLanguage 
  } = useStore();

  const activeChat = chats.find(c => c.id === activeChatId) || null;
  const messages = activeChat?.messages || [];

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    let chatId = activeChatId;

    if (!chatId) {
      // Create in Zustand first for instant UI
      createNewChat();
      chatId = useStore.getState().activeChatId;
    }
    if (!chatId) return;

    // Ensure Supabase conversation exists for this chat
    let dbConversationId: string | null = null;
    const existingChat = useStore.getState().chats.find(c => c.id === chatId);
    dbConversationId = existingChat?.dbId || null;

    // If no dbId yet and user is logged in, create in Supabase now
    if (!dbConversationId && user) {
      const dbConvo = await createConversation(user.id);
      if (dbConvo) {
        dbConversationId = dbConvo.id;
        // Store the Supabase ID mapping in the chat
        useStore.setState(state => ({
          chats: state.chats.map(c =>
            c.id === chatId ? { ...c, dbId: dbConvo.id } : c
          ),
        }));
      }
    }

    const userMessage: Omit<Message, 'timestamp'> = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      language: preferredLanguage,
    };
    addMessage(chatId, userMessage);

    // Persist user message to Supabase
    if (dbConversationId) {
      saveMessage(dbConversationId, userMessage);
    }

    // Generate title after first user message
    const currentChat = useStore.getState().chats.find(c => c.id === chatId);
    const isFirstMessage = currentChat && currentChat.messages.length === 1;
    if (isFirstMessage && dbConversationId) {
      // Immediately set a truncated title in Supabase (so it's never "New Chat")
      const fallbackTitle = content.trim().slice(0, 40) + (content.trim().length > 40 ? '...' : '');
      updateConversationTitle(dbConversationId, fallbackTitle);

      // Then upgrade to AI-generated title
      const capturedDbId = dbConversationId;
      generateTitle(content.trim())
        .then(title => {
          if (title) {
            updateChatTitle(chatId!, title);
            updateConversationTitle(capturedDbId, title);
          }
        })
        .catch(() => {
          // Fallback already set above, just update Zustand
          updateChatTitle(chatId!, fallbackTitle);
        });
    }

    setIsLoading(true);
    abortRef.current = new AbortController();

    try {
      // ─── Memory: Build enhanced context ───────────────────
      let enhancedInput = content.trim();
      if (user && dbConversationId) {
        const currentMessages = useStore.getState().chats
          .find(c => c.id === chatId)?.messages
          .map(m => ({ role: m.role, content: m.content })) || [];

        const context = await buildAmaContext(
          user.id,
          content.trim(),
          dbConversationId,
          currentMessages
        );

        if (context) {
          enhancedInput = `${context}Current message: ${content.trim()}`;
        }
      }

      // Build recent conversation history for context window
      const recentMessages = useStore.getState().chats
        .find(c => c.id === chatId)?.messages
        .slice(-10) // last 10 messages for context
        .map(m => ({ role: m.role, content: m.content })) || [];

      const res = await fetch(CHAT_API, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          inputs: enhancedInput,
          parameters: { timezone },
          history: recentMessages,
        }),
        signal: abortRef.current.signal,
      });

      const data = await res.json();

      const assistantMessage: Omit<Message, 'timestamp'> = {
        id: generateId(),
        role: 'assistant',
        content: data.response || data.generated_text || 'Sorry, I could not generate a response.',
        tools_used: data.tools_used || [],
        tool_results: data.tool_results || {},
        language: preferredLanguage,
      };

      addMessage(chatId, assistantMessage);

      // Persist assistant message to Supabase
      if (dbConversationId) {
        saveMessage(dbConversationId, assistantMessage);
      }

      // ─── Memory: Store embeddings + maybe refresh profile ───
      if (user && dbConversationId) {
        storeEmbedding(user.id, dbConversationId, userMessage.id, 'user', content.trim());
        storeEmbedding(user.id, dbConversationId, assistantMessage.id, 'assistant', assistantMessage.content);

        // Refresh user profile every 5 messages
        // Use actual conversation message count so it persists across reloads
        const currentMessages = useStore.getState().chats.find(c => c.id === chatId)?.messages || [];
        const msgCount = currentMessages.length;
        if (msgCount % 5 === 0 || msgCount <= 2) {
          // Fire & forget — won't block the UI
          refreshUserProfile(user.id);
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        const errorMessage: Omit<Message, 'timestamp'> = {
          id: generateId(),
          role: 'assistant',
          content: 'Kafra — an error occurred. Please try again. (Sorry — an error occurred.)',
        };
        addMessage(chatId, errorMessage);
      }
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  }, [activeChatId, isLoading, addMessage, createNewChat, updateChatTitle, timezone, preferredLanguage, user]);

  const regenerate = useCallback(async () => {
    if (!activeChat || activeChat.messages.length < 2) return;
    const lastUserMsg = [...activeChat.messages].reverse().find(m => m.role === 'user');
    if (lastUserMsg) {
      // Delete the last assistant message
      const lastAssistantIdx = activeChat.messages.length - 1;
      const lastAssistant = activeChat.messages[lastAssistantIdx];
      if (lastAssistant?.role === 'assistant') {
        useStore.getState().deleteMessage(activeChat.id, lastAssistant.id);
        // Also delete from Supabase
        const dbId = (activeChat as any)?.dbId;
        if (dbId) deleteDbMessage(lastAssistant.id);
      }
      await sendMessage(lastUserMsg.content);
    }
  }, [activeChat, sendMessage]);

  const stopGeneration = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      setIsLoading(false);
    }
  }, []);

  // ─── Memory: Refresh user profile on app load ───
  const profileRefreshedRef = useRef(false);
  useEffect(() => {
    if (user && !profileRefreshedRef.current) {
      profileRefreshedRef.current = true;
      // Refresh profile on app start (Claude will skip if still fresh)
      refreshUserProfile(user.id);
    }
  }, [user]);

  return { messages, isLoading, sendMessage, regenerate, stopGeneration, activeChat };
}
