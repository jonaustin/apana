"""Parlor — on-device, real-time multimodal AI (voice + vision)."""

import asyncio
import base64
import json
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

import litert_lm
import numpy as np
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

import tts

HF_REPO = "litert-community/gemma-4-E2B-it-litert-lm"
HF_FILENAME = "gemma-4-E2B-it.litertlm"


def resolve_model_path() -> str:
    path = os.environ.get("MODEL_PATH", "")
    if path:
        return path
    from huggingface_hub import hf_hub_download
    print(f"Downloading {HF_REPO}/{HF_FILENAME} (first run only)...")
    return hf_hub_download(repo_id=HF_REPO, filename=HF_FILENAME)


MODEL_PATH = resolve_model_path()
SYSTEM_PROMPT = (
    "You are a beginner Mandarin tutor teaching English-speaking users. "
    "The user is talking to you through a microphone and showing you their camera. "
    "You MUST always use the respond_to_user tool to reply every turn. "
    "Your rules: stay mostly in English, teach at most one or two new Mandarin items per turn, "
    "always include pinyin for new Mandarin text, prefer short repeatable examples, "
    "ask the learner to repeat often, and avoid claiming precise pronunciation scoring. "
    "Use this exact format: transcription='what the user said', response='your response', "
    "english_coaching='brief English instruction', mandarin_text='Mandarin characters', "
    "pinyin='romanized pinyin', meaning='gloss in English', speech_text='exact text for TTS'."
)

SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')
CHINESE_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?。！？])')

# Mandarin TTS settings (validated in benchmarks/benchmark_tts.py)
MANDARIN_VOICE = os.environ.get("TTS_VOICE", "zf_xiaoyi")
MANDARIN_SPEED = float(os.environ.get("TTS_SPEED", "0.9"))
DEFAULT_VOICE = "af_heart"
DEFAULT_SPEED = 1.1


def _has_chinese(text: str) -> bool:
    """Return True if text contains any CJK Unified Ideographs."""
    return bool(re.search(r'[\u4e00-\u9fff]', text))

engine = None
tts_backend = None


def load_models():
    global engine, tts_backend
    print(f"Loading Gemma 4 E2B from {MODEL_PATH}...")
    engine = litert_lm.Engine(
        MODEL_PATH,
        backend=litert_lm.Backend.GPU,
        vision_backend=litert_lm.Backend.GPU,
        audio_backend=litert_lm.Backend.CPU,
    )
    engine.__enter__()
    print("Engine loaded.")

    tts_backend = tts.load()


@asynccontextmanager
async def lifespan(app):
    await asyncio.get_event_loop().run_in_executor(None, load_models)
    yield


app = FastAPI(lifespan=lifespan)


def split_sentences(text: str, include_chinese: bool = True) -> list[str]:
    """Split text into sentences for streaming TTS.

    Args:
        text: Text to split into sentences.
        include_chinese: If True, also split on Chinese punctuation (.!?).

    Returns:
        List of sentence strings, stripped of whitespace.
    """
    if include_chinese:
        # Split on both Western and Chinese punctuation
        parts = CHINESE_SENTENCE_SPLIT_RE.split(text.strip())
    else:
        parts = SENTENCE_SPLIT_RE.split(text.strip())
    return [s.strip() for s in parts if s.strip()]


def normalize_lesson_payload(tool_result: dict) -> dict:
    """Normalize tool output into a stable lesson payload.

    Args:
        tool_result: Raw tool result dict with transcription, response, and optional lesson fields.

    Returns:
        Normalized dict with text, transcription, and lesson keys.
    """
    # Extract base fields
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
    """Select the text to send to TTS.

    Args:
        lesson: Normalized lesson payload (may be None).
        fallback_text: Fallback text if no lesson or speech_text.

    Returns:
        Text string to send to TTS. Never returns empty string.
    """
    if lesson and lesson.get("speech_text"):
        return lesson["speech_text"]
    # Always return non-empty string - fallback_text guaranteed non-empty by caller
    return fallback_text if fallback_text.strip() else "..."


