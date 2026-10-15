"""
Text cleaning and page-aware chunking service.
Rule 7: Stores document IDs, filenames, page numbers, and chunk metadata for citations.
Associates each chunk with its original source page.
"""
import re
from typing import List, Dict, Any

def clean_text(text: str) -> str:
    """
    Cleans extracted text without removing meaningful content:
    - Normalizes Unicode spaces and line endings.
    - Removes non-printable/null control characters.
    - Condenses multiple consecutive blank lines to at most two.
    - Trims extraneous whitespace around lines.
    """
    if not text:
        return ""

    # Replace null bytes and non-breaking spaces
    text = text.replace("\x00", "").replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")

    # Remove non-printable characters while keeping newlines and tabs
    text = re.sub(r"[\x01-\x08\x0b\x0e-\x1f\x7f]", "", text)

    # Normalize excessive spaces within lines
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    cleaned_lines = []
    blank_counter = 0

    for line in lines:
        if line:
            blank_counter = 0
            cleaned_lines.append(line)
        else:
            blank_counter += 1
            if blank_counter <= 1:
                cleaned_lines.append("")

    return "\n".join(cleaned_lines).strip()

def approximate_token_count(text: str) -> int:
    """Estimates token count using standard word split approximation."""
    if not text:
        return 0
    words = text.split()
    # Word count is roughly 0.75 of token count; len(words) * 1.3 is standard
    return max(1, int(len(words) * 1.3))

def split_text_with_overlap(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[str]:
    """
    Splits text into chunks of maximum `chunk_size` characters with `chunk_overlap`.
    Tries to split on sentence boundaries (., !, ?, \n) to preserve readability.
    Ensures safe loop termination and snaps chunk starts to line/word boundaries.
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks: List[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        if end < text_len:
            # Look backwards from 'end' for a clean sentence or paragraph delimiter
            sub = text[start:end]
            # Try to find paragraph break or sentence end in the last 40% of the chunk
            search_window_start = max(0, int(len(sub) * 0.6))
            delimiters = [m.start() for m in re.finditer(r"(\.\s+|\n\n|\n)", sub[search_window_start:])]

            if delimiters:
                split_point = search_window_start + delimiters[-1] + 1
                end = start + split_point

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Stop once the end of the text has been reached
        if end >= text_len:
            break

        # Calculate next start with overlap
        target_start = end - chunk_overlap
        if target_start <= start:
            start = end
        else:
            # Snap target_start forward to nearest newline or space to avoid cutting words/lines
            snapped = target_start
            found_break = False
            for offset in range(min(40, end - target_start)):
                if text[target_start + offset] == "\n":
                    snapped = target_start + offset + 1
                    found_break = True
                    break
            if not found_break:
                for offset in range(min(20, end - target_start)):
                    if text[target_start + offset] in (" ", "\t"):
                        snapped = target_start + offset + 1
                        break
            start = snapped

    return chunks

def chunk_document(
    pages: List[Dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Processes extracted pages into chunks while preserving source page numbers.
    Returns:
    [
        {
            "chunk_index": 0,
            "page_number": 1,
            "content": "...",
            "token_count": 85
        }, ...
    ]
    """
    all_chunks: List[Dict[str, Any]] = []
    global_index = 0

    for page_info in pages:
        page_num = page_info.get("page_number", 1)
        raw_text = page_info.get("text", "")
        cleaned = clean_text(raw_text)

        if not cleaned:
            continue

        page_chunks = split_text_with_overlap(
            cleaned,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        for content in page_chunks:
            all_chunks.append({
                "chunk_index": global_index,
                "page_number": page_num,
                "content": content,
                "token_count": approximate_token_count(content)
            })
            global_index += 1

    return all_chunks
