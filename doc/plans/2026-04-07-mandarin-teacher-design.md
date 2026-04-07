# Mandarin Teacher Design

## Goal

Turn Parlor from a general-purpose conversational assistant into a real-time, on-device, private Mandarin tutor for an absolute beginner. The app should stay mostly in English while introducing small amounts of Mandarin, and it must help the user learn correct pronunciation through spoken examples, pinyin, repetition, and clear coaching.

## Current State

The current app already has the right high-level architecture for a conversational tutor:

- `server.py` owns the system prompt, websocket loop, LLM conversation, and TTS streaming.
- `tts.py` provides a unified TTS backend abstraction, but it currently defaults to an English-oriented Kokoro voice.
- `index.html` provides a compact transcript UI, but it treats assistant output as a single generic message rather than a structured lesson card.

The main gap is that the current system is optimized for a generic assistant, not a Mandarin teacher. Prompt changes alone would improve pedagogy, but they would not make pronunciation trustworthy.

## Requirements

### Functional

- Keep the app fully on-device and private.
- Keep the interaction conversational and real-time.
- Teach an absolute beginner, so default responses should remain mostly in English.
- Introduce only a small amount of Mandarin at a time.
- Always include pinyin for new Mandarin phrases.
- Provide spoken Mandarin examples so the user can hear pronunciation.
- Encourage repetition and short speaking practice.

### Non-Functional

- Do not rely on cloud inference, cloud STT, or cloud TTS services.
- Preserve low-latency interaction.
- Avoid turning each turn into a long spoken monologue.
- Make the lesson format visually clear in the transcript UI.
- Local browser-side assets may still be fetched normally; the privacy boundary is around model inference and speech processing.

## Recommended Approach

Keep the current Gemma-based conversation loop, but upgrade the app in five coordinated areas:

1. Replace the generic teaching prompt with a beginner-Mandarin tutor prompt.
2. Move from a single freeform assistant reply toward structured lesson output.
3. Add a Mandarin-capable on-device speech path instead of assuming the current English-first TTS is sufficient.
4. Update the frontend to render lesson content in a learner-friendly format.
5. Add basic Mandarin-specific formatting and playback support, including sentence splitting for Chinese punctuation.

This is the best balance of speed, risk, and quality because it preserves the working real-time architecture while fixing the product-critical issue: spoken Mandarin quality.

## Prompt Design

The new system prompt should instruct the model to behave as a patient Mandarin teacher for a total beginner. It should:

- Stay mostly in English unless deliberately presenting practice material.
- Introduce only one or two new Mandarin items per turn.
- Always include pinyin for new Mandarin words or phrases.
- Explain pronunciation in plain English.
- Favor short, repeatable examples over long explanations.
- Ask the user to repeat words aloud often.
- Correct likely misunderstandings gently and clearly.
- Keep responses concise enough for low-latency conversation and short TTS playback.

The teacher should not assume prior knowledge of tones, pinyin, grammar, or characters.

## Response Structure

The backend should evolve from a single `response` string into structured tutor output. A suitable first schema is:

- `english_coaching`
- `mandarin_text`
- `pinyin`
- `meaning`
- `pronunciation_tip`
- `repeat_prompt`
- `transcription`
- `speech_text`

The intended meaning of these fields should be explicit:

- `english_coaching`: short teaching explanation in English
- `mandarin_text`: the exact Mandarin phrase the learner should see
- `pinyin`: pinyin for the Mandarin phrase
- `meaning`: concise English gloss or translation
- `pronunciation_tip`: plain-English coaching on tones or mouth shape
- `repeat_prompt`: short repetition instruction for the learner
- `transcription`: exact transcription of what the user said
- `speech_text`: the exact text that should be sent to TTS for this turn

The tutor may omit some optional fields on simple turns, but beginner lesson turns should consistently separate what to say, how to pronounce it, what it means, and what should actually be spoken.

