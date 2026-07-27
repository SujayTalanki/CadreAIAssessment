"""Calls Claude (via OpenRouter) to generate a grounded chat reply.

Only an OpenRouter key (sk-or-...) was available for this exercise, not a
native Anthropic key (sk-ant-...), so Claude is called through OpenRouter's
OpenAI-compatible endpoint rather than the native Anthropic SDK. This also
happens to match Cadre AI's own stated approach in the brief ("OpenRouter
for model access"). Reasoning/extended-thinking is explicitly disabled via
extra_body, since OpenRouter's unified API doesn't expose Anthropic's
`thinking` param directly - this is a grounded-QA task with no need for it.

No vector store: the entire FAQ corpus is loaded fresh from faqs.json on
every call and sent in full - a plain file read, cheap enough not to
bother caching in memory, so editing faqs.json takes effect on the very
next request with no restart needed. The resulting prompt is still cached
on OpenRouter's side (see generate_reply) to reduce token usage, latency,
and cost - that's a different kind of caching, applied after this load.
"""

import json
import logging
from pathlib import Path
import openai
from app.config import settings
from app.models import ChatMessage, ChatResponse
from app.system_prompt import SYSTEM_PROMPT, format_knowledge_block

logger = logging.getLogger(__name__)
_client = openai.OpenAI(base_url=settings.OPENROUTER_BASE_URL, api_key=settings.OPENROUTER_API_KEY)

FAQS_PATH = Path(__file__).parent.parent / "data" / "faqs.json"


def _load_knowledge_block() -> str:
    """
    Load the FAQ corpus fresh from disk and format it into a knowledge block.

    Read on every call (not cached) - a plain file read with no per-query
    ranking involved, so the result is already deterministic across every
    call, and cheap enough that editing faqs.json can take effect
    immediately without a server restart.

    Returns:
        str: The formatted "Relevant knowledge for this question" block.
    """
    with open(FAQS_PATH, "r", encoding="utf-8") as f:
        faqs = json.load(f)
    return format_knowledge_block(faqs)


ESCALATE_MARKER = "[[ESCALATE]]"

RATE_LIMIT_MESSAGE = (
    "We're getting a lot of questions right now. Please try again in a "
    "moment, or reach out to us directly."
)

CONNECTION_ERROR_MESSAGE = (
    "Something went wrong on our end. Please try again, or reach out to "
    "us directly."
)

GENERIC_ERROR_MESSAGE = (
    "Sorry, something went wrong while answering that. Please try again, "
    "or reach out to us directly."
)


def _parse_escalation(reply_text: str) -> tuple[str, bool]:
    """
    Strip the escalation marker from a reply and report whether it was present.

    The system prompt places the marker on its own final line, so this
    matches that exactly rather than substring-containment - otherwise a
    user message that happens to quote the literal marker back would
    falsely flag escalation.

    Args:
        reply_text (str): The raw model reply, possibly ending in the
            ESCALATE_MARKER on its own line.

    Returns:
        tuple[str, bool]: The reply text with the marker removed, and
            whether escalation was flagged.
    """
    escalate = reply_text.rstrip().endswith(ESCALATE_MARKER)
    if escalate:
        reply_text = reply_text.rstrip()[: -len(ESCALATE_MARKER)]
    return reply_text.strip(), escalate


def generate_reply(messages: list[ChatMessage]) -> ChatResponse:
    """
    Generate a grounded chat reply using the full FAQ corpus as context.

    The API call and response parsing live inside one try block: CLAUDE.md
    guarantees /api/chat always returns HTTP 200 with a graceful message,
    and a failure anywhere in this chain (an empty choices list on a
    provider-side refusal, etc.) needs to hit that same fallback rather
    than bubbling up as a 500.

    Args:
        messages (list[ChatMessage]): The full conversation history so
            far, most recent message last.

    Returns:
        ChatResponse: The assistant's reply and whether to escalate to a
            human. Always returns a graceful message on failure rather
            than raising.
    """
    try:
        system_text = SYSTEM_PROMPT + "\n\n" + _load_knowledge_block()

        chat_messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_text,
                        "cache_control": {"type": "ephemeral", "ttl": "1h"},
                    }
                ],
            }
        ] + [{"role": m.role, "content": m.content} for m in messages]

        response = _client.chat.completions.create(
            model=settings.MODEL_NAME,
            max_tokens=1024,
            messages=chat_messages,
            extra_body={
                "reasoning": {"enabled": False},
                "session_id": "cadre-ai-chatbot-shared-system-prompt-cache",
            },
        )
        reply_text = response.choices[0].message.content or ""
    except openai.RateLimitError:
        logger.warning("OpenRouter rate limit hit")
        return ChatResponse(reply=RATE_LIMIT_MESSAGE, escalate=True)
    except openai.AuthenticationError:
        logger.error("OpenRouter authentication failed - check OPENROUTER_API_KEY")
        return ChatResponse(reply=GENERIC_ERROR_MESSAGE, escalate=True)
    except (openai.APIConnectionError, openai.APIStatusError) as e:
        logger.error("OpenRouter API error: %s", e)
        return ChatResponse(reply=CONNECTION_ERROR_MESSAGE, escalate=True)
    except Exception:
        logger.exception("Unexpected error generating a reply")
        return ChatResponse(reply=GENERIC_ERROR_MESSAGE, escalate=True)

    reply_text, escalate = _parse_escalation(reply_text)
    return ChatResponse(reply=reply_text, escalate=escalate)
