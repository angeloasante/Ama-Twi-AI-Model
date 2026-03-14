/**
 * Embedding generation via server-side API route.
 * HF token stays on the server — client never sees it.
 */

export async function getEmbedding(text: string): Promise<number[]> {
  const res = await fetch('/api/embeddings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    console.error('Embedding API error:', res.status);
    throw new Error(`Embedding failed: ${res.status}`);
  }

  const data = await res.json();
  const embedding = data.embeddings;

  // API returns nested array for single input — flatten if needed
  if (Array.isArray(embedding) && Array.isArray(embedding[0])) {
    return embedding[0];
  }
  return embedding;
}

/**
 * Batch embed multiple texts (one API call)
 */
export async function getEmbeddings(texts: string[]): Promise<number[][]> {
  if (texts.length === 0) return [];

  const res = await fetch('/api/embeddings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texts }),
  });

  if (!res.ok) {
    console.error('Batch embedding API error:', res.status);
    throw new Error(`Batch embedding failed: ${res.status}`);
  }

  const data = await res.json();
  return data.embeddings;
}
