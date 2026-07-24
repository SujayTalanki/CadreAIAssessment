import type { ChatResponse, Message } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * Sends the full conversation history to the backend and returns its reply.
 *
 * The backend always responds with HTTP 200 and a `{ reply, escalate }` body,
 * even for its own internal failure cases (rate limits, errors, etc.) — those
 * are represented as a graceful `reply` with `escalate: true`, not as a thrown
 * error here. This function only throws when something goes wrong *before*
 * that contract can even apply: the network is unreachable, the backend is
 * down, CORS is misconfigured, or the response body isn't valid/expected
 * JSON. Callers should treat a thrown error as "no graceful reply exists,
 * show a fallback error UI".
 */
export async function sendMessage(history: Message[]): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages: history }),
    });
  } catch {
    throw new Error(
      'Could not reach the Cadre AI support service. Please check your connection and try again.',
    );
  }

  if (!response.ok) {
    throw new Error(
      `Cadre AI support service returned an unexpected status (${response.status}). Please try again.`,
    );
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new Error('Received an unreadable response from the support service. Please try again.');
  }

  if (
    typeof data !== 'object' ||
    data === null ||
    typeof (data as Record<string, unknown>).reply !== 'string' ||
    typeof (data as Record<string, unknown>).escalate !== 'boolean'
  ) {
    throw new Error('Received an unexpected response shape from the support service.');
  }

  return data as ChatResponse;
}
