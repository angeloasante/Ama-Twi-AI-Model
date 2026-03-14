import { NextRequest, NextResponse } from 'next/server';

const HF_EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2';
const HF_TOKEN = process.env.HF_TOKEN || '';

export async function POST(req: NextRequest) {
  try {
    const { text, texts } = await req.json();

    if (!HF_TOKEN) {
      return NextResponse.json({ error: 'HF token not configured' }, { status: 500 });
    }

    const input = texts || [text];

    const res = await fetch(
      `https://router.huggingface.co/hf-inference/models/${HF_EMBEDDING_MODEL}/pipeline/feature-extraction`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${HF_TOKEN}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          inputs: input,
          options: { wait_for_model: true },
        }),
      },
    );

    if (!res.ok) {
      return NextResponse.json({ error: `Embedding failed: ${res.status}` }, { status: res.status });
    }

    const embeddings = await res.json();
    return NextResponse.json({ embeddings });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
