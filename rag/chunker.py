import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict


class TextChunker:
    """
    Splits text into overlapping chunks for RAG.
    Uses sentence-aware splitting so chunks don't cut mid-sentence.
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        chunk_size: target characters per chunk
        overlap: characters to repeat between consecutive chunks
                 so context isn't lost at boundaries
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, metadata: dict = None) -> list[Chunk]:
        """Split text into overlapping chunks."""
        if not text or not text.strip():
            return []

        # Clean up whitespace
        text = self._clean_text(text)

        # Split into sentences first — avoid cutting mid-sentence
        sentences = self._split_sentences(text)

        chunks = []
        current_chunk = ""
        current_start = 0
        char_pos = 0

        for sentence in sentences:
            # If adding this sentence exceeds chunk_size, save current chunk
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunk = Chunk(
                    text=current_chunk.strip(),
                    chunk_index=len(chunks),
                    start_char=current_start,
                    end_char=current_start + len(current_chunk),
                    metadata=metadata or {},
                )
                chunks.append(chunk)

                # Start new chunk with overlap from end of previous chunk
                overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                current_start = current_start + len(current_chunk) - len(overlap_text)
                current_chunk = overlap_text + sentence
            else:
                if not current_chunk:
                    current_start = char_pos
                current_chunk += sentence

            char_pos += len(sentence)

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                text=current_chunk.strip(),
                chunk_index=len(chunks),
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                metadata=metadata or {},
            ))

        print(f"[Chunker] Split into {len(chunks)} chunks "
              f"(chunk_size={self.chunk_size}, overlap={self.overlap})")
        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text on sentence boundaries."""
        # Split on period/exclamation/question followed by space or newline
        parts = re.split(r'(?<=[.!?])\s+', text)
        # Add space back so chunks join naturally
        return [p + " " for p in parts if p.strip()]

    def _clean_text(self, text: str) -> str:
        """Remove excessive whitespace and normalize newlines."""
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()