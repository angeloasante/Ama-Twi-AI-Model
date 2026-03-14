import { NextRequest, NextResponse } from 'next/server';

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY!;

/**
 * POST /api/title
 * Body: { message: string }
 * Uses Claude to generate a concise 3-5 word conversation title.
 */
export async function POST(req: NextRequest) {
  try {
    const { message } = await req.json();
    if (!message) {
      return NextResponse.json({ title: 'New Chat' });
    }

    if (!ANTHROPIC_API_KEY) {
      // Fallback: truncate the message
      return NextResponse.json({
        title: message.slice(0, 40) + (message.length > 40 ? '...' : ''),
      });
    }

    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 20,
        messages: [
          {
            role: 'user',
            content: `Generate a concise 3-5 word English title for a conversation that starts with this message. Return ONLY the title, no quotes, no punctuation, no explanation.\n\nMessage: "${message.slice(0, 200)}"`,
          },
        ],
      }),
    });

    if (!res.ok) {
      console.error('Claude title error:', res.status);
      return NextResponse.json({
        title: message.slice(0, 40) + (message.length > 40 ? '...' : ''),
      });
    }

    const data = await res.json();
    let title = (data.content?.[0]?.text || '').trim();
    // Clean: remove quotes, trailing punctuation
    title = title.replace(/^["']|["']$/g, '').replace(/[.!]+$/, '').trim();

    return NextResponse.json({
      title: title || message.slice(0, 40),
    });
  } catch (err) {
    console.error('Title generation error:', err);
    return NextResponse.json({
      title: 'New Chat',
    });
  }
}
