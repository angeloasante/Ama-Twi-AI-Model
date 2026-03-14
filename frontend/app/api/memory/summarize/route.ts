import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Server-side only — uses service key to bypass RLS
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY!;
const CLAUDE_MODEL = 'claude-sonnet-4-20250514';
const STALE_MINUTES = 5; // don't re-summarize if < 5 min old
const MIN_MESSAGES_FOR_SUMMARY = 4; // need at least 4 messages of history

/**
 * POST /api/memory/summarize
 * Body: { userId: string }
 *
 * Fetches all user conversations from Supabase, sends to Claude
 * for profile summarization, stores result in user_memory.profile_summary.
 */
export async function POST(req: NextRequest) {
  try {
    const { userId } = await req.json();
    if (!userId) {
      return NextResponse.json({ error: 'userId required' }, { status: 400 });
    }

    if (!ANTHROPIC_API_KEY || ANTHROPIC_API_KEY === 'your-anthropic-api-key-here') {
      return NextResponse.json({ error: 'Anthropic API key not configured' }, { status: 500 });
    }

    // ─── 1. Check if summary is stale ──────────────────────
    const { data: existingMemory } = await supabase
      .from('user_memory')
      .select('profile_summary, last_summarized_at, messages_at_last_summary')
      .eq('user_id', userId)
      .single();

    // We skip ONLY if: summary exists AND is fresh AND no new messages
    // This ensures new messages always trigger a re-summary once staleness passes
    const isFresh = existingMemory?.last_summarized_at
      ? (Date.now() - new Date(existingMemory.last_summarized_at).getTime()) / 60000 < STALE_MINUTES
      : false;

    // ─── 2. Get user's name from auth ───────────────────────
    let userName = 'the user';
    try {
      const { data: authUser } = await supabase.auth.admin.getUserById(userId);
      if (authUser?.user) {
        const meta = authUser.user.user_metadata;
        userName = meta?.full_name || meta?.name || meta?.display_name
          || authUser.user.email?.split('@')[0] || 'the user';
      }
    } catch (e) {
      console.error('Could not fetch user name:', e);
    }

    // ─── 3. Fetch all conversations + messages ─────────────
    // Use REST API directly instead of RPC to avoid needing a migration
    const { data: conversations, error: convError } = await supabase
      .from('conversations')
      .select('id, title, created_at')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(50);

    if (convError) {
      console.error('Error fetching conversations:', convError);
      return NextResponse.json({ error: 'Failed to fetch conversations' }, { status: 500 });
    }

    if (!conversations || conversations.length === 0) {
      return NextResponse.json({ profile: null, skipped: true, reason: 'No conversations yet' });
    }

    // Fetch messages for each conversation
    const convoIds = conversations.map((c: any) => c.id);
    const { data: allMessages, error: msgError } = await supabase
      .from('messages')
      .select('conversation_id, role, content, created_at')
      .in('conversation_id', convoIds)
      .order('created_at', { ascending: true });

    if (msgError) {
      console.error('Error fetching messages:', msgError);
      return NextResponse.json({ error: 'Failed to fetch messages' }, { status: 500 });
    }

    // Group messages by conversation
    const messagesByConvo = new Map<string, any[]>();
    for (const msg of (allMessages || [])) {
      const existing = messagesByConvo.get(msg.conversation_id) || [];
      existing.push(msg);
      messagesByConvo.set(msg.conversation_id, existing);
    }

    // Count total messages and build conversation texts
    let totalMessages = 0;
    const convoTexts: string[] = [];
    for (const convo of conversations) {
      const msgs = messagesByConvo.get(convo.id);
      if (!msgs || msgs.length === 0) continue;
      totalMessages += msgs.length;
      const msgText = msgs
        .map((m: any) => `${m.role === 'user' ? 'User' : 'Ama'}: ${m.content}`)
        .join('\n');
      convoTexts.push(`--- Conversation: ${convo.title || 'Untitled'} (${convo.created_at}) ---\n${msgText}`);
    }

    if (totalMessages < MIN_MESSAGES_FOR_SUMMARY) {
      return NextResponse.json({
        profile: null,
        skipped: true,
        reason: `Only ${totalMessages} messages, need ${MIN_MESSAGES_FOR_SUMMARY}`,
      });
    }

    // Skip if no new messages since last summary AND summary is still fresh
    if (existingMemory?.messages_at_last_summary >= totalMessages && existingMemory?.profile_summary) {
      return NextResponse.json({
        profile: existingMemory.profile_summary,
        skipped: true,
        reason: 'No new messages since last summary',
      });
    }

    // Skip if summary was generated very recently (rate limit)
    if (isFresh && existingMemory?.profile_summary) {
      return NextResponse.json({
        profile: existingMemory.profile_summary,
        skipped: true,
        reason: `Summarized recently, still fresh`,
      });
    }

    // ─── 4. Truncate to fit Claude context ─────────────────
    // Keep under ~50K chars to stay well within limits
    let allText = convoTexts.join('\n\n');
    if (allText.length > 50000) {
      allText = allText.slice(-50000); // keep most recent
    }

    // ─── 5. Call Claude for summarization + fact extraction ─
    const claudePrompt = `You are analyzing all conversations a user named "${userName}" has had with "Ama", a bilingual Twi-English AI assistant.

You must return a JSON object with two fields:
1. "profile" — A concise third-person profile summary (max 200 words)
2. "facts" — A JSON array of short, specific facts about the user

For the PROFILE, extract and summarize:
- Their name: ${userName}
- Where they're from / where they live
- Their interests, hobbies, profession
- Their relationship to Ghana/Twi (e.g., diaspora, learning for a partner, heritage speaker)
- Why they're learning Twi (if applicable)
- Important people they've mentioned (partner, family, etc.)
- Their personality traits or communication style
- Any preferences they've expressed (language preference, topics they enjoy)
- Key life details (age, education, etc. if mentioned)

For the FACTS array, extract specific atomic facts like:
["${userName}'s name is ${userName}", "${userName} has a Ghanaian girlfriend", "${userName} is British", "${userName} is learning Twi for his partner"]

Rules:
- Profile must be in THIRD PERSON using their name ("${userName} is...", "${userName} mentioned...", "He/She...")
- Be concise — profile max 200 words
- Only include things the user actually said or clearly implied
- If very little personal info exists, keep it short — don't pad
- Do NOT include anything about Ama's capabilities or the conversations themselves
- Focus on FACTS about the user, not conversation topics
- Return ONLY valid JSON, no markdown, no code fences

Here are all their conversations:

${allText}

Return JSON:
{"profile": "...", "facts": ["...", "..."]}`;

    const claudeRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: CLAUDE_MODEL,
        max_tokens: 512,
        messages: [{ role: 'user', content: claudePrompt }],
      }),
    });

    if (!claudeRes.ok) {
      const errText = await claudeRes.text();
      console.error('Claude API error:', claudeRes.status, errText);
      return NextResponse.json({ error: 'Claude summarization failed' }, { status: 500 });
    }

    const claudeData = await claudeRes.json();
    const rawText = claudeData.content?.[0]?.text?.trim();

    if (!rawText) {
      return NextResponse.json({ error: 'Claude returned empty response' }, { status: 500 });
    }

    // Parse Claude's JSON response
    let profileSummary = '';
    let extractedFacts: string[] = [];
    try {
      // Strip markdown code fences if Claude added them
      const cleaned = rawText.replace(/^```json\s*/i, '').replace(/```\s*$/i, '').trim();
      const parsed = JSON.parse(cleaned);
      profileSummary = parsed.profile || '';
      extractedFacts = Array.isArray(parsed.facts) ? parsed.facts : [];
    } catch {
      // If JSON parse fails, treat the whole response as the profile
      console.error('Failed to parse Claude JSON, using raw text as profile');
      profileSummary = rawText;
    }

    if (!profileSummary) {
      return NextResponse.json({ error: 'Claude returned empty summary' }, { status: 500 });
    }

    // ─── 6. Upsert into user_memory (profile + facts) ──────
    const { error: upsertError } = await supabase
      .from('user_memory')
      .upsert(
        {
          user_id: userId,
          profile_summary: profileSummary,
          facts: extractedFacts,
          last_summarized_at: new Date().toISOString(),
          messages_at_last_summary: totalMessages,
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'user_id' }
      );

    if (upsertError) {
      console.error('Error saving profile:', upsertError);
      return NextResponse.json({ error: 'Failed to save profile' }, { status: 500 });
    }

    return NextResponse.json({
      profile: profileSummary,
      facts: extractedFacts,
      skipped: false,
      totalMessages,
    });
  } catch (err: any) {
    console.error('Profile summarization error:', err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

/**
 * GET /api/memory/summarize?userId=xxx
 * Returns the current profile summary without regenerating.
 */
export async function GET(req: NextRequest) {
  const userId = req.nextUrl.searchParams.get('userId');
  if (!userId) {
    return NextResponse.json({ error: 'userId required' }, { status: 400 });
  }

  const { data, error } = await supabase
    .from('user_memory')
    .select('profile_summary, last_summarized_at, messages_at_last_summary')
    .eq('user_id', userId)
    .single();

  if (error && error.code !== 'PGRST116') {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({
    profile: data?.profile_summary || null,
    lastSummarizedAt: data?.last_summarized_at || null,
    messagesAtLastSummary: data?.messages_at_last_summary || 0,
  });
}

/**
 * PATCH /api/memory/summarize
 * Body: { userId: string, profile: string }
 * Lets the user manually edit their profile summary.
 */
export async function PATCH(req: NextRequest) {
  try {
    const { userId, profile } = await req.json();
    if (!userId || typeof profile !== 'string') {
      return NextResponse.json({ error: 'userId and profile required' }, { status: 400 });
    }

    const { error } = await supabase
      .from('user_memory')
      .upsert(
        {
          user_id: userId,
          profile_summary: profile.trim(),
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'user_id' }
      );

    if (error) {
      console.error('Error updating profile:', error);
      return NextResponse.json({ error: 'Failed to save profile' }, { status: 500 });
    }

    return NextResponse.json({ success: true, profile: profile.trim() });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
