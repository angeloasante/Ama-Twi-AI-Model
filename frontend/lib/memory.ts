import { supabase } from './supabase';
import { getEmbedding } from './embeddings';

// ─── Config ──────────────────────────────────────────────────
const SUMMARY_THRESHOLD = 20; // summarize after this many messages
const RECENT_MESSAGE_COUNT = 10; // last N messages sent in full
const RAG_MATCH_THRESHOLD = 0.7;
const RAG_MATCH_COUNT = 5;
const PROFILE_REFRESH_INTERVAL = 5; // refresh profile every N messages

// ─────────────────────────────────────────────────────────────
// 1. RAG — Semantic search over past messages
// ─────────────────────────────────────────────────────────────

/**
 * Store a message embedding in pgvector
 */
export async function storeEmbedding(
  userId: string,
  conversationId: string,
  messageId: string,
  role: 'user' | 'assistant',
  content: string
) {
  try {
    const embedding = await getEmbedding(content);

    const { error } = await supabase.from('message_embeddings').insert({
      user_id: userId,
      conversation_id: conversationId,
      message_id: messageId,
      role,
      content,
      embedding,
    });

    if (error) console.error('Error storing embedding:', error);
  } catch (err) {
    console.error('Failed to store embedding:', err);
  }
}

/**
 * Search past messages by semantic similarity
 */
export async function searchRelevantContext(
  userId: string,
  query: string,
  currentConversationId?: string
): Promise<{ content: string; role: string; similarity: number }[]> {
  try {
    const embedding = await getEmbedding(query);

    const { data, error } = await supabase.rpc('match_messages', {
      query_embedding: embedding,
      match_threshold: RAG_MATCH_THRESHOLD,
      match_count: RAG_MATCH_COUNT,
      p_user_id: userId,
    });

    if (error) {
      console.error('RAG search error:', error);
      return [];
    }

    // Filter out messages from the current conversation (we already have those)
    return (data || [])
      .filter((m: any) => !currentConversationId || m.conversation_id !== currentConversationId)
      .map((m: any) => ({
        content: m.content,
        role: m.role,
        similarity: m.similarity,
      }));
  } catch (err) {
    console.error('RAG search failed:', err);
    return [];
  }
}

// ─────────────────────────────────────────────────────────────
// 2. User Profile — Claude-powered profile summary
// ─────────────────────────────────────────────────────────────

/**
 * Load user's profile summary (natural language, built by Claude)
 */
export async function loadUserProfile(userId: string): Promise<string | null> {
  const { data, error } = await supabase
    .from('user_memory')
    .select('profile_summary, facts')
    .eq('user_id', userId)
    .single();

  if (error && error.code !== 'PGRST116') {
    console.error('Error loading profile:', error);
  }

  // Primary: profile_summary column
  if (data?.profile_summary) {
    return data.profile_summary;
  }

  // Fallback: check for __PROFILE__ entry in facts array
  if (data?.facts && Array.isArray(data.facts)) {
    const profileFact = data.facts.find((f: string) => f.startsWith('__PROFILE__:'));
    if (profileFact) {
      return profileFact.replace('__PROFILE__:', '');
    }
  }

  return null;
}

/**
 * Trigger a profile refresh via the server-side API route.
 * Uses Claude to summarize all user conversations into a profile.
 * Fire-and-forget safe — won't throw.
 */
export async function refreshUserProfile(userId: string): Promise<string | null> {
  try {
    const res = await fetch('/api/memory/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId }),
    });

    if (!res.ok) {
      console.error('Profile refresh failed:', res.status);
      return null;
    }

    const data = await res.json();
    if (data.skipped) {
      console.log('Profile refresh skipped:', data.reason);
      return data.profile;
    }

    console.log('Profile refreshed:', data.profile?.slice(0, 80) + '...');
    return data.profile;
  } catch (err) {
    console.error('Profile refresh error:', err);
    return null;
  }
}

/**
 * Check if we should refresh the profile based on message count.
 * Returns true if enough new messages have been sent since last summary.
 */
export async function shouldRefreshProfile(userId: string): Promise<boolean> {
  try {
    const res = await fetch(`/api/memory/summarize?userId=${userId}`);
    if (!res.ok) return false;

    const data = await res.json();
    
    // No profile yet? Should refresh if there are any messages
    if (!data.profile) return true;

    // Check staleness — if last summary was > 30 min ago
    if (data.lastSummarizedAt) {
      const minutesAgo = (Date.now() - new Date(data.lastSummarizedAt).getTime()) / 60000;
      if (minutesAgo < 5) return false; // too recent, don't spam
    }

    return true;
  } catch {
    return false;
  }
}

/**
 * Load user's stored memory facts (legacy — kept for backward compat)
 */
