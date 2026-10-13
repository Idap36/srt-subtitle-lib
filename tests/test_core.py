import io
import os
import tempfile
import unittest

from srt_subtitle_lib import SRTError, Subtitle, parse, parse_file, serialize


class ParseTests(unittest.TestCase):
    def test_single_cue(self) -> None:
        srt = "1\n00:00:01,000 --> 00:00:02,000\nHello world\n"
        cues = parse(srt)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0], Subtitle(1, 1000, 2000, "Hello world"))

    def test_multi_cue_preserves_indices(self) -> None:
        srt = (
            "1\n00:00:01,000 --> 00:00:02,000\nFirst\n\n"
            "3\n00:00:04,000 --> 00:00:05,000\nSecond\n"
        )
        cues = parse(srt)
        self.assertEqual([c.index for c in cues], [1, 3])

    def test_crlf_line_endings(self) -> None:
        srt = "1\r\n00:00:01,000 --> 00:00:02,000\r\nHello\r\n"
        cues = parse(srt)
        self.assertEqual(cues[0].text, "Hello")

    def test_cr_only_line_endings(self) -> None:
        srt = "1\r00:00:01,000 --> 00:00:02,000\rHello\r"
        cues = parse(srt)
        self.assertEqual(cues[0].text, "Hello")

    def test_multiline_text(self) -> None:
        srt = "1\n00:00:01,000 --> 00:00:02,000\nLine one\nLine two\n"
        cues = parse(srt)
        self.assertEqual(cues[0].text, "Line one\nLine two")

    def test_leading_trailing_whitespace_in_timecode(self) -> None:
        srt = "1\n  00:00:01,000 --> 00:00:02,000  \nText\n"
        cues = parse(srt)
        self.assertEqual(cues[0].start, 1000)
        self.assertEqual(cues[0].end, 2000)

    def test_hour_rollover(self) -> None:
        srt = "1\n01:02:03,004 --> 01:02:03,500\nHi\n"
        cues = parse(srt)
        self.assertEqual(cues[0].start, ((1 * 60 + 2) * 60 + 3) * 1000 + 4)
        self.assertEqual(cues[0].end, ((1 * 60 + 2) * 60 + 3) * 1000 + 500)

    def test_empty_text_allowed(self) -> None:
        srt = "1\n00:00:01,000 --> 00:00:02,000\n\n"
        cues = parse(srt)
        self.assertEqual(cues[0].text, "")

    def test_empty_string(self) -> None:
        self.assertEqual(parse(""), [])

    def test_blank_lines_ignored(self) -> None:
        srt = "\n\n1\n00:00:01,000 --> 00:00:02,000\nHi\n\n\n"
        cues = parse(srt)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "Hi")

    def test_missing_index_synthesised(self) -> None:
        srt = "00:00:01,000 --> 00:00:02,000\nHi\n"
        cues = parse(srt)
        self.assertEqual(cues[0].index, 1)
        self.assertEqual(cues[0].start, 1000)

    def test_bad_timecode(self) -> None:
        srt = "1\n00:00:01,000 -> 00:00:02,000\nHi\n"
        with self.assertRaises(SRTError):
            parse(srt)

    def test_non_string_input(self) -> None:
        with self.assertRaises(TypeError):
            parse(b"1\n00:00:01,000 --> 00:00:02,000\nHi\n")  # type: ignore[arg-type]

    def test_end_before_start(self) -> None:
        srt = "1\n00:00:02,000 --> 00:00:01,000\nHi\n"
        with self.assertRaises(SRTError):
            parse(srt)

    def test_extra_whitespace_in_arrow(self) -> None:
        srt = "1\n00:00:01,000   -->   00:00:02,000\nHi\n"
        cues = parse(srt)
        self.assertEqual(cues[0].start, 1000)


class SerializeTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        original = "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld\n"
        cues = parse(original)
        out = serialize(cues)
        self.assertEqual(parse(out), cues)

    def test_reindexes_sequentially(self) -> None:
        cues = [Subtitle(5, 1000, 2000, "A"), Subtitle(10, 3000, 4000, "B")]
        out = serialize(cues)
        self.assertTrue(out.startswith("1\n"))
        self.assertIn("\n2\n", out)

    def test_empty_text_serializes(self) -> None:
        cues = [Subtitle(1, 1000, 2000, "")]
        out = serialize(cues)
        self.assertIn("00:00:01,000 --> 00:00:02,000", out)


class FileTests(unittest.TestCase):
    def test_parse_file_strips_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.srt")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("\ufeff1\n00:00:01,000 --> 00:00:02,000\nHi\n")
            cues = parse_file(path)
            self.assertEqual(cues[0].index, 1)
            self.assertEqual(cues[0].text, "Hi")

    def test_parse_file_without_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.srt")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("1\n00:00:01,000 --> 00:00:02,000\nHi\n")
            cues = parse_file(path)
            self.assertEqual(cues[0].text, "Hi")


if __name__ == "__main__":
    unittest.main()
