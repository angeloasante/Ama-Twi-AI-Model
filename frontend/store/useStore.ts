import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  tools_used?: string[];
  tool_results?: any;
  language?: 'en' | 'tw';
  reaction?: 'up' | 'down' | null;
}

export interface Chat {
  id: string;
  dbId?: string; // Supabase conversation UUID
  title: string;
  messages: Message[];
  updatedAt: number;
}

interface AppState {
  // UI State
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  onboardingSeen: boolean;
  completeOnboarding: () => void;
  
  // Settings
  timezone: string;
  setTimezone: (tz: string) => void;
  preferredLanguage: 'en' | 'tw';
  toggleLanguage: () => void;
  
  // Chat History
  chats: Chat[];
  activeChatId: string | null;
  createNewChat: () => void;
  setActiveChat: (id: string) => void;
  deleteChat: (id: string) => void;
  clearHistory: () => void;
  
  // Active Chat Actions
  addMessage: (chatId: string, message: Omit<Message, 'timestamp'>) => void;
  updateMessageReaction: (chatId: string, messageId: string, reaction: 'up' | 'down' | null) => void;
  deleteMessage: (chatId: string, messageId: string) => void;
  updateChatTitle: (chatId: string, title: string) => void;
  loadChats: (chats: Chat[]) => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      sidebarOpen: true,
      toggleSidebar: () => set({ sidebarOpen: !get().sidebarOpen }),
      
      theme: 'dark',
      toggleTheme: () => set({ theme: get().theme === 'dark' ? 'light' : 'dark' }),
      
      onboardingSeen: false,
      completeOnboarding: () => set({ onboardingSeen: true }),
      
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'Africa/Accra',
      setTimezone: (tz) => set({ timezone: tz }),
      
      preferredLanguage: 'en',
      toggleLanguage: () => set({ preferredLanguage: get().preferredLanguage === 'en' ? 'tw' : 'en' }),
      
      chats: [],
      activeChatId: null,
      
      createNewChat: () => {
        const newChat: Chat = {
          id: Date.now().toString(),
          title: 'New Chat',
          messages: [],
          updatedAt: Date.now(),
        };
        set({ 
          chats: [newChat, ...get().chats],
          activeChatId: newChat.id,
        });
      },
      
      setActiveChat: (id) => set({ activeChatId: id }),
      
      deleteChat: (id) => {
        const { chats, activeChatId } = get();
        const newChats = chats.filter(c => c.id !== id);
        set({ 
          chats: newChats,
          activeChatId: activeChatId === id ? (newChats[0]?.id || null) : activeChatId
        });
      },
      
      clearHistory: () => set({ chats: [], activeChatId: null }),
      
      addMessage: (chatId, message) => {
        const { chats } = get();
        const chatIndex = chats.findIndex(c => c.id === chatId);
        
        if (chatIndex === -1) return;
        
        const updatedChat = { ...chats[chatIndex] };
        updatedChat.messages = [...updatedChat.messages, { ...message, timestamp: Date.now() }];
        updatedChat.updatedAt = Date.now();
        
        // Set a temporary title from first user message (will be replaced by AI title)
        if (updatedChat.title === 'New Chat' && message.role === 'user') {
          updatedChat.title = message.content.slice(0, 40) + (message.content.length > 40 ? '...' : '');
        }
        
        const newChats = [...chats];
        newChats[chatIndex] = updatedChat;
        newChats.sort((a, b) => b.updatedAt - a.updatedAt);
        
        set({ chats: newChats });
      },
      
      updateMessageReaction: (chatId, messageId, reaction) => {
        const { chats } = get();
        const newChats = chats.map(c => {
          if (c.id !== chatId) return c;
          return {
            ...c,
            messages: c.messages.map(m => m.id === messageId ? { ...m, reaction } : m)
          };
        });
        set({ chats: newChats });
      },
      
      deleteMessage: (chatId, messageId) => {
        const { chats } = get();
        const newChats = chats.map(c => {
          if (c.id !== chatId) return c;
          return {
            ...c,
            messages: c.messages.filter(m => m.id !== messageId)
          };
        });
        set({ chats: newChats });
      },

      updateChatTitle: (chatId, title) => {
        const { chats } = get();
        const newChats = chats.map(c =>
          c.id === chatId ? { ...c, title } : c
        );
        set({ chats: newChats });
      },

      loadChats: (chats) => {
        set({ chats });
      },
    }),
    {
      name: 'twi-ai-storage',
    }
  )
);
