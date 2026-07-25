"""Calls Claude (via OpenRouter) to generate a grounded chat reply.

Only an OpenRouter key (sk-or-...) was available for this exercise, not a
native Anthropic key (sk-ant-...), so Claude is called through OpenRouter's
OpenAI-compatible endpoint rather than the native Anthropic SDK. This also
happens to match Cadre AI's own stated approach in the brief ("OpenRouter
for model access"). Reasoning/extended-thinking is explicitly disabled via
extra_body, since OpenRouter's unified API doesn't expose Anthropic's
`thinking` param directly - this is a grounded-QA task with no need for it.
"""

import logging
import chromadb
import openai
from app.config import settings
from app.models import ChatMessage, ChatResponse
from app.services import retrieval
from app.system_prompt import SYSTEM_PROMPT, format_knowledge_block

logger = logging.getLogger(__name__)

_client = openai.OpenAI(
    base_url=settings.OPENROUTER_BASE_URL, api_key=settings.OPENROUTER_API_KEY
)

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


def generate_reply(messages: list[ChatMessage], collection: chromadb.Collection) -> ChatResponse:
    """
    Retrieve relevant FAQ knowledge and generate a grounded chat reply.

    Retrieval, the API call, and response parsing all live inside one try
    block: CLAUDE.md guarantees /api/chat always returns HTTP 200 with a
    graceful message, and a failure anywhere in this chain (a Chroma error,
    an empty choices list on a provider-side refusal, etc.) needs to hit
    that same fallback rather than bubbling up as a 500.

    Retrieval always fetches the entire corpus (k=collection.count()), not
    a fixed number. Fixed k values (3 -> 5 -> 6 -> 10) each got outpaced by
    corpus growth in turn - a compound question like "what do you do, and
    do you serve X industry?" repeatedly pushed industries-served out of
    the top-k window as more FAQs were added (it eventually ranked #11/15).
    Embedding similarity isn't reliable at distinguishing short,
    closely-related FAQ entries at this scale, so top-k filtering doesn't
    actually earn its keep yet - the corpus is small enough that always
    including everything is simpler and permanently removes this failure
    mode. Revisit top-k filtering (with a real chunking/re-ranking
    strategy) if the corpus grows large enough that including it all
    becomes a real cost/latency concern - it isn't at 15 entries.

    Args:
        messages (list[ChatMessage]): The full conversation history so
            far, most recent message last.
        collection (chromadb.Collection): The FAQ collection to retrieve
            from, built once at app startup.

    Returns:
        ChatResponse: The assistant's reply and whether to escalate to a
            human. Always returns a graceful message on failure rather
            than raising.
    """
    try:
        latest_user_message = messages[-1].content
        chunks = retrieval.query(collection, latest_user_message, k=collection.count())
        system = SYSTEM_PROMPT + "\n\n" + format_knowledge_block(chunks)

        chat_messages = [{"role": "system", "content": system}] + [
            {"role": m.role, "content": m.content} for m in messages
        ]

        response = _client.chat.completions.create(
            model=settings.MODEL_NAME,
            max_tokens=1024,
            messages=chat_messages,
            extra_body={"reasoning": {"enabled": False}},
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
