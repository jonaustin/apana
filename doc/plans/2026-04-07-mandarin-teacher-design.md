# Mandarin Teacher MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Purpose:** Teach beginner Mandarin to English-speaking users through short spoken examples with pinyin and translation, entirely on-device.

**Goal:** Turn Parlor into a good beginner Mandarin tutor MVP that stays on-device, teaches a small amount of Mandarin at a time, and provides trustworthy spoken examples with clear on-screen coaching.

**Architecture:** Keep the current FastAPI WebSocket loop, Gemma conversation engine, and browser VAD/playback flow. Add a structured lesson payload on top of the existing `text` message contract, choose one credible local Mandarin speech path, and keep the frontend compatible with plain-text fallback while rendering a richer lesson card when structured fields are present.

**Tech Stack:** FastAPI, LiteRT-LM / Gemma 4 E2B, local TTS via `src/tts.py`, browser VAD, plain HTML/CSS/JS frontend, `pytest` for new backend tests, existing benchmark scripts under `src/benchmarks/`

## MVP Product Decision

This MVP should optimize for one thing: a beginner can ask a question, hear a short Mandarin example, see the exact phrase with pinyin and meaning, and be prompted to repeat it.

For MVP, do this well and defer the rest.

### In Scope

- Beginner-safe tutor prompt that stays mostly in English
- One or two Mandarin phrases per turn
- Structured lesson output for the frontend
- Pinyin, meaning, and short pronunciation guidance
- Spoken Mandarin example using a local TTS path
- Chinese punctuation support in streamed playback
- Plain-text fallback if structured output is missing

### Explicitly Out of Scope for MVP

- Automatic pronunciation scoring
- Tone-level grading of the learner's speech
- Spaced repetition or saved lesson history
- Full curriculum planning
- Multi-voice or multi-backend speech settings UI
- Heavy frontend redesign beyond the transcript card treatment

### Important Constraint

The current stack does not provide a trustworthy Mandarin pronunciation grader. For MVP, the app should ask the learner to repeat, show the best-effort transcription, and coach gently, but it must not pretend to reliably score tones or mouth position from the learner's audio.

## Current Codebase

The implementation should stay close to the current file boundaries:

- `src/server.py`: system prompt, tool call contract, WebSocket payloads, TTS streaming
- `src/tts.py`: local speech backend loading and voice selection
- `src/index.html`: transcript rendering, playback state, interrupt handling
- `src/benchmarks/benchmark_tts.py`: current TTS benchmark entry point
- `src/benchmarks/bench.py`: end-to-end WebSocket benchmark

There is no automated test suite yet. MVP work should add a small `pytest` harness for backend helpers and payload normalization instead of introducing a full frontend test stack.

## Target Behavior

Each assistant turn should still send a top-level WebSocket message with `type: "text"` and `text` so the app remains backward compatible.

When lesson data is available, the same message should also include:

- `transcription`: best-effort transcription of what the user said
- `lesson`: object with structured tutor fields

Recommended MVP `lesson` schema:

- `english_coaching`: one or two short English sentences
- `mandarin_text`: exact Mandarin phrase to say
- `pinyin`: pinyin for `mandarin_text`
- `meaning`: concise English gloss
- `pronunciation_tip`: optional plain-English tip
- `repeat_prompt`: optional short instruction such as "Say it once slowly."
- `speech_text`: exact text to send to TTS

Rules:

- Keep `text` as a compact fallback summary for old clients and debugging.
- Keep `transcription` top-level so the current user-bubble replacement flow survives.
- Use `speech_text` for TTS. Do not speak the full English coaching paragraph.
- If the model fails to produce a valid `lesson`, fall back to the existing plain-text path.

## TTS MVP Strategy

Do not over-engineer the speech layer up front. The first decision is whether the current local stack can produce Mandarin audio that is good enough for a beginner tutor.

### Go / No-Go Gate

Before doing deeper UI work, test a small local phrase set such as:

- `ni hao`
- `xie xie`
- `zai jian`
- `wo jiao ...`
- `qing zai shuo yi ci`

Use actual characters in the benchmark fixture, not only pinyin.

Pass criteria:

- A Mandarin speaker or strong learner can understand the phrase without guessing
- The pace is slow enough for repetition
- The audio does not sound obviously English-accented to the point of being misleading

If the current Kokoro-based path passes, keep the implementation simple:

- expose voice and speed via environment variables in `src/tts.py`
- document the chosen Mandarin-capable voice
- reuse the existing backend abstraction

