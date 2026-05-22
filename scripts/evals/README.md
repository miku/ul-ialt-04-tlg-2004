# Translation evaluation, briefly

WIP playground for computing translation-quality metrics, so we can run them
against open-source translation models and see how they compare on the same
content under the same scoring rules.

The metric stack and weights mirror the **Alconost Quality Index (AQI)** from
[Best LLM for Translation in 2026: A Data-Driven Engine Scoreboard](https://alconost.com/en/blog/best-llm-for-translation-2026) (Alconost,
May 2026, [local copy](best-llm-for-translation-2026.txt)):

| Metric    | Weight | What it captures |
|-----------|-------:|------------------|
| COMET     | 30%    | Neural metric, strong human-judgment correlation |
| LE        | 20%    | Linguist Evaluation, 0-100 (human input) |
| nTER      | 15%    | Edit-distance, proxies post-editing effort |
| BERTscore | 15%    | Contextual embedding similarity |
| BLEU      | 10%    | Classic n-gram precision |
| CHrF++    |  5%    | Character n-gram F-score |
| COMET-QE  |  5%    | Reference-free quality estimation |

See [TODO.md](./TODO.md) for which components are faithful implementations and
which are approximations, and for the open-source model benchmarking work
that's still to do.

## Surface metrics: `metrics.py`

Pure Python, no dependencies. BLEU, ROUGE-N, chrF++, nTER, Jaccard.

```shell
$ python metrics.py
```

| Reference | Candidate | Jac | BLEU | ROUGE-1 | CHrF++ | nTER |
|---|---|---|---|---|---|---|
| The cat sits on the mat | The cat is sitting on the mat | 0.571 | 0.052 | 0.833 | 0.704 | 0.333 |
| Hello world | Hello world | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
| This is a complex translation test | Something completely different | 0.000 | 0.000 | 0.000 | 0.110 | 1.000 |

## Additional metrics: `extra.py`

Adds the neural / embedding-based metrics: COMET and COMET-QE via
[unbabel-comet](https://github.com/Unbabel/COMET), BERTscore via an OpenAI-compatible embeddings endpoint (local
Ollama out of the box) and combines all seven into a single weighted
`combined` score. Uses `uv run --script` so dependencies install on first run.

```shell
$ ./extra.py --metrics all --model nomic-embed-text:latest --input example.jsonl --format markdown
```

| src | mt | ref | bleu | chrf_plus | nter | bertscore | comet | comet_qe | combined |
|---|---|---|---|---|---|---|---|---|---|
| Le chat est sur le tapis. | The cat is sitting on the mat | The cat sits on the mat | 0.052 | 0.704 | 0.333 | 0.983 | 0.921 | 0.830 | 0.757 |

JSONL on stdin works the same way. Each output record carries a `meta` block
with weights and model identifiers, so a results file is self-describing:

```shell
$ echo '{
  "src": "Le chat est sur le tapis.",
  "ref": "The cat sits on the mat",
  "cand": "The cat is sitting on the mat"
}' | ./extra.py --metrics all --model nomic-embed-text:latest | jq .

{
  "src": "Le chat est sur le tapis.",
  "ref": "The cat sits on the mat",
  "mt": "The cat is sitting on the mat",
  "scores": {
    "bleu": 0.05169731539571706,
    "chrf_plus": 0.7037631071761987,
    "nter": 0.3333333333333333,
    "bertscore": 0.9827368052790287,
    "comet": 0.9212710857391357,
    "comet_qe": 0.8304271697998047,
    "combined": 0.7570888648774587
  },
  "meta": {
    "metrics": ["bertscore", "bleu", "chrf_plus", "comet", "comet_qe", "nter"],
    "weights": {"bertscore": 0.15, "bleu": 0.1, "chrf_plus": 0.05, "comet": 0.3, "comet_qe": 0.05, "nter": 0.15},
    "embedding_model": "nomic-embed-text:latest",
    "embedding_base_url": "http://strix:11434/v1",
    "bertscore_mode": "sentence-cosine",
    "comet_model": "Unbabel/wmt22-comet-da",
    "comet_qe_model": "Unbabel/wmt22-cometkiwi-da",
    "timestamp": "2026-05-22T12:38:23.871811+00:00"
  }
}
```

## Why different metrics?

Different metrics catch different signals: surface overlap (BLEU, CHrF++),
edit effort (nTER), semantic similarity (BERTscore), learned alignment with
human judgment (COMET). A weighted blend smooths over each metric's blind
spots. AQI's weighting (heavy COMET + LE, light BLEU) reflects the current
consensus that surface overlap is a weak signal in 2026.

LLM-as-judge scoring is a separate evaluation track ([survey, Jan
2026](https://arxiv.org/pdf/2504.01919#page=33)) and not implemented here.
