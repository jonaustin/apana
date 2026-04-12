"""Tests for mandarin_phrases fixtures."""

import pytest
from benchmarks.mandarin_phrases import (
    MANDARIN_PHRASES,
    MANDARIN_TEXT_SET,
    MANDARIN_VOICE,
    MANDARIN_SPEED,
)


class TestMandarinTextSet:
    """Tests for MANDARIN_TEXT_SET fixture."""

    def test_keys_match_expected(self):
        """Test MANDARIN_TEXT_SET has expected keys."""
        expected_keys = {"short", "medium", "long"}
        assert set(MANDARIN_TEXT_SET.keys()) == expected_keys

    def test_all_values_are_non_empty_strings(self):
        """Test all values are non-empty strings."""
        for label, text in MANDARIN_TEXT_SET.items():
            assert isinstance(text, str), f"Text for {label} is not a string"
            assert len(text) > 0, f"Text for {label} is empty"

    def test_no_literal_ellipsis(self):
        """Test no text contains literal '...' that TTS would pronounce as 'dot dot dot'."""
        for label, text in MANDARIN_TEXT_SET.items():
            assert "..." not in text, f"Text for {label} contains literal ellipsis: {text!r}"


class TestMandarinPhrases:
    """Tests for MANDARIN_PHRASES fixture."""

    def test_all_entries_have_required_keys(self):
        """Test all entries have text, pinyin, meaning keys."""
        required_keys = {"text", "pinyin", "meaning"}
        for phrase_key, phrase_data in MANDARIN_PHRASES.items():
            assert set(phrase_data.keys()) == required_keys, (
                f"Phrase {phrase_key} missing required keys. "
                f"Got: {set(phrase_data.keys())}, expected: {required_keys}"
            )

    def test_all_texts_are_non_empty_strings(self):
        """Test all text values are non-empty strings."""
        for phrase_key, phrase_data in MANDARIN_PHRASES.items():
            text = phrase_data["text"]
            assert isinstance(text, str), f"Text for {phrase_key} is not a string"
            assert len(text) > 0, f"Text for {phrase_key} is empty"

    def test_no_phrase_contains_literal_ellipsis(self):
        """Test no phrase text contains literal '...'."""
        for phrase_key, phrase_data in MANDARIN_PHRASES.items():
            text = phrase_data["text"]
            assert "..." not in text, (
                f"Phrase {phrase_key} contains literal ellipsis: {text!r}"
            )


class TestMetadataLookup:
    """Tests validating metadata lookup works correctly."""

    def test_short_text_matches_phrase(self):
        """Test MANDARIN_TEXT_SET['short'] text appears in MANDARIN_PHRASES."""
        short_text = MANDARIN_TEXT_SET["short"]
        found = any(
            phrase_data["text"] == short_text
            for phrase_data in MANDARIN_PHRASES.values()
        )
        assert found, f"Short text {short_text!r} not found in MANDARIN_PHRASES"

    def test_medium_long_are_composite(self):
        """Test medium/long texts are composite (don't need exact match).

        These are combinations of multiple phrases, so they won't match any
        single phrase entry exactly. This is expected behavior.
        """
        medium_text = MANDARIN_TEXT_SET["medium"]
        long_text = MANDARIN_TEXT_SET["long"]

        # Verify they contain characters from multiple phrases
        phrase_texts = [p["text"] for p in MANDARIN_PHRASES.values()]

        # medium should contain at least 2 phrase texts
        medium_matches = sum(1 for pt in phrase_texts if pt in medium_text)
        assert medium_matches >= 2, (
            f"Medium text {medium_text!r} should contain at least 2 phrases, "
            f"found {medium_matches}"
        )

        # long should contain at least 3 phrase texts
        long_matches = sum(1 for pt in phrase_texts if pt in long_text)
        assert long_matches >= 3, (
            f"Long text {long_text!r} should contain at least 3 phrases, "
            f"found {long_matches}"
        )


class TestMandarinVoiceAndSpeed:
    """Tests for voice and speed settings."""

    def test_voice_is_non_empty_string(self):
        """Test MANDARIN_VOICE is a non-empty string."""
        assert isinstance(MANDARIN_VOICE, str)
        assert len(MANDARIN_VOICE) > 0

    def test_speed_is_valid_range(self):
        """Test MANDARIN_SPEED is in reasonable range for TTS."""
        assert isinstance(MANDARIN_SPEED, (int, float))
        assert 0.5 <= MANDARIN_SPEED <= 2.0, (
            f"Speed {MANDARIN_SPEED} outside valid range [0.5, 2.0]"
        )
