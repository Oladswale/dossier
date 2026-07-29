"""
Free, local, extractive summarization fallback.

Used only when a feed entry has no usable publisher-written summary/
description. Scores sentences by word-frequency (a minimal TextRank-style
heuristic) and returns the top N in original order. No API calls, no
downloads, no cost — runs entirely inside the GitHub Actions runner.
"""

import re
from collections import Counter

_STOPWORDS = set("""
a an the and or but if while is are was were be been being to of in on
for with as by at from this that these those it its it's he she they we
you your his her their our not no nor so than then too very can will
just about into over under after before up down out off again further
here there when where why how all any both each few more most other some
such only own same can't cannot could would should shall might must
""".split())

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[a-zA-Z']+")


def clean_html(text: str) -> str:
    """Strip HTML tags/entities from feed content, collapse whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&amp;|&#\d+;|&\w+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extractive_summary(text: str, max_sentences: int = 3) -> str:
    """Pick the most representative sentences from `text`, in original order."""
    text = clean_html(text)
    if not text:
        return ""

    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    if len(sentences) <= max_sentences:
        return text

    words = [w.lower() for w in _WORD_RE.findall(text) if w.lower() not in _STOPWORDS]
    freq = Counter(words)
    if not freq:
        return " ".join(sentences[:max_sentences])

    max_freq = max(freq.values())
    for w in freq:
        freq[w] /= max_freq

    scores = []
    for i, sent in enumerate(sentences):
        sent_words = [w.lower() for w in _WORD_RE.findall(sent)]
        if not sent_words:
            scores.append((0.0, i, sent))
            continue
        score = sum(freq.get(w, 0.0) for w in sent_words) / len(sent_words)
        # small bonus for early sentences (leads usually carry the gist)
        position_bonus = 1.0 if i < 2 else 0.0
        scores.append((score + position_bonus * 0.15, i, sent))

    top = sorted(scores, key=lambda x: x[0], reverse=True)[:max_sentences]
    top_in_order = [s for _, _, s in sorted(top, key=lambda x: x[1])]
    return " ".join(top_in_order)


def best_summary(publisher_summary: str, fallback_body: str = "", max_sentences: int = 3) -> str:
    """Prefer the publisher's own summary; fall back to local extraction."""
    cleaned = clean_html(publisher_summary)
    if cleaned and len(cleaned.split()) >= 8:
        # trim overly long publisher summaries too, for consistency
        sentences = [s.strip() for s in _SENT_SPLIT.split(cleaned) if s.strip()]
        return " ".join(sentences[:max_sentences]) if len(sentences) > max_sentences else cleaned
    if fallback_body:
        return extractive_summary(fallback_body, max_sentences)
    return cleaned
