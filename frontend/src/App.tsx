import { useState } from 'react';
import ChatWindow from './components/ChatWindow';
import MessageBubble from './components/MessageBubble';
import TypingIndicator from './components/TypingIndicator';
import EscalationCard, { CONTACT_URL } from './components/EscalationCard';
import ChatInput from './components/ChatInput';
import { sendMessage } from './lib/api';
import type { Message } from './types';

const GREETING: Message = {
  role: 'assistant',
  content:
    "Hi! I'm the Cadre AI assistant — ask me about our services, booking a call, or anything else.",
};

export default function App() {
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [escalatedIndices, setEscalatedIndices] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sends `history` (which already includes the outstanding user turn) to the
  // backend and appends the assistant's reply. Shared by both the initial
  // send and the "Retry" path so a retry never re-appends the user message.
  const postToBackend = async (history: Message[]) => {
    setIsLoading(true);
    setError(null);
    try {
      const { reply, escalate } = await sendMessage(history);
      // `history` is exactly the messages state at the time this call was
      // made (see handleSend/handleRetry below), so the assistant reply we're
      // about to append will land at this index.
      const newMessageIndex = history.length;
      const assistantMessage: Message = { role: 'assistant', content: reply };
      setMessages((prev) => [...prev, assistantMessage]);
      if (escalate) {
        setEscalatedIndices((prev) => new Set(prev).add(newMessageIndex));
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong reaching the Cadre AI support service.',
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = (text: string) => {
    const userMessage: Message = { role: 'user', content: text };
    const history = [...messages, userMessage];
    setMessages(history);
    void postToBackend(history);
  };

  const handleRetry = () => {
    void postToBackend(messages);
  };

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 shadow-sm sm:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            C
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Cadre AI Support</p>
            <p className="text-xs text-slate-500">Usually replies in a few seconds</p>
          </div>
        </div>
        <a
          href={CONTACT_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-100 sm:text-sm"
        >
          Contact us
        </a>
      </header>

      <ChatWindow>
        {messages.map((message, index) => (
          <div key={index} className="space-y-3">
            <MessageBubble message={message} />
            {escalatedIndices.has(index) && <EscalationCard />}
          </div>
        ))}

        {isLoading && <TypingIndicator />}

        {error && (
          <div className="flex w-full justify-start">
            <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl rounded-bl-sm border border-red-200 bg-red-50 px-4 py-3 shadow-sm">
              <p className="text-sm font-semibold text-red-800">Something went wrong</p>
              <p className="mt-1 text-sm text-red-700">{error}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleRetry}
                  disabled={isLoading}
                  className="inline-flex items-center rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  Retry
                </button>
                <a
                  href={CONTACT_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 transition-colors hover:bg-red-100"
                >
                  Contact us
                </a>
              </div>
            </div>
          </div>
        )}
      </ChatWindow>

      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
