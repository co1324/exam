"""Knowledge base creation and querying utilities."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence


WORD_RE = re.compile(r"[\w']+")


@dataclass
class DocumentChunk:
    """Representation of a single chunk of reference text."""

    page_number: int
    chunk_index: int
    text: str

    def to_metadata(self) -> Dict[str, int]:
        return {"page_number": self.page_number, "chunk_index": self.chunk_index}


class SimpleTfidfVectorizer:
    """Minimal TF-IDF vectoriser that avoids optional heavy dependencies."""

    def __init__(self, lowercase: bool = True, stopwords: Optional[Sequence[str]] = None):
        self.lowercase = lowercase
        self.stopwords = set(stopwords or [])
        self.vocabulary_: Dict[str, int] = {}
        self.idf_: List[float] = []

    def _tokenize(self, text: str) -> List[str]:
        if self.lowercase:
            text = text.lower()
        tokens = WORD_RE.findall(text)
        return [token for token in tokens if token not in self.stopwords]

    def fit_transform(self, documents: Sequence[str]) -> List[Dict[int, float]]:
        self.vocabulary_.clear()
        self.idf_.clear()
        tokenised_docs: List[List[str]] = []
        document_frequency: Dict[str, int] = {}

        for doc in documents:
            tokens = self._tokenize(doc)
            tokenised_docs.append(tokens)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                document_frequency[token] = document_frequency.get(token, 0) + 1

        num_docs = len(documents)
        for token, df in sorted(document_frequency.items()):
            index = len(self.vocabulary_)
            self.vocabulary_[token] = index
            idf = math.log((1 + num_docs) / (1 + df)) + 1
            self.idf_.append(idf)

        return [self._vectorise(tokens) for tokens in tokenised_docs]

    def transform(self, documents: Sequence[str]) -> List[Dict[int, float]]:
        return [self._vectorise(self._tokenize(doc)) for doc in documents]

    def _vectorise(self, tokens: Sequence[str]) -> Dict[int, float]:
        if not tokens:
            return {}
        term_counts: Dict[int, int] = {}
        for token in tokens:
            if token not in self.vocabulary_:
                continue
            index = self.vocabulary_[token]
            term_counts[index] = term_counts.get(index, 0) + 1

        total_terms = sum(term_counts.values())
        vector: Dict[int, float] = {}
        for index, count in term_counts.items():
            tf = count / total_terms
            vector[index] = tf * self.idf_[index]
        return vector


def cosine_similarity(vector_a: Dict[int, float], vector_b: Dict[int, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""

    if not vector_a or not vector_b:
        return 0.0

    numerator = 0.0
    for index, value in vector_a.items():
        numerator += value * vector_b.get(index, 0.0)

    norm_a = math.sqrt(sum(value * value for value in vector_a.values()))
    norm_b = math.sqrt(sum(value * value for value in vector_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return numerator / (norm_a * norm_b)


@dataclass
class KnowledgeBase:
    """Vector-backed knowledge base of law chunks."""

    chunks: List[DocumentChunk]
    vectors: List[Dict[int, float]]
    vectorizer: SimpleTfidfVectorizer

    def query(self, query_text: str, top_k: int = 5) -> List[DocumentChunk]:
        query_vector = self.vectorizer.transform([query_text])[0]
        scored_chunks = [
            (cosine_similarity(query_vector, chunk_vector), chunk)
            for chunk_vector, chunk in zip(self.vectors, self.chunks)
        ]
        scored_chunks.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for score, chunk in scored_chunks[:top_k] if score > 0.0]

    def save(self, output_path: Path) -> None:
        """Serialise the knowledge base to disk."""

        payload = {
            "chunks": [chunk.__dict__ for chunk in self.chunks],
            "vectors": self.vectors,
            "vocabulary": self.vectorizer.vocabulary_,
            "idf": self.vectorizer.idf_,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, input_path: Path) -> "KnowledgeBase":
        """Load a knowledge base from disk."""

        payload = json.loads(input_path.read_text(encoding="utf-8"))
        chunks = [DocumentChunk(**chunk_dict) for chunk_dict in payload["chunks"]]
        vectors = [{int(k): v for k, v in vector.items()} for vector in payload["vectors"]]
        vectorizer = SimpleTfidfVectorizer()
        vectorizer.vocabulary_ = {token: int(index) for token, index in payload["vocabulary"].items()}
        vectorizer.idf_ = [float(value) for value in payload["idf"]]
        return cls(chunks=chunks, vectors=vectors, vectorizer=vectorizer)


class KnowledgeBaseBuilder:
    """Builder responsible for creating a knowledge base from a law PDF."""

    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200, stopwords: Optional[Sequence[str]] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.stopwords = stopwords or []

    def build_from_pages(self, pages: Sequence[str]) -> KnowledgeBase:
        chunks = self._chunk_pages(pages)
        vectorizer = SimpleTfidfVectorizer(stopwords=self.stopwords)
        vectors = vectorizer.fit_transform([chunk.text for chunk in chunks])
        return KnowledgeBase(chunks=chunks, vectors=vectors, vectorizer=vectorizer)

    def _chunk_pages(self, pages: Sequence[str]) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        for page_number, page_text in enumerate(pages, start=1):
            page_chunks = self._split_text(page_text, page_number)
            chunks.extend(page_chunks)
        return chunks

    def _split_text(self, text: str, page_number: int) -> List[DocumentChunk]:
        cursor = 0
        chunk_index = 0
        text = text.strip()
        size = self.chunk_size
        overlap = self.chunk_overlap
        chunks: List[DocumentChunk] = []

        while cursor < len(text):
            end = min(cursor + size, len(text))
            chunk_text = text[cursor:end].strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        page_number=page_number,
                        chunk_index=chunk_index,
                        text=chunk_text,
                    )
                )
                chunk_index += 1
            if end == len(text):
                break
            cursor = end - overlap
            if cursor < 0:
                cursor = 0
        return chunks


def persist_knowledge_base(kb: KnowledgeBase, directory: Path, filename: str = "knowledge_base.json") -> Path:
    """Persist the knowledge base in a deterministic location and return the path."""

    directory.mkdir(parents=True, exist_ok=True)
    output_path = directory / filename
    kb.save(output_path)
    return output_path