If it fails, then and only then add a second fully local backend behind `src/tts.py`. Do not do a general speech-plugin refactor unless the benchmark forces it.

## Frontend MVP Strategy

The frontend should stay visually compact. The MVP UI change is a structured assistant lesson card inside the existing transcript column.

Each lesson card should show:

- coaching text in English
- Mandarin phrase
- pinyin
- meaning
- optional pronunciation tip
- optional repeat prompt

Implementation rules:

- Render model strings with DOM text nodes or `textContent`, not `innerHTML`
- Preserve the current plain assistant bubble path for fallback
- Preserve the current transcription replacement flow for the temporary user bubble
- Keep the rest of the shell, camera view, waveform, and controls intact

## Backend MVP Strategy

The backend should remain the backbone of the product. Keep the message flow simple:

1. User audio arrives
2. Model responds through the tool call when possible
3. Server normalizes tool output into:
   - top-level `text`
   - top-level `transcription`
   - optional `lesson`
   - chosen `speech_text`
4. Frontend renders the lesson card if present
5. TTS streams `speech_text`, split with both Western and Chinese punctuation

MVP response-writing rules for the system prompt:

- stay mostly in English
- introduce at most one or two new Mandarin items per turn
- always include pinyin for new Mandarin text
- prefer short, repeatable examples
- ask the learner to repeat often
- avoid claiming precise pronunciation scoring
- keep spoken output short

## Testing Strategy

Use a mix of small automated tests and deliberate manual checks.

### Automated

Add `pytest` and cover only server-side behavior that is stable and cheap to test.

Test targets:

- sentence splitting includes `。`, `！`, and `？`
- lesson payload normalization handles missing optional fields
- top-level `transcription` survives structured lesson responses
- fallback behavior still works when tool output is incomplete
- `speech_text` selection prefers the lesson field and falls back to plain text safely

### Manual

Manual checks are required for:

- Mandarin TTS quality
- transcript card readability
- barge-in during streamed Mandarin playback
- real end-to-end latency on the local machine

Use:

- `cd src && uv run python benchmarks/benchmark_tts.py`
- `cd src && uv run python benchmarks/bench.py`
- `cd src && uv run python server.py`

## Acceptance Criteria

The MVP is ready when all of the following are true:

- A user can ask for a beginner Mandarin phrase and receive a short lesson card
- New Mandarin text always includes pinyin and meaning
- TTS speaks the Mandarin example, not the full English explanation
- The app still works when the model returns plain text only
- User transcription still appears in the transcript flow
- Chinese punctuation does not break sentence-level streaming
- Manual listening confirms the chosen local voice is good enough to teach the included phrases

## Implementation Tasks

### Task 1: Add a Minimal Test Harness and Helper Boundaries

**Files:**
- Modify: `src/pyproject.toml`
- Modify: `src/uv.lock`
- Modify: `src/server.py`
- Create: `src/tests/test_server.py`

**Step 1: Add `pytest` as a dev dependency**

Run: `cd src && uv add --dev pytest`
Expected: `src/pyproject.toml` and `src/uv.lock` gain test dependencies

**Step 2: Extract or isolate helper logic in `src/server.py`**

Create testable helpers for:

- sentence splitting
- lesson normalization
- speech text selection

**Step 3: Write failing tests for the helper behavior**

Cover:

- Chinese punctuation splitting
- valid lesson normalization
- incomplete lesson fallback
- transcription preservation

**Step 4: Run the tests and verify the failures are real**

Run: `cd src && uv run pytest src/tests/test_server.py -q`
Expected: FAIL until the helper logic is implemented

**Step 5: Commit**

Run:
```bash
git add src/pyproject.toml src/uv.lock src/server.py src/tests/test_server.py
git commit -m "test: add server helpers for mandarin tutor rollout"
```

### Task 2: Validate a Mandarin-Capable Local TTS Path

**Files:**
- Modify: `src/tts.py`
- Modify: `src/benchmarks/benchmark_tts.py`
- Create: `src/benchmarks/mandarin_phrases.py`
- Optional Modify: `README.md`

**Step 1: Add a small Mandarin phrase fixture**

Include characters and an English label for each phrase so the benchmark can print readable results.

**Step 2: Update the benchmark script to exercise the Mandarin phrase set**

Run: `cd src && uv run python benchmarks/benchmark_tts.py`
Expected: local benchmark runs on the target machine and prints timings for the Mandarin phrase set

**Step 3: Add minimal voice configuration in `src/tts.py`**

