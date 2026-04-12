"""Benchmark: kokoro-onnx (CPU) vs mlx-audio (Apple GPU) for Kokoro TTS."""

import platform
import sys
import time
import statistics
import wave
import numpy as np

# Test sentences of varying length
SENTENCES = {
    "short": "Hello, how are you doing today?",
    "medium": "I can see you're sitting at your desk. It looks like you're working on something interesting. How can I help you today?",
    "long": (
        "That's a really great question! Let me think about this for a moment. "
        "The history of artificial intelligence goes back to the 1950s, when Alan Turing "
        "first proposed the idea of machines that could think. Since then, we've made "
        "incredible progress, from simple rule-based systems to today's large language models "
        "that can understand and generate human-like text."
    ),
}

VOICE = "af_heart"
SPEED = 1.1
WARMUP = 2
RUNS = 5

# Mandarin phrases for TTS validation
try:
    from .mandarin_phrases import MANDARIN_PHRASES, MANDARIN_TEXT_SET, MANDARIN_VOICE, MANDARIN_SPEED
except ImportError:
    # Fallback for when run as script (python benchmark_tts.py)
    from mandarin_phrases import MANDARIN_PHRASES, MANDARIN_TEXT_SET, MANDARIN_VOICE, MANDARIN_SPEED


def benchmark_kokoro_onnx(mandarin=False, output_dir=None):
    """Benchmark kokoro-onnx (ONNX Runtime, CPU)."""
    import kokoro_onnx
    from huggingface_hub import hf_hub_download

    model_path = hf_hub_download("fastrtc/kokoro-onnx", "kokoro-v1.0.onnx")
    voices_path = hf_hub_download("fastrtc/kokoro-onnx", "voices-v1.0.bin")

    print("Loading kokoro-onnx...")
    t0 = time.time()
    tts = kokoro_onnx.Kokoro(model_path, voices_path)
    print(f"  Loaded in {time.time() - t0:.2f}s")

    # Choose text set based on mode
    text_set = MANDARIN_TEXT_SET if mandarin else SENTENCES
    voice = MANDARIN_VOICE if mandarin else VOICE
    speed = MANDARIN_SPEED if mandarin else SPEED
    lang_code = "zh-cn" if mandarin else "en-us"  # 'en-us'=English, 'zh-cn'=Mandarin

    # Validate fixtures are loaded
    if mandarin and (text_set is None or len(text_set) == 0):
        raise RuntimeError("Mandarin mode requested but MANDARIN_TEXT_SET is empty. Check that mandarin_phrases.py is available.")

    results = {}
    for label, text in text_set.items():
        # Warmup
        for _ in range(WARMUP):
            tts.create(text, voice=voice, speed=speed, lang=lang_code, is_phonemes=False)

        # Timed runs
        times = []
        audio_duration = None
        pcm_sample = None
        for run_idx in range(RUNS):
            t0 = time.time()
            pcm, sr = tts.create(text, voice=voice, speed=speed, lang=lang_code, is_phonemes=False)
            elapsed = time.time() - t0
            times.append(elapsed)
            audio_duration = len(pcm) / sr
            # Save first run for output
            if run_idx == 0:
                pcm_sample = (pcm, sr)

        # Save audio file for Mandarin mode
        if mandarin and output_dir and pcm_sample:
            pcm, sr = pcm_sample
            import os
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"kokoro-onnx-{label}.wav")
            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sr)
                wf.writeframes((pcm * 32767).astype(np.int16).tobytes())
            print(f"  Saved: {output_path}")

        results[label] = {
            "times": times,
            "mean": statistics.mean(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "audio_sec": audio_duration,
            "rtf": statistics.mean(times) / audio_duration,
            "sample_rate": sr,
        }

    return results


def benchmark_mlx_audio(mandarin=False, output_dir=None):
    """Benchmark mlx-audio (MLX, Apple GPU)."""
    from mlx_audio.tts.generate import load_model

    print("Loading mlx-audio...")
    t0 = time.time()
    model = load_model("mlx-community/Kokoro-82M-bf16")
    sr = model.sample_rate
    # Warmup to trigger pipeline init
    warmup_text = "Hello" if not mandarin else "你好"
    warmup_voice = VOICE if not mandarin else MANDARIN_VOICE
    warmup_speed = SPEED if not mandarin else MANDARIN_SPEED
    warmup_lang = "a" if not mandarin else "z"  # 'a'=English, 'z'=Mandarin
    list(model.generate(text=warmup_text, voice=warmup_voice, speed=warmup_speed, lang_code=warmup_lang))
    print(f"  Loaded in {time.time() - t0:.2f}s (sample_rate={sr})")

    # Choose text set based on mode
    text_set = MANDARIN_TEXT_SET if mandarin else SENTENCES
    voice = MANDARIN_VOICE if mandarin else VOICE
    speed = MANDARIN_SPEED if mandarin else SPEED
    lang_code = "z" if mandarin else "a"  # 'a'=English, 'z'=Mandarin

    # Validate fixtures are loaded
    if mandarin and (text_set is None or len(text_set) == 0):
        raise RuntimeError("Mandarin mode requested but MANDARIN_TEXT_SET is empty. Check that mandarin_phrases.py is available.")

    results = {}
    for label, text in text_set.items():
        # Warmup
        for _ in range(WARMUP):
            list(model.generate(text=text, voice=voice, speed=speed, lang_code=lang_code))

        # Timed runs
        times = []
        audio_duration = None
        pcm_sample = None
        for run_idx in range(RUNS):
            t0 = time.time()
            gen_results = list(model.generate(text=text, voice=voice, speed=speed, lang_code=lang_code))
            elapsed = time.time() - t0
            times.append(elapsed)

            # Check for empty output (Issue 3: guard against no audio)
            if not gen_results:
                raise RuntimeError(f"Backend produced no audio for label='{label}', voice='{voice}'. TTS backend may be misconfigured.")

            pcm = np.concatenate([np.array(r.audio) for r in gen_results])
            audio_duration = len(pcm) / sr
            # Save first run for output
            if run_idx == 0:
                pcm_sample = (pcm, sr)

        # Save audio file for Mandarin mode
        if mandarin and output_dir and pcm_sample:
            pcm, sr = pcm_sample
            import os
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"mlx-audio-{label}.wav")
            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sr)
                wf.writeframes((pcm * 32767).astype(np.int16).tobytes())
            print(f"  Saved: {output_path}")

        results[label] = {
            "times": times,
            "mean": statistics.mean(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "audio_sec": audio_duration,
            "rtf": statistics.mean(times) / audio_duration,
            "sample_rate": sr,
        }

    return results


def benchmark_mlx_audio_streaming(mandarin=False):
    """Benchmark mlx-audio streaming: time-to-first-chunk on long text."""
    from mlx_audio.tts.generate import load_model

    print("\nBenchmarking mlx-audio streaming (time-to-first-chunk)...")
    model = load_model("mlx-community/Kokoro-82M-bf16")

    # Warmup
    warmup_text = "Hello" if not mandarin else "你好"
    warmup_voice = VOICE if not mandarin else MANDARIN_VOICE
    warmup_speed = SPEED if not mandarin else MANDARIN_SPEED
    warmup_lang = "a" if not mandarin else "z"  # 'a'=English, 'z'=Mandarin
    list(model.generate(text=warmup_text, voice=warmup_voice, speed=warmup_speed, lang_code=warmup_lang))

    # Choose text set based on mode
    text_set = MANDARIN_TEXT_SET if mandarin else SENTENCES
    voice = MANDARIN_VOICE if mandarin else VOICE
    speed = MANDARIN_SPEED if mandarin else SPEED
    lang_code = "z" if mandarin else "a"  # 'a'=English, 'z'=Mandarin

    # Validate fixtures are loaded
    if mandarin and (text_set is None or len(text_set) == 0):
        raise RuntimeError("Mandarin mode requested but MANDARIN_TEXT_SET is empty. Check that mandarin_phrases.py is available.")

    results = {}
    for label, text in text_set.items():
        # Warmup streaming
        for _ in range(WARMUP):
            first_chunk = next(model.generate(text=text, voice=voice, speed=speed, stream=True, streaming_interval=1.0, lang_code=lang_code), None)
            if first_chunk is None and mandarin:
                raise RuntimeError(f"Streaming backend produced no chunks for label='{label}', voice='{voice}'.")

        ttfc_times = []
        total_times = []
        chunk_counts = []
        for _ in range(RUNS):
            t0 = time.time()
            first = True
            n_chunks = 0
            for r in model.generate(text=text, voice=voice, speed=speed, stream=True, streaming_interval=1.0, lang_code=lang_code):
                if first:
                    ttfc_times.append(time.time() - t0)
                    first = False
                n_chunks += 1

            # Check for empty streaming output (Issue 3)
            if n_chunks == 0 and mandarin:
                raise RuntimeError(f"Streaming backend produced no chunks for label='{label}', voice='{voice}'.")

            total_times.append(time.time() - t0)
            chunk_counts.append(n_chunks)

        results[label] = {
            "ttfc_mean": statistics.mean(ttfc_times),
            "ttfc_min": min(ttfc_times),
            "total_mean": statistics.mean(total_times),
            "chunks": statistics.mean(chunk_counts),
        }

    return results


def print_results(name, results, text_set=None, phrases=None):
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    for label, r in results.items():
        # Determine text and optional metadata
        if text_set and label in text_set:
            text = text_set[label]
            # Try to find metadata from MANDARIN_PHRASES (Issue 4: key mismatch fix)
            pinyin = ""
            meaning = ""
            if phrases:
                for phrase_key, phrase_data in phrases.items():
                    # Check if this phrase's text matches the current label's text
                    if phrase_data.get("text") == text:
                        pinyin = phrase_data.get("pinyin", "")
                        meaning = phrase_data.get("meaning", "")
                        break
            print(f"\n  [{label}] ({text})")
            if pinyin:
                print(f"    Pinyin: {pinyin}")
            if meaning:
                print(f"    Meaning: {meaning}")
        else:
            text = SENTENCES.get(label, "")
            print(f"\n  [{label}] ({len(text)} chars)")
        print(f"    Mean:   {r['mean']*1000:7.1f} ms  (+/-{r['stdev']*1000:.1f})")
        print(f"    Min:    {r['min']*1000:7.1f} ms")
        print(f"    Audio:  {r['audio_sec']:7.2f} s")
        print(f"    RTF:    {r['rtf']:7.3f}x  (< 1.0 = faster than real-time)")
        print(f"    SR:     {r['sample_rate']} Hz")


def print_streaming_results(results, text_set=None):
    print(f"\n{'=' * 60}")
    print(f"  mlx-audio: Streaming Mode")
    print(f"{'=' * 60}")
    for label, r in results.items():
        if text_set and label in text_set:
            text = text_set[label]
            print(f"\n  [{label}] ({text})")
        else:
            text = SENTENCES.get(label, "")
            print(f"\n  [{label}] ({len(text)} chars)")
        print(f"    TTFC Mean:  {r['ttfc_mean']*1000:7.1f} ms")
        print(f"    TTFC Min:   {r['ttfc_min']*1000:7.1f} ms")
        print(f"    Total Mean: {r['total_mean']*1000:7.1f} ms")
        print(f"    Chunks:     {r['chunks']:.1f}")


if __name__ == "__main__":
    is_apple = sys.platform == "darwin" and platform.machine() == "arm64"
    mandarin = "--mandarin" in sys.argv
    output_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]

    print("=" * 60)
    if is_apple:
        print("  TTS Benchmark: kokoro-onnx vs mlx-audio")
    else:
        print("  TTS Benchmark: kokoro-onnx")

    if mandarin:
        print("  Mode: MANDARIN PHRASES")
        print(f"  Voice: {MANDARIN_VOICE}, Speed: {MANDARIN_SPEED}")
    else:
        print("  Mode: ENGLISH PHRASES")

    if output_dir:
        print(f"  Output directory: {output_dir}")

    print(f"  Warmup: {WARMUP} runs, Measured: {RUNS} runs")
    print("=" * 60)

    text_set = MANDARIN_TEXT_SET if mandarin else None

    onnx_results = benchmark_kokoro_onnx(mandarin=mandarin, output_dir=output_dir)
    print_results("kokoro-onnx (ONNX Runtime, CPU)", onnx_results, text_set=text_set, phrases=MANDARIN_PHRASES)

    if is_apple:
        mlx_results = benchmark_mlx_audio(mandarin=mandarin, output_dir=output_dir)
        print_results("mlx-audio (MLX, Apple GPU)", mlx_results, text_set=text_set, phrases=MANDARIN_PHRASES)

        streaming_results = benchmark_mlx_audio_streaming(mandarin=mandarin)
        print_streaming_results(streaming_results, text_set=text_set)

        # Comparison
        print(f"\n{'=' * 60}")
        print(f"  Comparison: speedup of mlx-audio over kokoro-onnx")
        print(f"{'=' * 60}")
        for label in (text_set or SENTENCES):
            onnx_mean = onnx_results[label]["mean"]
            mlx_mean = mlx_results[label]["mean"]
            speedup = onnx_mean / mlx_mean
            print(f"  [{label}]  {onnx_mean*1000:.0f}ms -> {mlx_mean*1000:.0f}ms  ({speedup:.2f}x {'faster' if speedup > 1 else 'slower'})")

        # Go/No-Go Gate for Mandarin
        if mandarin:
            print(f"\n{'=' * 60}")
            print(f"  MANDARIN TTS VALIDATION: GO/NO-GO GATE")
            print(f"{'=' * 60}")
            if output_dir:
                print(f"\nAudio files saved to: {output_dir}")
                print("\nManual Listening Check Required:")
                print("  1. Listen to the generated Mandarin audio files")
                print("  2. Verify: phrases are intelligible to a Mandarin speaker/learner")
                print("  3. Verify: pace is slow enough for beginner repetition")
                print("  4. Verify: no obviously misleading English accent")
            else:
                print("\nNo audio files saved (use --output <dir> to save).")
                print("To validate, run: python src/benchmarks/benchmark_tts.py --mandarin --output /tmp/tts-validation")
            print("\n  PASS criteria: All conditions above are met")
            print("  If PASS: Continue with Mandarin teacher MVP rollout")
            print("  If FAIL: Document blocker, consider alternative TTS backend")
