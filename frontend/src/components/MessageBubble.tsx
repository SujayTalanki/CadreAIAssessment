import ReactMarkdown from 'react-markdown';
import type { Message } from '../types';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-white text-slate-800 border border-slate-200 rounded-bl-sm'
        }`}
      >
        <div
          className={`prose prose-sm max-w-none break-words ${
            isUser
              ? 'prose-invert prose-p:text-white prose-a:text-white prose-strong:text-white prose-li:text-white'
              : 'prose-slate prose-a:text-indigo-600'
          } prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-headings:my-1.5`}
        >
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
