import logging

import chromadb
import openai

from app.config import settings
from app.models import ChatMessage, ChatResponse
from app.services import retrieval
from app.system_prompt import SYSTEM_PROMPT, format_knowledge_block

logger = logging.getLogger(__name__)

# Only an OpenRouter key (sk-or-...) was available for this exercise, not a
# native Anthropic key (sk-ant-...), so Claude is called through OpenRouter's
# OpenAI-compatible endpoint rather than the native Anthropic SDK. This also
# happens to match Cadre AI's own stated approach in the brief ("OpenRouter
# for model access"). Reasoning/extended-thinking is explicitly disabled via
# extra_body, since OpenRouter's unified API doesn't expose Anthropic's
# `thinking` param directly - this is a grounded-QA task with no need for it.
_client = openai.OpenAI(
    base_url=settings.OPENROUTER_BASE_URL, api_key=settings.OPENROUTER_API_KEY
)

ESCALATE_MARKER = "[[ESCALATE]]"

RATE_LIMIT_MESSAGE = (
    "We're getting a lot of questions right now. Please try again in a "
    "moment, or reach out to us directly at hello@cadreai.io."
)
CONNECTION_ERROR_MESSAGE = (
    "Something went wrong on our end. Please try again, or reach out to "
    "us directly at hello@cadreai.io."
)
GENERIC_ERROR_MESSAGE = (
    "Sorry, something went wrong while answering that. Please try again, "
    "or reach out to us directly at hello@cadreai.io."
)


def _parse_escalation(reply_text: str) -> tuple[str, bool]:
    # The system prompt places the marker on its own final line, so match
    # that exactly rather than substring-containment - otherwise a user
    # message that happens to quote the literal marker back would falsely
    # flag escalation.
    escalate = reply_text.rstrip().endswith(ESCALATE_MARKER)
    if escalate:
        reply_text = reply_text.rstrip()[: -len(ESCALATE_MARKER)]
    return reply_text.strip(), escalate


def generate_reply(
    messages: list[ChatMessage], collection: chromadb.Collection
) -> ChatResponse:
    # Retrieval, the API call, and response parsing all live inside one try
    # block: CLAUDE.md guarantees /api/chat always returns HTTP 200 with a
    # graceful message, and a failure anywhere in this chain (a Chroma
    # error, an empty choices list on a provider-side refusal, etc.) needs
    # to hit that same fallback rather than bubbling up as a 500.
    try:
        latest_user_message = messages[-1].content
        # k=10 (out of 13 entries): compound questions ("what do you do, and
        # do you serve X industry?") have repeatedly pushed industries-served
        # out of smaller top-k windows as the corpus grew (k=3 -> k=5 -> k=6
        # all eventually regressed; at one point it ranked #8/13 for a
        # real-estate question despite literally mentioning "real estate").
        # Embedding similarity isn't reliable at distinguishing short,
        # closely-related FAQ entries at this scale, so k is set high enough
        # to retrieve nearly the whole corpus rather than chasing k again.
        # A real fix (better chunking/retrieval strategy, e.g. splitting
        # multi-topic entries or re-ranking) is a follow-up, not a quick fix.
        chunks = retrieval.query(collection, latest_user_message, k=10)
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
