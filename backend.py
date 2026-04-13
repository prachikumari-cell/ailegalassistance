"""
backend.py — Constitutional Search Engine
Uses TF-IDF + keyword scoring to find relevant articles.
No heavy ML required. Fast, offline, reliable.
"""

import json
import os
import math
import re
from collections import Counter


def load_articles():
    """Load articles from JSON file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "data", "articles.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def tokenize(text):
    """Lowercase and split text into words, remove punctuation."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    # Simple stopword removal
    stopwords = {
        "the", "a", "an", "is", "in", "of", "to", "and", "or", "for",
        "on", "at", "by", "with", "are", "was", "be", "it", "this",
        "that", "as", "not", "shall", "any", "all", "no", "has", "have",
        "been", "from", "such", "which", "its", "their", "they", "also",
        "can", "may", "will", "would", "could", "should"
    }
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def build_tfidf(articles):
    """
    Build TF-IDF matrix from articles.
    Each article = title + text + keywords combined.
    """
    docs = []
    for art in articles:
        combined = (
            art["title"] + " " +
            art["text"] + " " +
            " ".join(art.get("keywords", [])) + " " +
            art["article"]
        )
        docs.append(tokenize(combined))

    # Build vocab
    vocab = set()
    for doc in docs:
        vocab.update(doc)
    vocab = list(vocab)

    N = len(docs)

    # IDF: log(N / df) for each term
    idf = {}
    for term in vocab:
        df = sum(1 for doc in docs if term in set(doc))
        idf[term] = math.log((N + 1) / (df + 1)) + 1  # smoothed

    # TF-IDF vectors for each document
    tfidf_vectors = []
    for doc in docs:
        tf = Counter(doc)
        total = len(doc) if len(doc) > 0 else 1
        vec = {}
        for term in set(doc):
            vec[term] = (tf[term] / total) * idf.get(term, 1)
        tfidf_vectors.append(vec)

    return tfidf_vectors, idf


def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two sparse vectors (dicts)."""
    # Dot product
    dot = sum(vec1.get(t, 0) * vec2.get(t, 0) for t in vec2)
    # Magnitudes
    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def keyword_bonus(query_tokens, article):
    """
    Give extra score if query words directly appear in article keywords.
    This improves precision for short, specific queries.
    """
    keywords_lower = [k.lower() for k in article.get("keywords", [])]
    article_text = article["article"].lower()
    bonus = 0.0
    for token in query_tokens:
        # Direct keyword match
        if any(token in kw for kw in keywords_lower):
            bonus += 0.15
        # Article number match (e.g. user types "article 21")
        if token in article_text:
            bonus += 0.25
    return min(bonus, 0.5)  # cap at 0.5


def search(query, articles, tfidf_vectors, idf, top_k=3):
    """
    Search for top-k most relevant articles for a given query.
    Returns list of (article, score, match_reason) tuples.
    """
    if not query.strip():
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    # Build query TF-IDF vector
    tf = Counter(query_tokens)
    total = len(query_tokens)
    query_vec = {}
    for term in set(query_tokens):
        query_vec[term] = (tf[term] / total) * idf.get(term, 1.0)

    results = []
    for i, (article, doc_vec) in enumerate(zip(articles, tfidf_vectors)):
        sim = cosine_similarity(query_vec, doc_vec)
        bonus = keyword_bonus(query_tokens, article)
        final_score = sim + bonus

        # Generate match reason
        matched_kws = [
            kw for kw in article.get("keywords", [])
            if any(qt in kw.lower() for qt in query_tokens)
        ]
        match_reason = f"Matched on: {', '.join(matched_kws[:4])}" if matched_kws else "Matched via semantic similarity"

        results.append((article, round(final_score, 4), match_reason))

    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)

    # Filter out very low scores
    results = [(a, s, r) for a, s, r in results if s > 0.01]

    return results[:top_k]


def get_relevance_label(score):
    """Convert score to human-readable relevance label."""
    if score >= 0.4:
        return "🔴 Highly Relevant"
    elif score >= 0.2:
        return "🟡 Relevant"
    elif score >= 0.08:
        return "🟢 Possibly Relevant"
    else:
        return "⚪ Low Match"


# Initialize on import — so Streamlit doesn't reload every time
_articles = load_articles()
_tfidf_vectors, _idf = build_tfidf(_articles)


def run_search(query, top_k=3):
    """
    Public API for the Streamlit app.
    Returns: list of dicts with article info + score.
    """
    results = search(query, _articles, _tfidf_vectors, _idf, top_k=top_k)
    output = []
    for article, score, reason in results:
        output.append({
            "article": article["article"],
            "title": article["title"],
            "text": article["text"],
            "simple_explanation": article["simple_explanation"],
            "keywords": article["keywords"],
            "score": score,
            "relevance": get_relevance_label(score),
            "match_reason": reason,
        })
    return output


def get_all_articles():
    """Return all articles (for the browse tab)."""
    return _articles
