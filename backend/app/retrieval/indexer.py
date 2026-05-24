from __future__ import annotations

from dataclasses import dataclass

from app.embedding import BaseEmbeddingProvider, get_embedding_provider
from app.vector_store import BaseVectorStore, VectorRecord, get_vector_store

from .chunk_builder import build_course_chunks
from .chunk_schema import KnowledgeChunk


@dataclass
class CourseVectorIndex:
    chunks: list[KnowledgeChunk]
    store: BaseVectorStore
    embedding: BaseEmbeddingProvider

    @property
    def chunks_by_id(self) -> dict[str, KnowledgeChunk]:
        return {chunk.id: chunk for chunk in self.chunks}


def build_course_vector_index(
    course: dict,
    *,
    embedding: BaseEmbeddingProvider | None = None,
    store: BaseVectorStore | None = None,
) -> CourseVectorIndex:
    embedding = embedding or get_embedding_provider()
    course_id = str(course.get("id", "course"))
    store = store or get_vector_store(collection_name=course_id)
    chunks = build_course_chunks(course)
    texts = [f"{chunk.chapter_title} {chunk.section_label} {' '.join(chunk.keywords)} {chunk.text}" for chunk in chunks]
    vectors = embedding.embed_batch(texts)
    store.upsert(
        [
            VectorRecord(
                id=chunk.id,
                vector=vector,
                document=chunk.text,
                metadata={
                    "chunk_id": chunk.id,
                    "course_id": chunk.course_id,
                    "chapter_id": chunk.chapter_id,
                    "chapter_title": chunk.chapter_title,
                    "section": chunk.section,
                    "section_label": chunk.section_label,
                    "difficulty": chunk.difficulty,
                    "source_type": chunk.source_type,
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]
    )
    return CourseVectorIndex(chunks=chunks, store=store, embedding=embedding)
