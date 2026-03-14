/**
 * /api/chat — Thin proxy to Modal agentic endpoint.
 * All tool logic, API keys, and model inference live on Modal.
 * This route just forwards requests and adds the API key.
 * Includes retry logic for cold starts (Modal needs ~30-60s to load model).
 */

import { NextRequest, NextResponse } from 'next/server';

const MODAL_CHAT_ENDPOINT =
  process.env.MODAL_CHAT_ENDPOINT ||
  'https://angeloasante--twi-qwen-model-chat.modal.run';
const AMA_API_KEY = process.env.AMA_API_KEY || '';

async function callModal(payload: object, retries = 2): Promise<Response> {
  for (let i = 0; i <= retries; i++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120_000); // 2 min timeout

      const res = await fetch(MODAL_CHAT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeout);
      return res;
    } catch (err: any) {
      const isLastAttempt = i === retries;
      if (isLastAttempt) throw err;
      // Wait 2s before retry on connection errors (cold start)
      await new Promise(r => setTimeout(r, 2000));
    }
  }
  throw new Error('Unreachable');
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const res = await callModal({
      inputs: body.inputs || '',
      timezone: body.parameters?.timezone || body.timezone || 'UTC',
      history: body.history || [],
      api_key: AMA_API_KEY,
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('Modal error:', res.status, err);
      return NextResponse.json(
        {
          success: false,
          response: 'Kafra — an error occurred. Please try again.',
          tools_used: [],
          tool_results: {},
        },
        { status: res.status },
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      {
        success: false,
        response: 'Ama is waking up — please try again in a few seconds! (Cold start)',
        tools_used: [],
        tool_results: {},
      },
      { status: 503 },
    );
  }
}
