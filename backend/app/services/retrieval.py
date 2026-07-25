"""FAQ retrieval over an in-memory Chroma collection.

We intentionally use chromadb.Client() (in-memory) rather than a
PersistentClient. There is no persistent volume for this service by design:
the FAQ knowledge base is small and static, so it's cheaper and simpler to
rebuild the collection from faqs.json fresh on every app startup than to
manage on-disk index state.
"""

import json
from pathlib import Path
import chromadb

DEFAULT_FAQS_PATH = Path(__file__).parent.parent / "data" / "faqs.json"
COLLECTION_NAME = "cadre_faqs"


def ingest_faqs(faqs_path: str | Path | None = None) -> chromadb.Collection:
    """
    Load the FAQ corpus from disk and embed it into a fresh Chroma collection.

    Args:
        faqs_path (str | Path | None): Path to the FAQ JSON file. Defaults to
            DEFAULT_FAQS_PATH (app/data/faqs.json) when not provided.

    Returns:
        chromadb.Collection: An in-memory collection with one embedded
            document per FAQ entry, storing id/category/question/answer as
            metadata on each.
    """
    path = Path(faqs_path) if faqs_path is not None else DEFAULT_FAQS_PATH
    with open(path, "r", encoding="utf-8") as f:
        faqs = json.load(f)

    client = chromadb.Client()
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    documents = [f"{faq['question']} {faq['answer']}" for faq in faqs]
    metadatas = [
        {
            "id": faq["id"],
            "category": faq["category"],
            "question": faq["question"],
            "answer": faq["answer"],
        }
        for faq in faqs
    ]
    ids = [faq["id"] for faq in faqs]

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    return collection


def query(collection: chromadb.Collection, text: str, k: int) -> list[dict]:
    """
    Embed a query and return the k most similar FAQ entries.

    Args:
        collection (chromadb.Collection): The FAQ collection to search, as
            returned by ingest_faqs().
        text (str): The text to embed and search against, typically the
            latest user message.
        k (int): The number of matching FAQ entries to return.

    Returns:
        list[dict]: The top-k matching entries, each with id, category,
            question, and answer keys, ordered by similarity.
    """
    results = collection.query(query_texts=[text], n_results=k)
    metadatas = results.get("metadatas") or []
    matches = metadatas[0] if metadatas else []

    return [
        {
            "id": meta["id"],
            "category": meta["category"],
            "question": meta["question"],
            "answer": meta["answer"],
        }
        for meta in matches
    ]
