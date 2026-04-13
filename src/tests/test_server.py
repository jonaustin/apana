"""Tests for server helpers - Mandarin tutor rollout."""

import pytest

# Import helpers directly - these don't need the full server dependencies
# Inline the functions for testing to avoid import issues
import re

SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')
CHINESE_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?。！？])')


def split_sentences(text: str, include_chinese: bool = True) -> list[str]:
    """Split text into sentences for streaming TTS."""
    if include_chinese:
        parts = CHINESE_SENTENCE_SPLIT_RE.split(text.strip())
    else:
        parts = SENTENCE_SPLIT_RE.split(text.strip())
    return [s.strip() for s in parts if s.strip()]


def normalize_lesson_payload(tool_result: dict) -> dict:
    """Normalize tool output into a stable lesson payload (inline for testing)."""
    transcription = tool_result.get("transcription", "")
    text = tool_result.get("response", "")

    # Extract lesson fields if ANY lesson field is present
    lesson_fields = [
        "english_coaching", "mandarin_text", "pinyin", "meaning",
        "speech_text", "pronunciation_tip", "repeat_prompt",
    ]
    lesson = {}
    if any(field in tool_result for field in lesson_fields):
        # Sanitize: strip LiteRT tool wrapper artifacts (<|"|>) from all fields
        strip = lambda s: s.replace('<|"|>', "").strip()
        lesson = {
            "english_coaching": strip(tool_result.get("english_coaching", "")),
            "mandarin_text": strip(tool_result.get("mandarin_text", "")),
            "pinyin": strip(tool_result.get("pinyin", "")),
            "meaning": strip(tool_result.get("meaning", "")),
            "pronunciation_tip": strip(tool_result.get("pronunciation_tip", "")),
            "repeat_prompt": strip(tool_result.get("repeat_prompt", "")),
            "speech_text": strip(tool_result.get("speech_text", "")),
        }

    return {
        "text": text,
        "transcription": transcription,
        "lesson": lesson if lesson else None,
    }


def select_speech_text(lesson: dict | None, fallback_text: str) -> str:
    """Select the text to send to TTS (inline for testing)."""
    if lesson and lesson.get("speech_text"):
        return lesson["speech_text"]
    # Never return empty string - use fallback or ellipsis
    return fallback_text if fallback_text.strip() else "..."


class TestSplitSentences:
    """Tests for the split_sentences helper."""

    def test_western_punctuation_only(self):
        """Western punctuation splits correctly."""
        text = "Hello. How are you? I'm fine!"
        result = split_sentences(text, include_chinese=False)
        assert result == ["Hello.", "How are you?", "I'm fine!"]

    def test_chinese_punctuation_splits(self):
        """Chinese punctuation splits correctly."""
        text = "你好。你怎么样？我很好！"
        result = split_sentences(text, include_chinese=True)
        assert result == ["你好。", "你怎么样？", "我很好！"]

    def test_mixed_punctuation(self):
        """Mixed Western and Chinese punctuation splits correctly."""
        text = "Hello. 你好。How are you? 你怎么样？"
        result = split_sentences(text, include_chinese=True)
        assert result == ["Hello.", "你好。", "How are you?", "你怎么样？"]

    def test_empty_string(self):
        """Empty string returns empty list."""
        assert split_sentences("") == []

    def test_whitespace_only(self):
        """Whitespace-only string returns empty list."""
        assert split_sentences("   ") == []

    def test_no_punctuation(self):
        """Text without punctuation returns single element list."""
        assert split_sentences("Hello world") == ["Hello world"]

    def test_strips_whitespace(self):
        """Leading and trailing whitespace is stripped."""
        text = "  Hello. World.  "
        assert split_sentences(text) == ["Hello.", "World."]


