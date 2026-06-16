# NLM Pass 6 10k Repaired Results

Run completed on Alienware on 2026-06-15.

## Artifacts

- Dataset: `datasets\nlm_v1\nlm_v1_pass6_10k_repaired.jsonl`
- Output adapter: `models\nlm_v1_lora_pass6_10k_repaired`
- Focused repair eval: `datasets\nlm_v1\nlm_v1_pass5_repair_eval.jsonl`
- Broad eval: `datasets\nlm_v1\nlm_v1_eval_seed.jsonl`
- Focused predictions: `datasets\nlm_v1\prototype_lora_pass6_10k_repaired_focused_predictions.jsonl`
- Broad predictions: `datasets\nlm_v1\prototype_lora_pass6_10k_repaired_broad_predictions.jsonl`
- Train log: `data\nlm_logs\nlm_train_pass6_10k_repaired_20260615_152127.log`
- Focused score JSON: `data\nlm_reports\pass6_10k_repaired_focused_20260615_152127.json`
- Broad score JSON: `data\nlm_reports\pass6_10k_repaired_broad_20260615_152127.json`

## Training Summary

- Base model: `unsloth/Llama-3.1-8B-Instruct`
- Dataset records: `10,000`
- Epochs: `1`
- Steps: `1250`
- Runtime: `4556s` / about `75.9 minutes`
- Samples/sec: `2.195`
- Steps/sec: `0.274`
- Train loss: `0.1306`
- Final adapter saved to `models\nlm_v1_lora_pass6_10k_repaired`

## Focused Repair Eval

- Eval cases: `25`
- Valid JSON: `100.0%` (`25/25`)
- Function accuracy: `100.0%` (`25/25`)
- Parameter match: `100.0%` (`25/25`)
- Response text match: `96.0%` (`24/25`)
- Strict pass: `96.0%` (`24/25`)
- Failures: `1`

Focused miss:

- `pass5-eval-offline-0003`
  - User: `can you help without internet`
  - Issue: response was correct in meaning but did not include the literal eval fragment `offline`.
  - Actual response: `Yes. I can still handle local apps, windows, system controls, music, memory, and conversation. Web features need online mode.`

## Broad Eval

- Eval cases: `137`
- Valid JSON: `100.0%` (`137/137`)
- Function accuracy: `99.3%` (`136/137`)
- Parameter match: `97.1%` (`133/137`)
- Response text match: `100.0%` (`137/137`)
- Strict pass: `97.1%` (`133/137`)
- Failures: `4`

Broad failures:

1. `eval-brightness-0002`
   - User: `dim the screen a bit`
   - Expected: `decrease_brightness` with `{"amount": 10}`
   - Actual: `adjust_brightness` with `{"amount": -10}`

2. `eval-youtube-0007`
   - User: `show latest videos from mkbhd`
   - Expected: `get_channel_videos` with `{"channel_name": "mkbhd", "count": 5}`
   - Actual: `get_channel_videos` with `{"channel_name": "mkbhd", "count": 3}`

3. `eval-music-0007`
   - User: `list my music library`
   - Expected: `list_music_library` with `{}`
   - Actual: `list_music_library` with `{"artist": "artist", "sort": "sort"}`

4. `eval-goal-0001`
   - User: `track my goal learn guitar`
   - Expected: `track_goal` with `{"goal_name": "learn guitar"}`
   - Actual: `track_goal` with `{"goal_name": "learn guitar", "description": "description"}`

## Comparison

- Pass4 broad strict: `96.4%` (`132/137`)
- Pass5 focused strict: `100.0%` (`25/25`)
- Pass5 broad strict: `83.9%` (`115/137`)
- Pass6 focused strict: `96.0%` (`24/25`)
- Pass6 broad strict: `97.1%` (`133/137`)

## Decision

Pass 6 is the best broad adapter so far and beats Pass 4 by one strict broad case.

Promotion is reasonable if broad routing is the priority. If the focused repair gate must be exactly `100%`, the only remaining focused issue is a wording-only offline response miss, not a function or parameter routing failure.

Recommended next step: keep `models\nlm_v1_lora_pass6_10k_repaired` as the current best candidate, then decide whether to run a tiny wording-only repair for offline responses or accept Pass 6 because it improves broad eval without the Pass 5 overfit.