This structure will make the system more reliable than relying on raw prompt formatting, and it will let the frontend present lessons clearly.

## Speech Design

Pronunciation is the product, so the speech layer should be treated as a first-class subsystem rather than a transparent post-processing step.

The current `tts.py` abstraction is a good place to introduce a Mandarin-aware backend interface. The app should be able to choose a Mandarin-capable local speech backend without changing the rest of the websocket flow.

The speech layer should be validated before the full UI migration. A small manual phrase set should be used to determine whether the current local Mandarin-capable backend is credible enough to proceed.

Speech behavior should follow these rules:

- Speak the Mandarin example by default.
- Optionally speak a very short English cue when helpful.
- Avoid speaking the full teaching explanation unless explicitly needed.
- Support slower learner-friendly pacing.
- Preserve streaming playback so the app still feels responsive.

If the available fully local TTS backend cannot produce credible Mandarin pronunciation, rollout should stop until the speech layer is good enough.

## Frontend Design

The transcript UI should render tutor messages as structured lesson cards rather than one generic bubble. Each assistant turn should clearly separate:

- what to say
- pinyin
- meaning
- pronunciation guidance
- repeat instruction

This should remain compact and readable in the current interface without redesigning the entire app shell.

The current frontend should also be updated so multiline or structured assistant content renders predictably.

## Backend Design

The websocket flow in `server.py` should remain the backbone of the app. The main backend changes are:

- replace the system prompt
- update the response tool contract to support structured tutor output
- keep the existing user transcription transport reliable during rollout, even if the tutor payload grows
- serialize structured lesson fields to the frontend
- synthesize the Mandarin-specific `speech_text` field instead of speaking the whole reply
- expand sentence splitting to include Chinese punctuation such as `。`, `！`, and `？`
- preserve a compatibility fallback so the app can still render a plain text assistant message if the tool call or schema output is incomplete

This keeps the architecture simple and minimizes risk to the real-time interaction loop.

## Testing

Testing should cover three areas.

### Formatting

- Verify the tutor consistently produces beginner-safe output.
- Verify new Mandarin content includes pinyin.
- Verify new Mandarin teaching turns include `meaning` and `speech_text`.
- Verify response length stays short enough for real-time voice interaction.

### Streaming and UX

- Verify Chinese punctuation splits correctly for streamed playback.
- Verify assistant cards render cleanly in the transcript.
- Verify playback interruption still works correctly when the user barges in.
- Verify the UI still renders a reasonable plain-text fallback if structured tutor fields are missing.

### Rollout Compatibility

- Verify the backend still handles both tool-call output and raw-text fallback safely during migration.
- Verify missing optional schema fields do not break websocket payload handling.
- Verify legacy transcript updates for user transcription still work while assistant cards become structured.

### Pronunciation Quality

- Create a small Mandarin phrase regression set.
- Run manual listening checks on the local machine.
- Validate that slow playback still sounds natural enough for instruction.
- Gate broader implementation on this check; if the local speech path is not credible, do not continue with UI-heavy changes.

Automated tests can cover formatting and transport behavior, but pronunciation quality requires deliberate human listening.

## Risks

- The current local TTS stack may not be good enough for Mandarin pronunciation.
- Structured output adds some implementation complexity to the current simple tool API.
- If the lesson format becomes too verbose, latency and usability will suffer.

The highest-risk item is speech quality, so that should be validated early.

## Implementation Outline

Implementation should proceed in this order:

1. validate a local Mandarin-capable speech path on a small phrase set
2. update the tutor prompt and tool contract, including `meaning` and `speech_text`
3. update speech selection and sentence splitting for Mandarin-aware playback
4. make the frontend render structured lesson fields while preserving plain-text fallback behavior
5. tune pacing and wording for beginner lessons

This order reduces wasted work because it validates the product-critical speech path before deeper frontend work and keeps the rollout compatible with the current text-based transport.
