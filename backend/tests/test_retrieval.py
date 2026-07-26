from app.services.retrieval import ingest_faqs, query


def test_ingest_loads_all_faqs():
    collection = ingest_faqs()
    assert collection.count() == 27


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


def test_query_returns_relevant_faq_for_learn_more_resources():
    collection = ingest_faqs()
    results = query(collection, "do you have a podcast or blog I can check out", k=3)

    assert "learn-more-resources" in [r["id"] for r in results]


def test_query_returns_relevant_faq_for_careers():
    collection = ingest_faqs()
    results = query(collection, "are you hiring, how do I apply for a job there", k=3)

    assert "careers-jobs" in [r["id"] for r in results]


def test_query_returns_relevant_faq_for_events():
    collection = ingest_faqs()
    results = query(collection, "do you host any webinars or speaking events", k=3)

    assert "events" in [r["id"] for r in results]


def test_query_returns_industries_served_for_compound_question():
    collection = ingest_faqs()
    results = query(
        collection,
        "What does Cadre AI do, and do you work with real estate companies?",
        k=collection.count(),
    )

    assert "industries-served" in [r["id"] for r in results]
