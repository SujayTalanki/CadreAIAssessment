from app.services.retrieval import ingest_faqs, query


def test_ingest_loads_all_faqs():
    collection = ingest_faqs()
    assert collection.count() == 12


def test_query_returns_relevant_faq_for_booking():
    collection = ingest_faqs()
    results = query(collection, "how do I book a call with a strategist", k=3)

    assert len(results) == 3
    assert results[0]["id"] == "book-a-call"


def test_query_returns_relevant_faq_for_maturity_index():
    collection = ingest_faqs()
    results = query(collection, "what is the AI maturity index", k=2)

    assert results[0]["id"] == "ai-maturity-index"


def test_query_returns_relevant_faq_for_why_us():
    collection = ingest_faqs()
    results = query(collection, "why should we choose Cadre AI over another vendor", k=3)

    assert "why-cadre-ai" in [r["id"] for r in results]
