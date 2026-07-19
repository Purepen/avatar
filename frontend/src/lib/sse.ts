/** SSE consumer for POST /api/chat.
 *
 * fetch() + manual stream parsing (EventSource cannot send a POST body).
 * Yields {event, data} pairs; throws RateLimitError on HTTP 429.
 */

export interface SseEvent {
  event: string;
  data: Record<string, unknown>;
}

export class RateLimitError extends Error {}

export async function* streamChat(payload: {
  conversation_id: string;
  message: string;
  visitor_name?: string;
  attention?: boolean;
}): AsyncGenerator<SseEvent> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (response.status === 429) throw new RateLimitError();
  if (!response.ok || !response.body) {
    throw new Error(`chat request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = "";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (event && data) yield { event, data: JSON.parse(data) };
    }
  }
}
