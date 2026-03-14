import { supabase } from './supabase';
import type { Message } from '@/store/useStore';

// ─── Types ───────────────────────────────────────────────────

export interface DbConversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface DbMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  language: string | null;
  tools_used: string[];
  tool_results: Record<string, any>;
  reaction: 'up' | 'down' | null;
  created_at: string;
}

// ─── Conversations ──────────────────────────────────────────

export async function createConversation(userId: string, title = 'New Chat'): Promise<DbConversation | null> {
  const { data, error } = await supabase
    .from('conversations')
    .insert({ user_id: userId, title })
    .select()
    .single();

  if (error) {
    console.error('Error creating conversation:', error);
    return null;
  }
  return data;
}

export async function getConversations(userId: string): Promise<DbConversation[]> {
  const { data, error } = await supabase
    .from('conversations')
    .select('*')
    .eq('user_id', userId)
    .order('updated_at', { ascending: false });

  if (error) {
    console.error('Error fetching conversations:', error);
    return [];
  }
  return data || [];
}

export async function updateConversationTitle(conversationId: string, title: string) {
  const { error } = await supabase
    .from('conversations')
    .update({ title })
    .eq('id', conversationId);

  if (error) console.error('Error updating title:', error);
}

export async function deleteConversation(conversationId: string) {
  const { error } = await supabase
    .from('conversations')
    .delete()
    .eq('id', conversationId);

  if (error) console.error('Error deleting conversation:', error);
}

export async function clearAllConversations(userId: string) {
  const { error } = await supabase
    .from('conversations')
    .delete()
    .eq('user_id', userId);

  if (error) console.error('Error clearing conversations:', error);
}

// ─── Messages ───────────────────────────────────────────────

export async function saveMessage(
  conversationId: string,
  message: Omit<Message, 'timestamp'>
): Promise<DbMessage | null> {
  const { data, error } = await supabase
    .from('messages')
    .insert({
      id: message.id,
      conversation_id: conversationId,
      role: message.role,
      content: message.content,
      language: message.language || null,
      tools_used: message.tools_used || [],
      tool_results: message.tool_results || {},
      reaction: message.reaction || null,
    })
    .select()
    .single();

  if (error) {
    console.error('Error saving message:', error);
    return null;
  }
  return data;
}

export async function getMessages(conversationId: string): Promise<Message[]> {
  const { data, error } = await supabase
    .from('messages')
    .select('*')
    .eq('conversation_id', conversationId)
    .order('created_at', { ascending: true });

  if (error) {
    console.error('Error fetching messages:', error);
    return [];
  }

  return (data || []).map((m: DbMessage) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: new Date(m.created_at).getTime(),
    language: m.language as 'en' | 'tw' | undefined,
    tools_used: m.tools_used,
    tool_results: m.tool_results,
    reaction: m.reaction,
  }));
}

export async function updateMessageReaction(
  messageId: string,
  reaction: 'up' | 'down' | null
) {
  const { error } = await supabase
    .from('messages')
    .update({ reaction })
    .eq('id', messageId);

  if (error) console.error('Error updating reaction:', error);
}

export async function deleteMessage(messageId: string) {
  const { error } = await supabase
    .from('messages')
    .delete()
    .eq('id', messageId);

  if (error) console.error('Error deleting message:', error);
}
