import logging

import anthropic
import chromadb

from app.config import settings
from app.models import ChatMessage, ChatResponse
from app.services import retrieval
from app.system_prompt import SYSTEM_PROMPT, format_knowledge_block

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

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
    escalate = ESCALATE_MARKER in reply_text
    return reply_text.replace(ESCALATE_MARKER, "").strip(), escalate


def generate_reply(
    messages: list[ChatMessage], collection: chromadb.Collection
) -> ChatResponse:
    latest_user_message = messages[-1].content
    chunks = retrieval.query(collection, latest_user_message, k=3)
    system = SYSTEM_PROMPT + "\n\n" + format_knowledge_block(chunks)

    anthropic_messages = [
        {"role": m.role, "content": m.content} for m in messages
    ]

    try:
        response = _client.messages.create(
            model=settings.MODEL_NAME,
            max_tokens=1024,
            thinking={"type": "disabled"},
            system=system,
            messages=anthropic_messages,
        )
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limit hit")
        return ChatResponse(reply=RATE_LIMIT_MESSAGE, escalate=True)
    except anthropic.AuthenticationError:
        logger.error("Anthropic authentication failed - check ANTHROPIC_API_KEY")
        return ChatResponse(reply=GENERIC_ERROR_MESSAGE, escalate=True)
    except (anthropic.APIConnectionError, anthropic.APIStatusError) as e:
        logger.error("Anthropic API error: %s", e)
        return ChatResponse(reply=CONNECTION_ERROR_MESSAGE, escalate=True)
    except Exception:
        logger.exception("Unexpected error calling Anthropic")
        return ChatResponse(reply=GENERIC_ERROR_MESSAGE, escalate=True)

    reply_text = next(
        (block.text for block in response.content if block.type == "text"), ""
    )
    reply_text, escalate = _parse_escalation(reply_text)
    return ChatResponse(reply=reply_text, escalate=escalate)
