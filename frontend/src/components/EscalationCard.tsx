export const CONTACT_URL = 'https://www.cadreai.com/contact';

export default function EscalationCard() {
  const heading = "Looks like this needs a human touch";
  const description =
    "I've done what I can from here — the fastest way forward is to talk directly with the Cadre AI team.";

  return (
    <div className="flex w-full justify-start">
      <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl rounded-bl-sm border border-indigo-200 bg-indigo-50 px-4 py-3 shadow-sm">
        <p className="text-sm font-semibold text-indigo-900">{heading}</p>
        <p className="mt-1 text-sm text-indigo-800">{description}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <a
            href={CONTACT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
          >
            Talk With Our Team
          </a>
        </div>
      </div>
    </div>
  );
}
