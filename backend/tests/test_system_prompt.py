from app.system_prompt import format_knowledge_block


def test_format_knowledge_block_with_chunks():
    chunks = [
        {"id": "book-a-call", "category": "process", "question": "How do I book a call?", "answer": "Visit cal.com/cadre-ai."},
        {"id": "core-services", "category": "services", "question": "What services do you offer?", "answer": "AI Strategy, AI Agents."},
    ]

    block = format_knowledge_block(chunks)

    assert "Relevant knowledge for this question" in block
    assert "How do I book a call?" in block
    assert "Visit cal.com/cadre-ai." in block
    assert "What services do you offer?" in block


def test_format_knowledge_block_with_no_chunks_nudges_toward_escalation():
    block = format_knowledge_block([])

    assert "No matching knowledge" in block
    assert "Do not guess" in block