export async function loadUserMemory(userId: string): Promise<string[]> {
  const { data, error } = await supabase
    .from('user_memory')
    .select('facts')
    .eq('user_id', userId)
    .single();

  if (error && error.code !== 'PGRST116') {
    console.error('Error loading memory:', error);
  }

  // Filter out the __PROFILE__ entry if it exists (used as fallback storage)
  const facts = data?.facts || [];
  return facts.filter((f: string) => !f.startsWith('__PROFILE__:'));
}

/**
 * Delete a user's memory (for settings / GDPR)
 */
export async function clearUserMemory(userId: string) {
  const { error } = await supabase
    .from('user_memory')
    .delete()
    .eq('user_id', userId);

  if (error) console.error('Error clearing memory:', error);
}

// ─────────────────────────────────────────────────────────────
// 3. Conversation Summarization — compress long conversations
// ─────────────────────────────────────────────────────────────

/**
 * Check if a conversation needs summarization and do it.
 * Now uses a simple extractive approach (no model needed for this).
 */
export async function maybeSummarizeConversation(
  conversationId: string,
  messages: { role: string; content: string }[]
): Promise<string | null> {
  if (messages.length < SUMMARY_THRESHOLD) return null;

  try {
    // Simple extractive summary — take key user messages
    const userMessages = messages
      .filter((m) => m.role === 'user')
      .map((m) => m.content)
      .slice(-10); // last 10 user messages

    const summary = `Topics discussed: ${userMessages.join(' | ')}`;

    // Save summary to the conversation record
    const { error } = await supabase
      .from('conversations')
      .update({
        summary,
        message_count: messages.length,
      })
      .eq('id', conversationId);

    if (error) console.error('Error saving summary:', error);

    return summary;
  } catch (err) {
    console.error('Summarization failed:', err);
    return null;
  }
}

/**
 * Load an existing conversation summary
 */
export async function getConversationSummary(
  conversationId: string
): Promise<string | null> {
  const { data, error } = await supabase
    .from('conversations')
    .select('summary')
    .eq('id', conversationId)
    .single();

  if (error) return null;
  return data?.summary || null;
}

// ─────────────────────────────────────────────────────────────
// 4. Build full context for Ama — combines all memory systems
// ─────────────────────────────────────────────────────────────

/**
 * Build the enhanced context string to prepend to Ama's input.
 * Combines:
 * 1. User profile (Claude-generated summary of who this person is)
 * 2. User facts (legacy, if any)
 * 3. Conversation summary (compressed older messages)
 * 4. RAG (relevant past messages from other conversations)
 * 5. Recent messages (last 10 messages in full)
 */
export async function buildAmaContext(
  userId: string,
  currentMessage: string,
  conversationId?: string,
  conversationMessages?: { role: string; content: string }[]
): Promise<string> {
  const parts: string[] = [];

  // Run all memory lookups in parallel
  const [userProfile, userFacts, ragResults, summary] = await Promise.all([
    loadUserProfile(userId),
    loadUserMemory(userId),
    searchRelevantContext(userId, currentMessage, conversationId),
    conversationId ? getConversationSummary(conversationId) : Promise.resolve(null),
  ]);

  // 1. User profile — Claude-generated natural language profile
  if (userProfile) {
    parts.push(`[About This User]\n${userProfile}`);
  }

  // 2. User facts — legacy facts (backward compat)
  if (userFacts.length > 0 && !userProfile) {
    // Only include facts if there's no profile yet (profile supersedes facts)
    parts.push(`[User Facts]\n${userFacts.join('\n')}`);
  }

  // 3. Conversation summary — compressed older context from this session
  if (summary) {
    parts.push(`[Previous Context Summary]\n${summary}`);
  }

  // 4. RAG — semantically relevant messages from other conversations
  if (ragResults.length > 0) {
    const ragText = ragResults
      .map((r) => `${r.role === 'user' ? 'User' : 'Ama'}: ${r.content}`)
      .join('\n');
    parts.push(`[Relevant Past Conversations]\n${ragText}`);
  }

  // 5. Recent messages — last N messages from current conversation in full
  if (conversationMessages && conversationMessages.length > 0) {
    const recent = conversationMessages.slice(-RECENT_MESSAGE_COUNT);
    const recentText = recent
      .map((m) => `${m.role === 'user' ? 'User' : 'Ama'}: ${m.content}`)
      .join('\n');
    parts.push(`[Recent Messages]\n${recentText}`);
  }

  // 6. Maybe summarize current conversation if it's getting long (fire & forget)
  if (conversationId && conversationMessages && conversationMessages.length >= SUMMARY_THRESHOLD && !summary) {
    maybeSummarizeConversation(conversationId, conversationMessages);
  }

  if (parts.length === 0) return '';

  return parts.join('\n\n') + '\n\n';
}
