import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function generateId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback UUID v4 generator
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function formatTime(date: Date | string | number) {
  const d = typeof date === 'number' ? new Date(date) : typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function formatDate(date: Date | string | number) {
  const d = typeof date === 'number' ? new Date(date) : typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return d.toLocaleDateString();
}

export const TOOL_LABELS: Record<string, { label: string; icon: string }> = {
  web_search: { label: 'Web Search', icon: '🔍' },
  web_fetch: { label: 'Web Fetch', icon: '🌐' },
  image_search: { label: 'Image Search', icon: '🖼️' },
  get_current_time: { label: 'Time', icon: '🕐' },
  create_file: { label: 'Create File', icon: '📄' },
  view_file: { label: 'View File', icon: '👁️' },
  list_files: { label: 'List Files', icon: '📂' },
  search_knowledge_base: { label: 'Knowledge Base', icon: '📚' },
};

export const SUGGESTED_PROMPTS = [
  { label: 'Teach me Twi', text: 'Teach me basic Twi greetings' },
  { label: 'Translate for me', text: 'How do you say "I love you" in Twi?' },
  { label: 'Ghana culture', text: 'Tell me about Ghanaian naming traditions' },
  { label: 'Twi proverb', text: 'Share a Twi proverb and explain it' },
  { label: 'Current events', text: 'What is happening in Ghana today?' },
  { label: 'Akan history', text: 'Tell me about the Ashanti Empire' },
];

export const TIMEZONES = [
  { value: 'Africa/Accra', label: '🇬🇭 Accra (GMT)' },
  { value: 'Africa/Lagos', label: '🇳🇬 Lagos (WAT)' },
  { value: 'Africa/Nairobi', label: '🇰🇪 Nairobi (EAT)' },
  { value: 'Africa/Johannesburg', label: '🇿🇦 Johannesburg (SAST)' },
  { value: 'Africa/Cairo', label: '🇪🇬 Cairo (EET)' },
  { value: 'Europe/London', label: '🇬🇧 London (GMT/BST)' },
  { value: 'Europe/Paris', label: '🇫🇷 Paris (CET)' },
  { value: 'Europe/Berlin', label: '🇩🇪 Berlin (CET)' },
  { value: 'America/New_York', label: '🇺🇸 New York (EST)' },
  { value: 'America/Chicago', label: '🇺🇸 Chicago (CST)' },
  { value: 'America/Denver', label: '🇺🇸 Denver (MST)' },
  { value: 'America/Los_Angeles', label: '🇺🇸 Los Angeles (PST)' },
  { value: 'America/Toronto', label: '🇨🇦 Toronto (EST)' },
  { value: 'Asia/Dubai', label: '🇦🇪 Dubai (GST)' },
  { value: 'Asia/Shanghai', label: '🇨🇳 Shanghai (CST)' },
  { value: 'Asia/Tokyo', label: '🇯🇵 Tokyo (JST)' },
  { value: 'Australia/Sydney', label: '🇦🇺 Sydney (AEST)' },
  { value: 'Pacific/Auckland', label: '🇳🇿 Auckland (NZST)' },
];
