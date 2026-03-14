'use client';

import { useState } from 'react';
import { X, Moon, Sun, Trash2, Globe, Languages, LogOut, Brain, Sparkles, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { useStore } from '@/store/useStore';
import { useAuth } from '@/hooks/useAuth';
import { clearAllConversations } from '@/lib/conversations';
import { clearUserMemory } from '@/lib/memory';
import { TIMEZONES } from '@/lib/utils';
import { cn } from '@/lib/utils';
import ProfileView from './ProfileSheet';

interface SettingsPanelProps {
  open: boolean;
  onClose: () => void;
}

export default function SettingsPanel({ open, onClose }: SettingsPanelProps) {
  const {
    theme, toggleTheme,
    timezone, setTimezone,
    preferredLanguage, toggleLanguage,
    clearHistory,
  } = useStore();
  const { user, signOut } = useAuth();

  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showClearMemory, setShowClearMemory] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const displayName = user?.user_metadata?.full_name || user?.email || 'User';

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} />
      )}

      {/* Panel */}
      <div
        className={cn(
          'fixed top-0 right-0 z-50 h-full w-80 bg-background border-l border-border shadow-xl transition-transform duration-300 ease-in-out',
          open ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Profile sub-view fills the entire panel */}
        {profileOpen && user ? (
          <ProfileView
            userId={user.id}
            onBack={() => setProfileOpen(false)}
          />
        ) : (
          <>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold">Settings</h2>
          <Button variant="ghost" size="icon-sm" onClick={onClose}>
            <X size={18} />
          </Button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-57px)] p-4 space-y-6">
          {/* Account */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Account</h3>
            <p className="text-sm text-muted-foreground mb-3 truncate">{displayName}</p>
            <Button
              variant="outline"
              className="w-full justify-start gap-2"
              onClick={signOut}
            >
              <LogOut size={16} />
              Sign out
            </Button>
          </div>

          <Separator />
          {/* Appearance */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Appearance</h3>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                {theme === 'dark' ? <Moon size={16} /> : <Sun size={16} />}
                Dark Mode
              </div>
              <button
                onClick={toggleTheme}
                className={cn(
                  'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200',
                  theme === 'dark' ? 'bg-primary' : 'bg-border'
                )}
              >
                <span
                  className={cn(
                    'pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 mt-0.5',
                    theme === 'dark' ? 'translate-x-5.5' : 'translate-x-0.5'
                  )}
                />
              </button>
            </div>
          </div>

          <Separator />

          {/* Language */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Language</h3>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Languages size={16} />
              Preferred Language
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              Ama responds in both languages, but will prioritize your preference.
            </p>
            <div className="flex rounded-lg border border-border overflow-hidden">
              <button
                onClick={preferredLanguage === 'tw' ? toggleLanguage : undefined}
                className={cn(
                  'flex-1 py-2 text-sm font-medium transition-colors',
                  preferredLanguage === 'en'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-transparent hover:bg-accent'
                )}
              >
                English
              </button>
              <button
                onClick={preferredLanguage === 'en' ? toggleLanguage : undefined}
                className={cn(
                  'flex-1 py-2 text-sm font-medium transition-colors',
                  preferredLanguage === 'tw'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-transparent hover:bg-accent'
                )}
              >
                Twi
              </button>
            </div>
          </div>

          <Separator />

          {/* Timezone */}
          <div>
            <h3 className="text-sm font-semibold mb-3">Timezone</h3>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Globe size={16} />
              Your timezone
            </div>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring appearance-none cursor-pointer"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz.value} value={tz.value}>
                  {tz.label}
                </option>
              ))}
            </select>
          </div>

          <Separator />

          {/* Your Profile */}
          {user && (
            <>
              <div>
                <h3 className="text-sm font-semibold mb-3">Your Profile</h3>
                <button
                  onClick={() => setProfileOpen(true)}
                  className="w-full group flex items-center gap-3 p-3 rounded-xl border border-border bg-card hover:bg-accent/50 transition-all text-left"
                >
                  <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 text-primary shrink-0">
                    <Sparkles size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">What Ama Knows</p>
                    <p className="text-xs text-muted-foreground truncate">
                      Tap to view & edit your profile
                    </p>
                  </div>
                  <ChevronRight size={16} className="text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
                </button>
              </div>
              <Separator />
            </>
          )}

          {/* Danger Zone */}
          <div>
            <h3 className="text-sm font-semibold text-destructive mb-3">Danger Zone</h3>

            {/* Clear Memory */}
            {showClearMemory ? (
              <div className="space-y-2 mb-3">
                <p className="text-xs text-muted-foreground">
                  This will erase everything Ama knows about you.
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => setShowClearMemory(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                      if (user) clearUserMemory(user.id);
                      setShowClearMemory(false);
                    }}
                  >
                    Erase Memory
                  </Button>
                </div>
              </div>
            ) : (
              <Button
                variant="outline"
                className="w-full mb-3 text-destructive border-destructive/30 hover:bg-destructive/10"
                onClick={() => setShowClearMemory(true)}
              >
                <Brain size={16} />
                Clear Ama&apos;s Memory of You
              </Button>
            )}

            {/* Clear Chat History */}
            {showClearConfirm ? (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">
                  This will permanently delete all your conversations.
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => setShowClearConfirm(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                      clearHistory();
                      if (user) clearAllConversations(user.id);
                      setShowClearConfirm(false);
                    }}
                  >
                    Delete All
                  </Button>
                </div>
              </div>
            ) : (
              <Button
                variant="destructive"
                className="w-full"
                onClick={() => setShowClearConfirm(true)}
              >
                <Trash2 size={16} />
                Clear All Chat History
              </Button>
            )}
          </div>
        </div>
          </>
        )}
      </div>
    </>
  );
}
