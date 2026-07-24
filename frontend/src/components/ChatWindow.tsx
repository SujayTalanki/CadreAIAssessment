import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

interface ChatWindowProps {
  children: ReactNode;
}

/**
 * Scrollable message list container. Auto-scrolls to the bottom whenever its
 * contents change (new message, typing indicator appearing/disappearing,
 * escalation card, error banner, etc).
 */
export default function ChatWindow({ children }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  });

  return (
    <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-3 py-4 sm:px-6">
      {children}
      <div ref={bottomRef} />
    </div>
  );
}
