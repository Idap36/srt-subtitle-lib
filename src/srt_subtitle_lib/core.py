import io
import re
from dataclasses import dataclass


_TIMESTAMP_RE = (
    r"(\d{1,2}):(\d{2}):(\d{2}),(\d{3})"
)

_TIMECODE_RE = re.compile(
    r"^\s*" + _TIMESTAMP_RE + r"\s*-->\s*" + _TIMESTAMP_RE + r"\s*$"
)


class SRTError(ValueError):
    """Raised when an SRT stream cannot be parsed."""


@dataclass(frozen=True)
class Subtitle:
    """A single SubRip cue.

    Start and end are integer milliseconds from the beginning of the file.
    Text keeps its internal newlines but never has a leading or trailing
    line separator.  Empty cues (no text lines) are permitted on output
    so round-tripping preserves them.
    """

    index: int
    start: int
    end: int
    text: str

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("start must be non-negative")
        if self.end < 0:
            raise ValueError("end must be non-negative")
        if self.end < self.start:
            raise ValueError("end is before start")


def _parse_timestamp(h: str, m: str, s: str, ms: str) -> int:
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)


def _format_timestamp(total_ms: int) -> str:
    if total_ms < 0:
        raise ValueError("timestamp must be non-negative")
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _split_blocks(lines: list[str]) -> list[list[str]]:
    """Split top-level lines into blank-line-delimited blocks.

    We normalise CRLF to \n first (see parse), so we only split on \n here.
    Leading and trailing blank lines are stripped so empty files and
    files with a trailing newline still behave.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _parse_block(lines: list[str]) -> Subtitle:
    if not lines:
        raise SRTError("empty block")

    cursor = 0

    # Index is optional; tolerate blocks that begin straight with the
    # timecode. Real .srt files always have it, but being permissive here
    # costs nothing and catches hand-edited files.
    index: int
    match = _TIMECODE_RE.match(lines[cursor])
    if match is None:
        try:
            index = int(lines[cursor].strip())
        except ValueError as exc:
            raise SRTError(
                f"expected index or timecode, got {lines[0]!r}"
            ) from exc
        cursor += 1
        if cursor >= len(lines):
            raise SRTError("block ends after index; missing timecode")
        match = _TIMECODE_RE.match(lines[cursor])
    else:
        index = 0

    if match is None:
        raise SRTError(f"bad timecode line: {lines[cursor]!r}")

    start = _parse_timestamp(*match.group(1, 2, 3, 4))
    end = _parse_timestamp(*match.group(5, 6, 7, 8))
    cursor += 1

    text = "\n".join(lines[cursor:])

    try:
        return Subtitle(index=index, start=start, end=end, text=text)
    except ValueError as exc:
        raise SRTError(str(exc)) from exc


def parse(source: str) -> list[Subtitle]:
    """Parse SRT-formatted text into a list of :class:`Subtitle` records.

    The index field is taken verbatim from the file when present; gaps and
    duplicates are preserved.  When a block omits the index entirely we
    assign a synthetic 1-based index based on block order so the field is
    always a positive int.
    """
    if not isinstance(source, str):
        raise TypeError("parse expects str; use parse_file for files")

    normalised = source.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalised.split("\n")
    blocks = _split_blocks(lines)

    results: list[Subtitle] = []
    synthetic = 0
    for block in blocks:
        subtitle = _parse_block(block)
        if subtitle.index == 0:
            synthetic += 1
            subtitle = Subtitle(
                index=synthetic,
                start=subtitle.start,
                end=subtitle.end,
                text=subtitle.text,
            )
        else:
            synthetic = subtitle.index
        results.append(subtitle)
    return results


def parse_file(path: str, *, encoding: str = "utf-8") -> list[Subtitle]:
    """Read and parse the SRT file at *path*.

    A BOM, if present on a UTF-8 file, is silently stripped because some
    Windows editors emit it and it corrupts the first index line.
    """
    with open(path, "r", encoding=encoding, newline="") as handle:
        data = handle.read()
    if encoding.lower().replace("-", "_") in ("utf_8", "utf8") and data.startswith("\ufeff"):
        data = data[1:]
    return parse(data)


def serialize(subtitles: list[Subtitle]) -> str:
    """Serialize subtitles back to SRT text.

    Reindexes cues 1..N in output order; callers wanting to preserve
    original indices should do so in their own layer.
    """
    parts: list[str] = []
    for i, sub in enumerate(subtitles, start=1):
        parts.append(str(i))
        parts.append(
            f"{_format_timestamp(sub.start)} --> {_format_timestamp(sub.end)}"
        )
        if sub.text:
            parts.append(sub.text)
        parts.append("")
    return "\n".join(parts)


# Kept as an alias so tests that pass a file-like object work seamlessly.
def parse_io(source: io.TextIOBase) -> list[Subtitle]:
    return parse(source.read())

__all__ = ["SRTError", "Subtitle", "parse", "parse_file", "parse_io", "serialize"]
