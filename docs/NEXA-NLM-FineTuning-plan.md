# NLM V1: NEXA Spoken-Intent Brain

## Summary

Fine-tune `Llama 3.1 8B Instruct` into **NLM**, a NEXA-specific local model that understands messy spoken user input, knows NEXA's current capabilities, chooses the right intent/function, handles follow-ups, and behaves like a warm desktop assistant.

NLM will improve understanding and behavior, while NEXA's runtime code remains responsible for memory retrieval, validation, focus-mode safety, and actual execution.

## Wake Word Boundary

Wake-word detection stays outside NLM. The listener/runtime decides whether the user is addressing NEXA; NLM only receives text after NEXA is already awake, in active follow-up mode, or in an approved proactive-response window.

This matters because words like `next`, `nexus`, `nex`, and `lexa` can be ASR mishearings of `Nexa`, but `next` can also be part of real commands like `next song`. The wake-word gate should handle fuzzy activation conservatively, especially during media playback, while the dataset should teach NLM to understand addressed commands such as `Nexa open Chrome`, `hey next open Chrome`, or command text passed after the wake gate.

NLM should not become the source of truth for whether NEXA was called. It can learn to ignore leading address words and ASR noise, but activation, false-positive protection, timeout behavior, proactive bypass, and media-mode strictness remain runtime responsibilities.

Disambiguation rule:

- In passive/idle mode, fuzzy wake aliases should only count near the beginning of the transcript and only when the phrase looks like the user is addressing NEXA.
- In active/follow-up mode, words like `next`, `then`, `after that`, and `now` are treated as normal command sequencing, not wake words.
- After a confirmed wake word, examples like `reduce the brightness, next open Steam` should be parsed by NLM as a multi-step or follow-up instruction.
- Unaddressed passive transcripts like `next work item`, `next song`, or `next open Steam` should not wake NEXA unless the listener has strong evidence that `next` is an ASR mistake for `Nexa`.
- Media mode should be stricter than normal idle mode to avoid waking from lyrics, videos, or background speech.

## Dataset Plan

- Build `datasets/nlm_v1/` from the live NEXA function registry.
- Use chat/instruction examples compatible with Unsloth SFT.
- Target dataset sizes:
  - Prototype: `2,000` examples.
  - V1: `20,000-30,000` examples.
  - V1.5: `50,000+` examples after adding failure cases.
- Dataset mix:
  - `45%` spoken command understanding and function routing.
  - `20%` follow-ups, pronouns, ordinals, corrections, and multi-step commands.
  - `15%` assistant behavior and conversational meaning.
  - `10%` NEXA feature/capability Q&A.
  - `5%` clarification examples.
  - `5%` safety, offline limits, and risky-command confirmation.
- Include moderate ASR-style noise:
  - missing punctuation;
  - repeated words;
  - partial commands;
  - casual filler;
  - misheard words;
  - user corrections like "no wait".
- Include wake-word/address noise only as post-gate text examples:
  - `hey nexa open chrome`;
  - `nexa please lower the volume`;
  - `hey next open settings`;
  - `nexus what can you do`;
  - `reduce the brightness then open steam`;
  - `reduce the brightness next open steam`;
  - do not train NLM to decide whether an unaddressed transcript should wake NEXA.

## Model Behavior

Commands return strict JSON:

```json
{"function_call":{"name":"open_application","parameters":{"app_name":"chrome"}},"response":"Opening Chrome."}
```

Conversation returns:

```json
{"response":"..."}
```

NLM should learn:

- when to call a function;
- when to answer normally;
- when to ask clarification;
- when to check memory;
- when to confirm risky actions;
- when a request is unavailable offline;
- how to respond in NEXA's assistant personality.

NLM should not memorize private user facts. It should learn to use runtime memory functions.

## Unsloth Workflow

- Use Unsloth QLoRA for efficient fine-tuning.
- Base model: `unsloth/Llama-3.1-8B-Instruct` or equivalent Llama 3.1 8B Instruct checkpoint.
- Recommended starting config:
  - sequence length: `4096`;
  - LoRA rank: `16`;
  - LoRA alpha: `16` or `32`;
  - epochs: `1-3`;
  - learning rate: around `2e-4`;
  - train on assistant responses only if practical;
  - keep the same chat template for training and Ollama inference.
