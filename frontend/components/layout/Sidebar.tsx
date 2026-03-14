'use client';

import { useState } from 'react';
import {
  Plus,
  Search,
  Trash2,
  Settings,
  MessageSquare,
  MoreHorizontal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuAction,
  SidebarSeparator,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  useSidebar,
} from '@/components/ui/sidebar';
import { useStore } from '@/store/useStore';
import { useAuth } from '@/hooks/useAuth';
import { deleteConversation } from '@/lib/conversations';

interface AppSidebarProps {
  onOpenSettings: () => void;
}

export default function AppSidebar({ onOpenSettings }: AppSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const { chats, activeChatId, createNewChat, setActiveChat, deleteChat } = useStore();
  const { user } = useAuth();
  const { state } = useSidebar();
  const isCollapsed = state === 'collapsed';

  const fullName = user?.user_metadata?.full_name || user?.email || 'User';
  const initials = fullName
    .split(/\s+/)
    .map((w: string) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const filteredChats = searchQuery
    ? chats.filter(c => c.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : chats;

  return (
    <ShadcnSidebar collapsible="icon">
      {/* Header — brand */}
      <SidebarHeader className="p-3 pb-1">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <span className="text-lg font-bold text-foreground tracking-tight">Ama</span>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent>
        {/* Top actions */}
        <SidebarGroup className="pt-1">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton onClick={() => createNewChat()} tooltip="New chat">
                <Plus size={16} />
                <span>New chat</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={() => setSearchOpen(!searchOpen)}
                tooltip="Search"
              >
                <Search size={16} />
                <span>Search</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>

        {/* Search input (only when open & expanded) */}
        {searchOpen && !isCollapsed && (
          <div className="px-3 pb-2">
            <Input
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 text-sm"
              autoFocus
            />
          </div>
        )}

        <SidebarSeparator />

        {/* Recents */}
        <SidebarGroup>
          <SidebarGroupLabel>Recents</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {filteredChats.length === 0 ? (
                !isCollapsed && (
                  <p className="text-center text-xs text-muted-foreground py-6 px-3">
                    {searchQuery ? 'No chats found' : 'No conversations yet'}
                  </p>
                )
              ) : (
                filteredChats.map(chat => (
                  <SidebarMenuItem key={chat.id}>
                    <SidebarMenuButton
                      isActive={chat.id === activeChatId}
                      onClick={() => setActiveChat(chat.id)}
                      tooltip={chat.title}
                    >
                      <MessageSquare size={14} />
                      <span className="truncate">{chat.title}</span>
                    </SidebarMenuButton>
                    <SidebarMenuAction
                      onClick={() => {
                        if (chat.dbId) deleteConversation(chat.dbId);
                        deleteChat(chat.id);
                      }}
                      className="hover:bg-destructive/10 hover:text-destructive"
                    >
                      <MoreHorizontal size={14} />
                    </SidebarMenuAction>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* Footer — user + settings */}
      <SidebarFooter className="p-2">
        <SidebarSeparator className="mb-2" />
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={onOpenSettings} tooltip="Settings">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-[10px] font-bold shrink-0">
                {initials}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-sm font-medium truncate">{fullName}</span>
              </div>
            </SidebarMenuButton>
            <SidebarMenuAction onClick={onOpenSettings}>
              <Settings size={14} />
            </SidebarMenuAction>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </ShadcnSidebar>
  );
}
