'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import AppSidebar from '@/components/layout/Sidebar';
import Chat from '@/components/chat/Chat';
import SettingsPanel from '@/components/settings/SettingsPanel';
import Onboarding from '@/components/Onboarding';
import { useTheme } from '@/hooks/useTheme';
import { useAuth } from '@/hooks/useAuth';
import { FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useStore } from '@/store/useStore';
import { useConversationSync } from '@/hooks/useConversationSync';
import { useEffect } from 'react';

export default function Home() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { createNewChat } = useStore();
  const { user, loading } = useAuth();
  const router = useRouter();
  useTheme();
  useConversationSync();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-svh flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-primary" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <SidebarProvider>
      <Onboarding />
      <AppSidebar onOpenSettings={() => setSettingsOpen(true)} />
      <SidebarInset className="flex flex-col h-svh">
        {/* Thin minimal header — fixed, no border */}
        <header className="flex items-center justify-between h-10 px-3 shrink-0 sticky top-0 z-10 bg-background">
          <SidebarTrigger />
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-muted-foreground hover:text-foreground"
            onClick={() => createNewChat()}
          >
            <FileText size={16} />
          </Button>
        </header>
        <Chat />
      </SidebarInset>
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </SidebarProvider>
  );
}
