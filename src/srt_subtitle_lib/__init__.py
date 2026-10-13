"""srt-subtitle-lib: parse and serialize SubRip (.srt) subtitles."""

from .core import SRTError, Subtitle, parse, parse_file, serialize

__all__ = ["SRTError", "Subtitle", "parse", "parse_file", "serialize"]

__version__ = "1.0.0"