- Training stages:
  - Stage 1: train on the 2k prototype dataset as a smoke/pipeline validation run.
  - Stage 2: evaluate intent/function accuracy.
  - Stage 3: expand to 20k-30k examples.
  - Stage 4: train V1.
  - Stage 5: export merged model/adapters to GGUF.
  - Stage 6: quantize to `Q4_K_M`.
  - Stage 7: import into Ollama as `nexa-nlm:8b-q4_k_m`.

## Integration

- Update NEXA config/model name from `llama3.1:8b-instruct-q4_K_M` to `nexa-nlm:8b-q4_k_m`.
- Keep existing runtime guardrails:
  - `DynamicPreprocessor`;
  - `ReferenceResolver`;
  - `ClarificationHandler`;
  - `IntentState`;
  - `FunctionValidator`;
  - wake-word listener/gate;
  - kernel/focus-mode gating;
  - JSON extraction fallback.
- After NLM proves stable, reduce prompt size gradually, but do not remove runtime safety.

## Evaluation

- Create a golden eval set with `1,000+` prompts.
- Cover:
  - every registered function;
  - messy voice input;
  - follow-ups;
  - multi-step commands;
  - emotional conversation;
  - NEXA feature questions;
  - memory-first questions;
  - risky actions;
  - offline/online restrictions.
- Success targets:
  - valid JSON: `99%+`;
  - correct function/intent: `95%+`;
  - correct parameters: `92%+`;
  - no hallucinated functions: `99%+`;
  - better voice-understanding score than current Llama 3.1 8B.

## Current Prototype Run

The Stage 1 prototype completed successfully:

- Dataset: `datasets/nlm_v1/nlm_v1_prototype.jsonl`
- Size: `2,000` examples
- Purpose: verify training, logging, adapter saving, and first behavior improvement
- Not final: the real V1 target remains `20,000-30,000` examples after eval-driven dataset expansion
- Result: function accuracy improved from `41.7%` baseline to `83.3%`; parameter match improved from `33.3%` to `79.2%`

The Stage 1 pass 2 prototype completed after targeted dataset repair:

- Dataset: regenerated `datasets/nlm_v1/nlm_v1_prototype.jsonl`
- Eval: repair eval with `33` cases
- Adapter: `models/nlm_v1_lora_pass2`
- Result: valid JSON `100.0%`, function accuracy `100.0%`, parameter match `100.0%`, response text match `93.9%`
- Notes: pass 2 covered earlier failures plus wake/address noise and active-mode sequencing. It is still a prototype, not the final V1 NLM.

The eval seed has now been broadened for the next measurement pass:

- Eval: `datasets/nlm_v1/nlm_v1_eval_seed.jsonl`
- Size: `137` cases
- Coverage: system, apps, windows, network, Bluetooth, display, web, YouTube, files, games, music, content mode, clipboard, memory, goals, theme, TTS, sequencing, correction, clarification, safety, offline, capability, and assistant behavior
- Pass 2 broad score: valid JSON `100.0%`, function accuracy `63.5%`, parameter match `60.6%`, response text match `94.9%`.
- Pass 3 5k broad score: valid JSON `100.0%`, function accuracy `97.8%`, parameter match `97.8%`, response text match `99.3%`.
- Remaining pass 3 misses: `summarize this paragraph`, `how is my mood today`, and `switch voice to male`.
- Next action: either run a tiny repair pass for the remaining misses or expand toward a richer 10k pre-V1 dataset.

## Assumptions

- First NLM target is NEXA's real current capabilities.
- Base model remains Llama 3.1 8B.
- Dataset starts synthetic from the registry, then improves through eval failures.
- Moderate ASR noise is included.
- Unsloth is used for training, GGUF/Ollama for deployment.

## References

- [Unsloth fine-tuning guide](https://docs.unsloth.ai/get-started/fine-tuning-llms-guide)
- [Unsloth datasets guide](https://docs.unsloth.ai/basics/datasets-guide)
- [Unsloth saving to Ollama](https://docs.unsloth.ai/basics/running-and-saving-models/saving-to-ollama)
- [Ollama GGUF import](https://docs.ollama.com/import)
