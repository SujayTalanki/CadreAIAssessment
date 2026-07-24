from app.services.anthropic_client import _parse_escalation


def test_no_marker_means_no_escalation():
    text, escalate = _parse_escalation("You can book a call at https://cal.com/cadre-ai/strategy-call.")

    assert escalate is False
    assert "[[ESCALATE]]" not in text


def test_marker_is_stripped_and_flags_escalation():
    text, escalate = _parse_escalation(
        "I'm not sure about that, let me connect you with a strategist.\n[[ESCALATE]]"
    )

    assert escalate is True
    assert "[[ESCALATE]]" not in text
    assert text == "I'm not sure about that, let me connect you with a strategist."
