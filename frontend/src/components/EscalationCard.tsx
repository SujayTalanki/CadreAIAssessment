const BOOKING_URL = 'https://cal.com/cadre-ai/strategy-call';
const SUPPORT_EMAIL = 'hello@cadreai.io';

interface EscalationCardProps {
  /** The user's last question, used to pre-fill the email body for context. */
  lastUserMessage?: string;
  /** Optional heading override, e.g. for the network-error safety net variant. */
  heading?: string;
  /** Optional supporting copy override. */
  description?: string;
}

export default function EscalationCard({
  lastUserMessage,
  heading = "Looks like this needs a human touch",
  description = "I've done what I can from here — the fastest way forward is to talk directly with the Cadre AI team.",
}: EscalationCardProps) {
  const subject = encodeURIComponent('Question from the Cadre AI support chat');
  const bodyLines = [
    "Hi Cadre AI team,",
    "",
    "I was chatting with the support bot and wanted to follow up on this:",
    lastUserMessage ? `"${lastUserMessage}"` : '(no question captured)',
    "",
    "Thanks!",
  ];
  const body = encodeURIComponent(bodyLines.join('\n'));
  const mailtoHref = `mailto:${SUPPORT_EMAIL}?subject=${subject}&body=${body}`;

  return (
    <div className="flex w-full justify-start">
      <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl rounded-bl-sm border border-indigo-200 bg-indigo-50 px-4 py-3 shadow-sm">
        <p className="text-sm font-semibold text-indigo-900">{heading}</p>
        <p className="mt-1 text-sm text-indigo-800">{description}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <a
            href={BOOKING_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
          >
            Book a call
          </a>
          <a
            href={mailtoHref}
            className="inline-flex items-center rounded-lg border border-indigo-300 bg-white px-3 py-1.5 text-sm font-medium text-indigo-700 transition-colors hover:bg-indigo-100"
          >
            Email us
          </a>
        </div>
      </div>
    </div>
  );
}
