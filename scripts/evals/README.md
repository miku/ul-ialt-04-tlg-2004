# WIP: Quick Eval Experiment

Evals for **Translation** is a complex topic, as a number of approaches exist.

> Machine translation evaluation is a very active research area. Neural metrics
> are getting better and more efficient every year as we've seen in combination of
transformer-based [...] models. [Machine Translation evaluation metrics benchmarking: From traditional MT to LLMs](https://diposit.ub.edu/server/api/core/bitstreams/f27c4922-841b-4254-8ee4-e6a6d59e2b8c/content#page=20) (06/2023)

Quick example in Python:

```shell
$ python metrics.py
```

Reference                           | Candidate                           | Jac    | BLEU   | ROUGE-1 | CHrF++ | nTER
------------------------------------------------------------------------------------------------------------------------------------------------
The cat sits on the mat             | The cat is sitting on the mat       | 0.571 | 0.052 | 0.833 | 0.704 | 0.333
Hello world                         | Hello world                         | 1.000 | 1.000 | 1.000 | 1.000 | 0.000
This is a complex translation test  | Something completely different      | 0.000 | 0.000 | 0.000 | 0.110 | 1.000

Different metrics pick up different signals, example [Alconost Quality
Index](https://alconost.com/en/blog/best-llm-for-translation-2026), which is a
weighted score of BLEU, nTER, COMET, and others.

Classic metrics relied on deterministic formulas, modern LLM based evaluations
use LLM-as-a-judge style scoring.

> LLMs are increasingly being used as **automatic judges of MT quality**. Unlike
> traditional metrics like BLEU or learned metrics like COMET and BLEURT,
> LLM-based evaluators rely on prompting a generative model with source,
> translation, and possi- bly reference inputs to elicit quality scores or
> error analyses. While this LLM-as-judge paradigm offers flexibility and
> strong system-level performance, it also raises critical concerns regarding
> bias, segment-level reliability, and sensitivity to prompt design. --
> [Bridging the Linguistic Divide: A Survey on Leveraging Large Language Models
> for Machine Translation](https://arxiv.org/pdf/2504.01919#page=33) (01/2026)


```
$ ./extra.py --metrics all --model nomic-embed-text:latest --input example.json --format markdown
```

| src | mt | ref | bleu | chrf_plus | nter | bertscore | comet | comet_qe | combined |
|---|---|---|---|---|---|---|---|---|---|
| Le chat est sur le tapis. | The cat is sitting on the mat | The cat sits on the mat | 0.052 | 0.704 | 0.333 | 0.983 | 0.921 | 0.830 | 0.757 |


Extra.


```shell
$ echo '
{
  "src": "Le chat est sur le tapis.",
  "ref": "The cat sits on the mat",
  "cand": "The cat is sitting on the mat"
}
' | ./extra.py --metrics all --model nomic-embed-text:latest | jq .

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
    "metrics": [
      "bertscore",
      "bleu",
      "chrf_plus",
      "comet",
      "comet_qe",
      "nter"
    ],
    "weights": {
      "bertscore": 0.15,
      "bleu": 0.1,
      "chrf_plus": 0.05,
      "comet": 0.3,
      "comet_qe": 0.05,
      "nter": 0.15
    },
    "embedding_model": "nomic-embed-text:latest",
    "embedding_base_url": "http://strix:11434/v1",
    "bertscore_mode": "sentence-cosine",
    "comet_model": "Unbabel/wmt22-comet-da",
    "comet_qe_model": "Unbabel/wmt22-cometkiwi-da",
    "timestamp": "2026-05-22T12:38:23.871811+00:00"
  }
}
```
