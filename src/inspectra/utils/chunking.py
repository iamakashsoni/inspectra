"""Split large diffs into LLM-safe chunks."""

from __future__ import annotations

from dataclasses import dataclass

from inspectra.utils.tokenizer import count_tokens


@dataclass
class DiffChunk:
    file_path: str
    content: str
    token_count: int

    def __repr__(self) -> str:
        return f"<DiffChunk file={self.file_path!r} tokens={self.token_count}>"


def chunk_diff_by_file(
    file_diffs: dict[str, str],
    max_chunk_tokens: int = 3000,
) -> list[DiffChunk]:
    """
    Given a mapping of {file_path: diff_text}, produce a list of DiffChunks
    where each chunk stays within `max_chunk_tokens`.

    Large single-file diffs are split by hunk boundaries.
    """
    chunks: list[DiffChunk] = []

    for file_path, diff_text in file_diffs.items():
        token_count = count_tokens(diff_text)

        if token_count <= max_chunk_tokens:
            chunks.append(
                DiffChunk(file_path=file_path, content=diff_text, token_count=token_count)
            )
        else:
            # Split by hunk headers (@@ ... @@)
            sub_chunks = _split_by_hunks(file_path, diff_text, max_chunk_tokens)
            chunks.extend(sub_chunks)

    return chunks


def _split_by_hunks(file_path: str, diff_text: str, max_tokens: int) -> list[DiffChunk]:
    """Split a single file's diff into multiple chunks by hunk boundaries."""
    lines = diff_text.splitlines(keepends=True)
    hunk_groups: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if line.startswith("@@") and current:
            hunk_groups.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        hunk_groups.append(current)

    chunks: list[DiffChunk] = []
    buffer: list[str] = []
    buffer_tokens = 0

    for group in hunk_groups:
        group_text = "".join(group)
        group_tokens = count_tokens(group_text)

        if buffer_tokens + group_tokens > max_tokens and buffer:
            content = "".join(buffer)
            chunks.append(
                DiffChunk(
                    file_path=file_path,
                    content=content,
                    token_count=count_tokens(content),
                )
            )
            buffer = []
            buffer_tokens = 0

        buffer.extend(group)
        buffer_tokens += group_tokens

    if buffer:
        content = "".join(buffer)
        chunks.append(
            DiffChunk(
                file_path=file_path,
                content=content,
                token_count=count_tokens(content),
            )
        )

    return chunks