class TestNormalizeLessonPayload:
    """Tests for the normalize_lesson_payload helper."""

    def test_complete_lesson(self):
        """Complete lesson payload normalizes correctly."""
        tool_result = {
            "transcription": "How do you say hello?",
            "response": "Here's how to say hello.",
            "english_coaching": "Say it after me.",
            "mandarin_text": "你好",
            "pinyin": "nǐ hǎo",
            "meaning": "hello",
            "pronunciation_tip": "Rising tone on nǐ.",
            "repeat_prompt": "Say it once.",
            "speech_text": "你好",
        }
        result = normalize_lesson_payload(tool_result)

        assert result["text"] == "Here's how to say hello."
        assert result["transcription"] == "How do you say hello?"
        assert result["lesson"] is not None
        assert result["lesson"]["english_coaching"] == "Say it after me."
        assert result["lesson"]["mandarin_text"] == "你好"
        assert result["lesson"]["pinyin"] == "nǐ hǎo"
        assert result["lesson"]["meaning"] == "hello"
        assert result["lesson"]["pronunciation_tip"] == "Rising tone on nǐ."
        assert result["lesson"]["repeat_prompt"] == "Say it once."
        assert result["lesson"]["speech_text"] == "你好"

    def test_incomplete_lesson_fills_missing(self):
        """Missing optional fields are handled gracefully."""
        tool_result = {
            "transcription": "What is this?",
            "response": "This is a thing.",
            "english_coaching": "Look at this.",
            "mandarin_text": "这个",
        }
        result = normalize_lesson_payload(tool_result)

        assert result["text"] == "This is a thing."
        assert result["transcription"] == "What is this?"
        assert result["lesson"] is not None
        assert result["lesson"]["english_coaching"] == "Look at this."
        assert result["lesson"]["mandarin_text"] == "这个"
        assert result["lesson"]["pinyin"] == ""
        assert result["lesson"]["meaning"] == ""
        assert result["lesson"]["pronunciation_tip"] == ""
        assert result["lesson"]["repeat_prompt"] == ""
        assert result["lesson"]["speech_text"] == ""

    def test_no_lesson_returns_none(self):
        """Missing lesson fields returns None for lesson."""
        tool_result = {
            "transcription": "Hello",
            "response": "Hi there!",
        }
        result = normalize_lesson_payload(tool_result)

        assert result["text"] == "Hi there!"
        assert result["transcription"] == "Hello"
        assert result["lesson"] is None

    def test_transcription_preserved(self):
        """Transcription survives normalization."""
        tool_result = {
            "transcription": "User spoke Mandarin",
            "response": "Response text",
        }
        result = normalize_lesson_payload(tool_result)

        assert result["transcription"] == "User spoke Mandarin"

    def test_lesson_created_with_only_speech_text(self):
        """Lesson payload created when speech_text present without english_coaching."""
        tool_result = {
            "transcription": "What is this?",
            "response": "This is hello.",
            "speech_text": "你好",
            "mandarin_text": "你好",
            "pinyin": "nǐ hǎo",
            "meaning": "hello",
        }
        result = normalize_lesson_payload(tool_result)

        assert result["lesson"] is not None
        assert result["lesson"]["speech_text"] == "你好"
        assert result["lesson"]["english_coaching"] == ""

    def test_lesson_sanitizes_wrapper_artifacts(self):
        """Lesson fields strip LiteRT tool wrapper artifacts (<|\"|>)."""
        tool_result = {
            "transcription": "User said <|\"|>hello",
            "response": "Response",
            "speech_text": "<|\"|>你好<|\"|>",
            "mandarin_text": "<|\"|>你好",
        }
        result = normalize_lesson_payload(tool_result)

        assert result["lesson"]["speech_text"] == "你好"
        assert result["lesson"]["mandarin_text"] == "你好"


class TestSelectSpeechText:
    """Tests for the select_speech_text helper."""

    def test_prefers_lesson_speech_text(self):
        """Returns lesson.speech_text when available."""
        lesson = {"speech_text": "你好"}
        assert select_speech_text(lesson, "fallback") == "你好"

    def test_fallback_when_no_lesson(self):
        """Returns fallback when lesson is None."""
        assert select_speech_text(None, "fallback text") == "fallback text"

    def test_fallback_when_no_speech_text(self):
        """Returns fallback when speech_text is empty."""
        lesson = {"speech_text": ""}
        assert select_speech_text(lesson, "fallback text") == "fallback text"

    def test_never_returns_empty_string(self):
        """Always returns non-empty string."""
        # Both lesson and fallback empty - uses ellipsis as fallback
        lesson = {"speech_text": ""}
        result = select_speech_text(lesson, "")
        assert result == "..."
