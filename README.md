# ul-ialt-04-tlg-2004

> 2026-05-19, 11:15-12:45, [04-TLG-2004.SE01 Probleme und Methoden der
> Übersetzung](http://web.archive.org/web/20260427185142/https://almaweb.uni-leipzig.de/scripts/mgrqispi.dll?APPNAME=CampusNet&PRGNAME=COURSEDETAILS&ARGUMENTS=-N000000000000001,-N000590,-N0,-N396874687513055,-N396874687522056,-N0,-N0,-N0)

> [Martin Czygan](martin.czygan@gmail.com), SWE at Leipzig University Library;
> previously Lecturer at Lancaster University and HAW Hamburg, and Open Data
> Engineer at Internet Archive

## Local LLM and notes on LLM for translation

Three questions for today:

* What is a local LLM and how can I work work with one?
* Are there local LLM specifically for translations?
* How does context influence translations quality?

## Disclaimer

* language models are like any other machine, they can be benefit or a hazard; "[Traum oder Alptraum](https://blog.ub.uni-leipzig.de/ki-ein-traum-oder-alptraum-fuer-die-bibliothek/)"
* there is enough room between being luddite about it and blindly cheering it up
* AI has lots of negative externalities

> Negative Externality (Cost): An action that imposes unintended costs on
> others

Where I use and avoid working with an LLM:

* OK: code snippets, transcripts, quick summaries, tutor
* NO: prose for human consumption, as I feel LLMs can [distort our written language](https://arxiv.org/abs/2603.18161)

Observation for my field: deeply affected, agentic coding becoming mainstream
fast; very different speeds of adoption, wide variety of results:

> AI tools have seduced many people into a false belief that these fundamentals
> no longer apply. People brag about codebases of hundreds of thousands of
> lines that have never been viewed by people, churned out in record time. On
> closer inspection, these codebases inevitably turn out to be more like
> dancing elephants than useful engineering artifacts.

## What is a local LLM and how can I work with one?

* what is an LLM? an llm is a file
* example how you run them: you can download it, ollama, jan.ai, ...

## Are there local LLM specifically for translations?

Yes. On HF, we find about 12K models under the *translation* tag.

![](static/screenshot-2026-05-18-220355-hf-tag-translation.png)

There are also some notable

* translategemma

### Evaluation

* [WMT25](https://aclanthology.org/2025.wmt-1.22.pdf), "WMT25 General Machine Translation Shared Task"

### Top 30 Models

All time:

![](static/2026-05-18-hf-translation-top-30.png)

Since 2025:

![](static/2026-05-18-hf-translation-top-30-since-2025.png)

Since 2026:

![](static/2026-05-18-hf-translation-top-30-since-2026.png)

## How does context influence translations quality?
