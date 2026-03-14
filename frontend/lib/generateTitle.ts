/**
 * Generate a conversation title using Claude (via server-side API route).
 * Falls back to truncated message on failure.
 */
export async function generateTitle(firstMessage: string): Promise<string> {
  try {
    const response = await fetch('/api/title', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: firstMessage }),
    });

    if (!response.ok) throw new Error('Title generation failed');

    const data = await response.json();
    return data.title || firstMessage.slice(0, 40);
  } catch {
    return firstMessage.slice(0, 40) + (firstMessage.length > 40 ? '...' : '');
  }
}
