'use client';

import { useState, useEffect, useCallback } from 'react';
import { User, RefreshCw, Save, ArrowLeft, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ProfileViewProps {
  userId: string;
  onBack: () => void;
}

export default function ProfileView({ userId, onBack }: ProfileViewProps) {
  const [profile, setProfile] = useState('');
  const [editedProfile, setEditedProfile] = useState('');
  const [lastSummarized, setLastSummarized] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Load profile on mount
  const loadProfile = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/memory/summarize?userId=${userId}`);
      if (res.ok) {
        const data = await res.json();
        const p = data.profile || '';
        setProfile(p);
        setEditedProfile(p);
        setLastSummarized(data.lastSummarizedAt);
        setHasChanges(false);
      }
    } catch (err) {
      console.error('Failed to load profile:', err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/memory/summarize', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, profile: editedProfile }),
      });
      if (res.ok) {
        setProfile(editedProfile);
        setHasChanges(false);
      }
    } catch (err) {
      console.error('Failed to save profile:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await fetch('/api/memory/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.profile) {
          setProfile(data.profile);
          setEditedProfile(data.profile);
          setHasChanges(false);
          setLastSummarized(new Date().toISOString());
        }
      }
    } catch (err) {
      console.error('Failed to refresh profile:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleTextChange = (value: string) => {
    setEditedProfile(value);
    setHasChanges(value !== profile);
  };

  const timeAgo = lastSummarized
    ? formatTimeAgo(new Date(lastSummarized))
    : null;

  return (
    <div className="flex flex-col h-full">
      {/* Header — matches settings header */}
      <div className="flex items-center gap-2 p-4 border-b border-border">
        <Button variant="ghost" size="icon-sm" onClick={onBack}>
          <ArrowLeft size={18} />
        </Button>
        <h2 className="text-lg font-semibold">Your Profile</h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Description */}
        <div className="flex items-start gap-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 text-primary shrink-0 mt-0.5">
            <Sparkles size={18} />
          </div>
          <div>
            <p className="text-sm font-medium">What Ama Knows About You</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              This is the profile Ama uses to personalize your conversations.
            </p>
            {timeAgo && (
              <p className="text-xs text-muted-foreground/70 mt-1">
                Last updated {timeAgo}
              </p>
            )}
          </div>
        </div>

        {/* Profile content */}
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <div className="flex gap-1.5">
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:0ms]" />
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:150ms]" />
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        ) : profile || editedProfile ? (
          <textarea
            value={editedProfile}
            onChange={(e) => handleTextChange(e.target.value)}
            className="w-full min-h-[260px] rounded-xl border border-border bg-card p-4 text-sm leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-ring/30 transition-all"
            placeholder="No profile yet — keep chatting with Ama and she'll learn about you!"
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-40 text-muted-foreground text-center gap-3">
            <User size={32} className="opacity-40" />
            <p className="text-sm">
              No profile yet. Keep chatting with Ama and she&apos;ll build a profile about you!
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
              className="gap-2"
            >
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
              Generate Now
            </Button>
          </div>
        )}
      </div>

      {/* Footer buttons */}
      {(profile || editedProfile) && (
        <div className="flex gap-2 p-4 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing || saving}
            className="gap-2 flex-1"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            {refreshing ? 'Refreshing...' : 'Regenerate'}
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || saving}
            className="gap-2 flex-1"
          >
            <Save size={14} />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      )}
    </div>
  );
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}