@app.get("/")
async def root():
    return HTMLResponse(content=(Path(__file__).parent / "index.html").read_text())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    # Per-connection tool state captured via closure
    tool_result = {}

    def respond_to_user(
        transcription: str,
        response: str,
        english_coaching: str = "",
        mandarin_text: str = "",
        pinyin: str = "",
        meaning: str = "",
        pronunciation_tip: str = "",
        repeat_prompt: str = "",
        speech_text: str = "",
    ) -> str:
        """Respond to the user's voice message.

        Args:
            transcription: Exact transcription of what the user said in the audio.
            response: Your conversational response to the user. Keep it to 1-4 short sentences.
            english_coaching: Brief English instruction or encouragement.
            mandarin_text: The Mandarin characters to learn.
            pinyin: Romanized pinyin for the Mandarin text.
            meaning: Gloss in English.
            pronunciation_tip: Optional pronunciation guidance.
            repeat_prompt: Optional prompt to repeat the phrase.
            speech_text: Exact text to send to TTS.
        """
        tool_result["transcription"] = transcription
        tool_result["response"] = response
        if english_coaching:
            tool_result["english_coaching"] = english_coaching
        if mandarin_text:
            tool_result["mandarin_text"] = mandarin_text
        if pinyin:
            tool_result["pinyin"] = pinyin
        if meaning:
            tool_result["meaning"] = meaning
        if pronunciation_tip:
            tool_result["pronunciation_tip"] = pronunciation_tip
        if repeat_prompt:
            tool_result["repeat_prompt"] = repeat_prompt
        if speech_text:
            tool_result["speech_text"] = speech_text
        return "OK"

    conversation = engine.create_conversation(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}],
        tools=[respond_to_user],
    )
    conversation.__enter__()

    interrupted = asyncio.Event()
    msg_queue = asyncio.Queue()

    async def receiver():
        """Receive messages from WebSocket and route them."""
        try:
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                if msg.get("type") == "interrupt":
                    interrupted.set()
                    print("Client interrupted")
                else:
                    await msg_queue.put(msg)
        except WebSocketDisconnect:
            await msg_queue.put(None)

    recv_task = asyncio.create_task(receiver())

    try:
        while True:
            msg = await msg_queue.get()
            if msg is None:
                break

            interrupted.clear()

            content = []
            if msg.get("audio"):
                content.append({"type": "audio", "blob": msg["audio"]})
            if msg.get("image"):
                content.append({"type": "image", "blob": msg["image"]})

            if msg.get("audio") and msg.get("image"):
                content.append({"type": "text", "text": "The user just spoke to you (audio) while showing their camera (image). Respond to what they said, referencing what you see if relevant."})
            elif msg.get("audio"):
                content.append({"type": "text", "text": "The user just spoke to you. Respond to what they said."})
            elif msg.get("image"):
                content.append({"type": "text", "text": "The user is showing you their camera. Describe what you see."})
            else:
                content.append({"type": "text", "text": msg.get("text", "Hello!")})

            # LLM inference
            t0 = time.time()
            tool_result.clear()
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: conversation.send_message({"role": "user", "content": content})
            )
            llm_time = time.time() - t0

            # Extract response from tool call or fallback to raw text
            if tool_result:
                strip = lambda s: s.replace('<|"|>', "").strip()
                transcription = strip(tool_result.get("transcription", ""))
                text_response = strip(tool_result.get("response", ""))
                print(f"LLM ({llm_time:.2f}s) [tool] heard: {transcription!r} → {text_response}")
            else:
                # No tool call: for text-only input, use the incoming text as transcription
                strip = lambda s: s.replace('<|"|>', "").strip()
                text_response = strip(response["content"][0].get("text", ""))
                if msg.get("text"):
                    transcription = strip(msg.get("text", ""))
                else:
                    transcription = None
                print(f"LLM ({llm_time:.2f}s) [no tool]: {text_response}")

            if interrupted.is_set():
                print("Interrupted after LLM, skipping response")
                continue

            # Normalize the tool output into a lesson payload
            normalized = normalize_lesson_payload(tool_result)
            lesson = normalized.get("lesson")

            # Build the WebSocket reply with optional lesson payload
            reply = {"type": "text", "text": text_response, "llm_time": round(llm_time, 2)}
            if transcription:
                reply["transcription"] = transcription
            if lesson:
                reply["lesson"] = lesson
            await ws.send_text(json.dumps(reply))

            if interrupted.is_set():
                print("Interrupted before TTS, skipping audio")
                continue

            # Select the text for TTS: prefer lesson.speech_text, fallback to text_response
            speech_text = select_speech_text(lesson, text_response)

            # Streaming TTS: split into sentences and send chunks progressively
            sentences = split_sentences(speech_text)
            if not sentences:
                sentences = [speech_text]

            tts_start = time.time()

            # Signal start of audio stream
            await ws.send_text(json.dumps({
                "type": "audio_start",
                "sample_rate": tts_backend.sample_rate,
                "sentence_count": len(sentences),
            }))

            for i, sentence in enumerate(sentences):
                if interrupted.is_set():
                    print(f"Interrupted during TTS (sentence {i+1}/{len(sentences)})")
                    break

                # Generate audio for this sentence
                pcm = await asyncio.get_event_loop().run_in_executor(
                    None, lambda s=sentence: tts_backend.generate(
                        s,
                        voice=MANDARIN_VOICE if _has_chinese(s) else DEFAULT_VOICE,
                        speed=MANDARIN_SPEED if _has_chinese(s) else DEFAULT_SPEED,
                    )
                )

                if interrupted.is_set():
                    break

                # Convert to 16-bit PCM and send as base64
                pcm_int16 = (pcm * 32767).clip(-32768, 32767).astype(np.int16)
                await ws.send_text(json.dumps({
                    "type": "audio_chunk",
                    "audio": base64.b64encode(pcm_int16.tobytes()).decode(),
                    "index": i,
                }))

            tts_time = time.time() - tts_start
            print(f"TTS ({tts_time:.2f}s): {len(sentences)} sentences")

            if not interrupted.is_set():
                await ws.send_text(json.dumps({
                    "type": "audio_end",
                    "tts_time": round(tts_time, 2),
                }))

    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        recv_task.cancel()
        conversation.__exit__(None, None, None)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
