# TODO

Goal: compute metrics over a fixed reference corpus and a
swappable open-source translation model, to get comparable per-model scores.
The scoring half is mostly here (with caveats below); the runner half is not.

## Open-source model benchmarking

- [ ] Need a reference corpus. Candidates: the [Open Language Data
      Initiative](https://oldi.org/) (OLDI) datasets — successor home for the
      FLORES-style parallel data, actively maintained where FLORES-200 itself
      effectively isn't; WMT22/23 test sets; or a hand-curated set matching
      the content types we actually care about (UI strings, narrative,
      marketing).
- [ ] Pick an initial language pair set. Useful starting subset, taken from
      the Alconost top languages by sample volume: en→{de, ja, zh-CN, pt-BR}
      — coverage of morphologically rich / non-Latin / Latin alphabets.
- [ ] Translation runner: takes (model, language pair, corpus), emits JSONL
      with `src` / `mt` / `ref` so `extra.py` scores it without reshaping.
- [ ] Support Ollama and any OpenAI-compatible chat endpoint (vLLM, LM
      Studio). Cache translations on disk by (model, src) so a re-score
      doesn't re-translate. Pattern can mirror `extra.py`'s embedding cache.
- [ ] Initial model list to evaluate: NLLB-200, Madlad-400, Aya, Qwen,
      Gemma, Llama. Include one proprietary anchor (e.g. Claude or Gemini
      via API) for calibration against the Alconost numbers.
- [ ] Per-model summary output: mean per metric + combined, with sample
      size and per-language breakdown. Reuse `_emit_markdown` so the result
      drops straight into a writeup.

## Alconost-index fidelity

The current `extra.py` + `metrics.py` produce an Alconost-style composite with
the right components and weights (COMET 30 / LE 20 / nTER 15 / BERTscore 15 /
BLEU 10 / CHrF++ 5 / COMET-QE 5, summing to 1.00), but three of the seven
components are approximations rather than the textbook implementations the
index assumes.

| Component | Weight | Status | Notes |
|---|---|---|---|
| COMET | 30% | Real | `Unbabel/wmt22-comet-da` via official API. Faithful. |
| LE | 20% | Pass-through | Must be supplied as `le` field (0-100) or `--le`. If missing, gets dropped and the remaining weights re-normalize — `combined` then doesn't include the 20% human signal. |
| nTER | 15% | Simplified | Token-level Levenshtein normalized by ref length. Real TER also credits **shift** operations; without them this is effectively **WER**, which tends to over-estimate edit rate. Higher nTER → lower `(1-nter)` contribution → drags `combined` down vs a "true" TER score. |
| BERTscore | 15% | Approximation | Real BERTscore uses contextual subword embeddings in a single forward pass. `extra.py` calls a sentence-embedding API per sentence (or per token via `--bertscore-mode token-greedy`). Absolute values won't match published BERTscore numbers. |
| BLEU | 10% | Simplified | Constant 1e-4 smoothing (not Chen-Cherry), no tokenization standardization (sacrebleu's `13a`). OK for relative comparison; won't match a `sacrebleu` number on the same pair. |
| CHrF++ | 5% | Reasonable | Char n-grams 1-6 + word n-grams 1-2, β=2, mean of both. Matches Popović's formulation; small differences vs sacrebleu around tokenization. |
| COMET-QE | 5% | Real | `Unbabel/wmt22-cometkiwi-da`. Faithful. |

### To make the score publishable / Alconost-comparable

- [ ] Add `sacrebleu` and swap `calculate_bleu` / `calculate_chrf_plus` (and gain a proper TER too).
- [ ] Add `bert-score` and replace the embedding-API BERTscore approximation with real contextual BERTscore. Keep the embedding-API mode behind a flag for offline / no-GPU use.
- [ ] Warn (or hard-error behind a flag) when `combined` is produced without `le`, so the silent re-normalization of the 20% human-signal slot doesn't go unnoticed.

### Smaller items

- [ ] Decide whether nTER should be replaced by sacrebleu's TER (with shifts) or kept as-is and renamed `wer` for honesty.
- [ ] Consider exposing the WEIGHTS dict via CLI so the recipe can be tuned without editing source.
