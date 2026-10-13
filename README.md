# srt-subtitle-lib

Parses and serializes SubRip (.srt) subtitle files into structured records with `start`, `end`, and `text` fields. Standard library only; no dependencies.

## Usage

```python
from srt_subtitle_lib import parse, parse_file, serialize, Subtitle

srt_text = "1\n00:00:01,000 --> 00:00:02,000\nHello world\n"
cues = parse(srt_text)
for c in cues:
    print(c.index, c.start, c.end, c.text)

text = serialize(cues)
```

`parse(source: str) -> list[Subtitle]` parses an SRT string. `parse_file(path, *, encoding="utf-8")` reads and parses a file (stripping a UTF-8 BOM if present). `serialize(subtitles) -> str` writes cues back to SRT text, reindexing them 1..N.

`Subtitle` is a frozen dataclass with integer `index`, `start`, `end` (milliseconds), and `text` (internal newlines preserved, no trailing line break).

## Why

SubRip is a simple format with messy real-world files: CRLF endings, CR-only endings from old Macs, UTF-8 BOMs from Windows editors, missing index numbers, and blank padding lines. This library handles those without dragging in a dependency.

The trade-off: the parser is tolerant on input (it accepts missing indices, BOMs, and odd whitespace around timecodes) but the serializer is opinionated — it reindexes cues sequentially and writes LF line endings. If you need to preserve original indices exactly, do that in your own layer.

## Edges

- The `index` field comes verbatim from the file, including gaps and duplicates. Blocks with no index get a synthetic 1-based number. `serialize` ignores the stored index and always writes 1..N.
- Line endings are normalised to `\n` on parse; the serializer always emits `\n`.
- Empty cues (no text lines) are preserved on parse and emitted without a text line on serialize.