Prefer environment variables such as:

- `TTS_VOICE`
- `TTS_SPEED`

Only add a second backend if the benchmark shows the current path is not credible.

**Step 4: Perform a manual listening check**

Expected: pass the go / no-go gate above before continuing

**Step 5: Commit**

Run:
```bash
git add src/tts.py src/benchmarks/benchmark_tts.py src/benchmarks/mandarin_phrases.py README.md
git commit -m "feat: validate local mandarin speech path"
```

### Task 3: Add Structured Tutor Output on the Backend

**Files:**
- Modify: `src/server.py`
- Test: `src/tests/test_server.py`

**Step 1: Replace the generic assistant prompt with a beginner Mandarin tutor prompt**

The prompt must instruct the model to use the tool every turn and avoid unsupported pronunciation grading claims.

**Step 2: Expand the tool contract**

Move from:

- `transcription`
- `response`

To:

- `transcription`
- `text`
- `english_coaching`
- `mandarin_text`
- `pinyin`
- `meaning`
- `pronunciation_tip`
- `repeat_prompt`
- `speech_text`

**Step 3: Normalize tool output into a stable WebSocket payload**

Always send:

- `type`
- `text`
- `llm_time`

Optionally send:

- `transcription`
- `lesson`

**Step 4: Make the tests pass**

Run: `cd src && uv run pytest src/tests/test_server.py -q`
Expected: PASS

**Step 5: Commit**

Run:
```bash
git add src/server.py src/tests/test_server.py
git commit -m "feat: add structured mandarin lesson payloads"
```

### Task 4: Stream the Right Speech Text

**Files:**
- Modify: `src/server.py`
- Test: `src/tests/test_server.py`

**Step 1: Expand sentence splitting to support Chinese punctuation**

Include `。`, `！`, and `？`.

**Step 2: Route TTS through normalized `speech_text`**

Behavior:

- prefer `lesson.speech_text`
- otherwise use top-level `text`
- never speak an empty string

**Step 3: Keep interrupt handling unchanged**

Do not regress barge-in while changing the streamed sentence source.

**Step 4: Re-run automated tests**

Run: `cd src && uv run pytest src/tests/test_server.py -q`
Expected: PASS

**Step 5: Commit**

Run:
```bash
git add src/server.py src/tests/test_server.py
git commit -m "feat: stream mandarin lesson speech text"
```

### Task 5: Render a Structured Lesson Card Without Breaking Fallbacks

**Files:**
- Modify: `src/index.html`

**Step 1: Add DOM helpers for lesson-card rendering**

Render structured lesson fields with safe text insertion only.

**Step 2: Keep the current fallback path**

If `lesson` is absent, continue rendering the existing assistant bubble.

**Step 3: Keep transcription replacement working**

The temporary user loading bubble should still be replaced from top-level `transcription`.

**Step 4: Manually verify in the browser**

Check:

- lesson card layout
- plain-text fallback
- transcription replacement
- barge-in during playback

**Step 5: Commit**

Run:
```bash
git add src/index.html
git commit -m "feat: render mandarin lesson cards in transcript"
```

### Task 6: End-to-End MVP Verification

**Files:**
- Modify: `README.md`
- Optional Modify: `doc/plans/2026-04-07-mandarin-teacher-design.md`

**Step 1: Run backend tests**

Run: `cd src && uv run pytest -q`
Expected: PASS

**Step 2: Run the latency benchmark**

Run: `cd src && uv run python benchmarks/bench.py`
Expected: responses still complete within a reasonable local-interaction budget

**Step 3: Run the app manually and test real beginner scenarios**

Use prompts such as:

- "Teach me how to say hello in Mandarin."
- "How do I introduce myself?"
- "Please say that again more slowly."

**Step 4: Update README usage notes if configuration changed**

Document any new TTS environment variables and the beginner-teacher behavior.

**Step 5: Commit**

Run:
```bash
git add README.md doc/plans/2026-04-07-mandarin-teacher-design.md
git commit -m "docs: document mandarin teacher mvp"
```

## Open Risks

- The local TTS stack may still be too weak for Mandarin even after voice tuning
- Gemma may occasionally skip schema fields, so normalization must stay defensive
- The browser UI currently uses string-based rendering patterns; the lesson-card work must avoid expanding that risk

## Recommendation

Ship the MVP only if the local speech path passes the manual phrase check. If it does not, stop after Task 2, document the blocker clearly, and file a follow-up issue for a different local Mandarin TTS backend rather than forcing the rest of the UI rollout.
