#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "unbabel-comet>=2.2",
# ]
# ///
"""
Additional translation-quality metrics that need more than pure-Python string ops.

Companion to ./metrics.py. Implements the neural / embedding-based metrics from
the blog-post weighting:

    COMET (30%)         -> unbabel-comet Python API (loaded once, cached).
    LE (20%)            -> human input, just passed through.
    nTER (15%)          -> already in metrics.py (re-exported here for convenience).
    BERTscore (15%)     -> embedding-based, two modes (see below).
    BLEU (10%)          -> in metrics.py.
    CHrF++ (5%)         -> in metrics.py.
    COMET-QE (5%)       -> unbabel-comet with a QE model (no reference needed).

BERTscore modes
---------------
Real BERTscore uses contextual subword embeddings from a single forward pass over
the sentence. With a sentence-embeddings API (Ollama / vLLM / OpenAI), we can't
get that — each call returns one vector. We approximate it two ways:

  sentence-cosine : cosine sim of full-sentence embeddings (semantic similarity).
                    Honest, fast, but coarse.
  token-greedy    : embed each token in isolation, then BERTscore-style greedy
                    P/R/F1 with max cosine match. Loses context (so not literally
                    BERTscore) but captures partial overlap better than sentence-cosine.

Caching
-------
Embeddings are cached under $XDG_CACHE_HOME (default ~/.cache) keyed by
sha256(model + text). Writes are atomic (write tmp, fsync, os.replace).

Endpoint
--------
Speaks the OpenAI /v1/embeddings protocol. Works with Ollama on
http://localhost:11434/v1 out of the box. Override via --base-url or OPENAI_BASE_URL.
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

# Re-use the surface metrics from the sibling module so this script can produce
# the full weighted score in one shot.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as surface_metrics  # noqa: E402

DEFAULT_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
DEFAULT_MODEL = os.environ.get("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
DEFAULT_COMET_MODEL = os.environ.get("COMET_MODEL", "Unbabel/wmt22-comet-da")
DEFAULT_COMET_QE_MODEL = os.environ.get("COMET_QE_MODEL", "Unbabel/wmt22-cometkiwi-da")

# Blog-post weights. Kept here so combine_metrics() and the CLI agree.
WEIGHTS = {
    "comet": 0.30,
    "le": 0.20,
    "nter": 0.15,
    "bertscore": 0.15,
    "bleu": 0.10,
    "chrf_plus": 0.05,
    "comet_qe": 0.05,
}


# ---------------------------------------------------------------------------
# Cache + IO
# ---------------------------------------------------------------------------

def cache_dir(override=None):
    if override:
        d = Path(override)
    else:
        xdg = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        d = Path(xdg) / "ul-ialt-04-tlg-2004" / "embeddings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(model, text):
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(b"\x00")
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def _cache_path(model, text, root):
    key = _cache_key(model, text)
    # Two-level fanout to avoid huge flat dirs.
    sub = root / key[:2]
    sub.mkdir(parents=True, exist_ok=True)
    return sub / f"{key}.json"


def atomic_write_json(path: Path, data):
    """Write JSON atomically: tmp file in same dir, fsync, os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def _fetch_embedding(text, model, base_url, api_key, timeout):
    url = f"{base_url.rstrip('/')}/embeddings"
    payload = json.dumps({"model": model, "input": text}).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'dummy'}",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            body = json.load(resp)
    except urlerror.HTTPError as e:
        # Surface the response body — Ollama / OpenAI return useful JSON error details
        # (e.g. "model not found", wrong endpoint shape).
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = "<no body>"
        raise RuntimeError(
            f"embedding request failed: POST {url} -> {e.code} {e.reason}\n"
            f"  model: {model!r}\n"
            f"  body:  {err_body[:500]}"
        ) from e
    except urlerror.URLError as e:
        raise RuntimeError(f"embedding request failed: POST {url} -> {e.reason}") from e

    # OpenAI/Ollama format: {"data": [{"embedding": [...], ...}], ...}
    try:
        return body["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(
            f"unexpected embedding response shape from {url}: {json.dumps(body)[:500]}"
        ) from e


def get_embedding(text, model, base_url, api_key=None, timeout=60,
                  cache_root=None, no_cache=False, verbose=False):
    if not no_cache:
        path = _cache_path(model, text, cache_root)
        if path.exists():
            try:
                with path.open(encoding="utf-8") as f:
                    return json.load(f)["embedding"]
            except (OSError, json.JSONDecodeError, KeyError):
                # Treat any corruption as a miss; will refetch and overwrite atomically.
                pass

    if verbose:
        print(f"[fetch] model={model} text={text[:60]!r}", file=sys.stderr)
    emb = _fetch_embedding(text, model, base_url, api_key, timeout)

    if not no_cache:
        atomic_write_json(
            _cache_path(model, text, cache_root),
            {"model": model, "text": text, "embedding": emb},
        )
    return emb


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _tokenize(text):
    return re.findall(r"\w+", text.lower())


# ---------------------------------------------------------------------------
# BERTscore-style metrics (embedding-based)
# ---------------------------------------------------------------------------

def bertscore_sentence_cosine(reference, candidate, **emb_kw):
    """Coarse: cosine sim of full-sentence embeddings."""
    er = get_embedding(reference, **emb_kw)
    ec = get_embedding(candidate, **emb_kw)
    # Clamp to [0, 1] for downstream weighted-averaging — cosine can be slightly negative
    # for unrelated text, which would otherwise penalize the combined score oddly.
    return max(0.0, cosine(er, ec))


def bertscore_token_greedy(reference, candidate, **emb_kw):
    """BERTscore-style: embed each token, greedy max-cosine P/R/F1.

    Caveat: real BERTscore embeds tokens *in context*. With a sentence-embeddings
    API each token is embedded in isolation, so this is closer to a static-word-vector
    F1 than to the paper. Useful as a sanity signal, not as a published number.
    """
    ref_toks = _tokenize(reference)
    cand_toks = _tokenize(candidate)
    if not ref_toks or not cand_toks:
        return 0.0
    ref_emb = [get_embedding(t, **emb_kw) for t in ref_toks]
    cand_emb = [get_embedding(t, **emb_kw) for t in cand_toks]
    precision = sum(max(cosine(c, r) for r in ref_emb) for c in cand_emb) / len(cand_emb)
    recall = sum(max(cosine(r, c) for c in cand_emb) for r in ref_emb) / len(ref_emb)
    if precision + recall <= 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# COMET / COMET-QE via the unbabel-comet Python API
# ---------------------------------------------------------------------------
# The model is heavy (a few GB), so we load it once per process and reuse.

_COMET_MODELS = {}


def _get_comet_model(model_name):
    """Lazily import comet (heavy: torch + transformers) and cache the loaded model."""
    if model_name in _COMET_MODELS:
        return _COMET_MODELS[model_name]
    try:
        import comet  # noqa: WPS433 (intentional lazy import)
    except ImportError as e:
        raise RuntimeError(
            "unbabel-comet not installed. With `uv run --script` this should happen "
            "automatically; otherwise: pip install unbabel-comet"
        ) from e
    ckpt = comet.download_model(model_name)
    model = comet.load_from_checkpoint(ckpt)
    _COMET_MODELS[model_name] = model
    return model


def _comet_predict(data, model_name, gpus, batch_size):
    model = _get_comet_model(model_name)
    out = model.predict(data, batch_size=batch_size, gpus=gpus, progress_bar=False)
    # Prediction object: .scores (list), .system_score (float).
    return float(out.scores[0])


def comet_score(source, reference, candidate, model=DEFAULT_COMET_MODEL,
                gpus=0, batch_size=8):
    if not source:
        raise RuntimeError("COMET requires a 'source' field (the original sentence).")
    return _comet_predict(
        [{"src": source, "mt": candidate, "ref": reference}],
        model_name=model, gpus=gpus, batch_size=batch_size,
    )


def comet_qe_score(source, candidate, model=DEFAULT_COMET_QE_MODEL,
                   gpus=0, batch_size=8):
    if not source:
        raise RuntimeError("COMET-QE requires a 'source' field (the original sentence).")
    return _comet_predict(
        [{"src": source, "mt": candidate}],
        model_name=model, gpus=gpus, batch_size=batch_size,
    )


# ---------------------------------------------------------------------------
# Combined score
# ---------------------------------------------------------------------------

def combine_metrics(scores, weights=WEIGHTS):
    """Weighted average over only the metrics actually present in `scores`,
    with weights renormalized so missing metrics don't silently zero the score.
    nTER is 'lower is better' — flipped to (1 - nter) before combining.
    """
    total_w = 0.0
    total = 0.0
    for k, w in weights.items():
        if k not in scores or scores[k] is None:
            continue
        v = scores[k]
        if k == "nter":
            v = max(0.0, 1.0 - v)
        total += w * v
        total_w += w
    return total / total_w if total_w > 0 else 0.0


# ---------------------------------------------------------------------------
# Pair-level evaluation
# ---------------------------------------------------------------------------

def evaluate_pair(ref, cand, *, source=None, le=None,
                  selected, emb_kw, bertscore_mode,
                  comet_model, comet_qe_model, comet_gpus):
    """Compute the requested metrics for a single (ref, cand) pair.

    `selected` is a set of metric names. `le` is the optional human linguist score
    (0-100, will be normalized to 0-1 before combining).
    """
    out = {}

    if "bleu" in selected:
        out["bleu"] = surface_metrics.calculate_bleu(ref, cand)
    if "chrf_plus" in selected:
        out["chrf_plus"] = surface_metrics.calculate_chrf_plus(ref, cand)
    if "nter" in selected:
        out["nter"] = surface_metrics.calculate_nter(ref, cand)
    if "bertscore" in selected:
        if bertscore_mode == "token-greedy":
            out["bertscore"] = bertscore_token_greedy(ref, cand, **emb_kw)
        else:
            out["bertscore"] = bertscore_sentence_cosine(ref, cand, **emb_kw)
    if "comet" in selected:
        out["comet"] = comet_score(source, ref, cand, model=comet_model, gpus=comet_gpus)
    if "comet_qe" in selected:
        out["comet_qe"] = comet_qe_score(source, cand, model=comet_qe_model, gpus=comet_gpus)
    if le is not None:
        out["le"] = le / 100.0  # normalize human 0-100 to 0-1

    out["combined"] = combine_metrics(out)
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ALL_METRICS = ("bleu", "chrf_plus", "nter", "bertscore", "comet", "comet_qe")


def _load_pairs(args):
    """Yield dicts with at least 'ref' and 'cand'. Sources: --reference/--candidate,
    --input JSONL, or stdin JSONL."""
    if args.reference is not None and args.candidate is not None:
        yield {"ref": args.reference, "cand": args.candidate,
               "source": args.source, "le": args.le}
        return

    stream = open(args.input, encoding="utf-8") if args.input else sys.stdin
    try:
        for lineno, line in enumerate(stream, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[warn] skipping line {lineno}: {e}", file=sys.stderr)
                continue
            # Accept COMET-style aliases: src -> source, mt -> cand.
            if "source" not in rec and "src" in rec:
                rec["source"] = rec["src"]
            if "cand" not in rec and "mt" in rec:
                rec["cand"] = rec["mt"]
            if "ref" not in rec or "cand" not in rec:
                print(f"[warn] line {lineno} missing 'ref'/'cand' (or 'mt'), skipping",
                      file=sys.stderr)
                continue
            yield rec
    finally:
        if stream is not sys.stdin:
            stream.close()


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Input modes
    p.add_argument("--reference", "-r", help="Reference translation (one-shot mode).")
    p.add_argument("--candidate", "-c", help="Candidate translation (one-shot mode).")
    p.add_argument("--source", "-s", help="Source sentence (needed for COMET/COMET-QE).")
    p.add_argument("--le", type=float, help="Linguist Evaluation score 0-100 (one-shot).")
    p.add_argument("--input", "-i", help="JSONL file with {ref, cand, [source, le]} per line.")

    # Metric selection
    p.add_argument(
        "--metrics", "-m", default="bleu,chrf_plus,nter,bertscore",
        help=f"Comma-separated subset of {ALL_METRICS} or 'all'. "
             "COMET/COMET-QE are off by default because they need the comet-score binary.",
    )
    p.add_argument(
        "--bertscore-mode", choices=("sentence-cosine", "token-greedy"),
        default="sentence-cosine",
        help="How to approximate BERTscore via the embeddings API.",
    )

    # Embedding endpoint
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help="Embedding model name (default: %(default)s).")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL,
                   help="OpenAI-compatible base URL (default: %(default)s).")
    p.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"),
                   help="API key. Defaults to $OPENAI_API_KEY. 'dummy' is fine for Ollama.")
    p.add_argument("--timeout", type=float, default=60.0)

    # COMET endpoints
    p.add_argument("--comet-model", default=DEFAULT_COMET_MODEL)
    p.add_argument("--comet-qe-model", default=DEFAULT_COMET_QE_MODEL)
    p.add_argument("--comet-gpus", type=int, default=0)

    # Cache
    p.add_argument("--cache-dir", help="Override XDG cache dir for embeddings.")
    p.add_argument("--no-cache", action="store_true", help="Disable embedding cache.")

    # Output
    p.add_argument("--output", "-o", help="Write JSONL results here. Defaults to stdout.")
    p.add_argument("--verbose", "-v", action="store_true")

    args = p.parse_args(argv)

    # Resolve selected metrics
    if args.metrics.strip() == "all":
        selected = set(ALL_METRICS)
    else:
        selected = {m.strip() for m in args.metrics.split(",") if m.strip()}
        unknown = selected - set(ALL_METRICS)
        if unknown:
            p.error(f"unknown metrics: {sorted(unknown)}; valid: {ALL_METRICS}")

    needs_source = {"comet", "comet_qe"} & selected
    cache_root = cache_dir(args.cache_dir)

    emb_kw = dict(
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        timeout=args.timeout,
        cache_root=cache_root,
        no_cache=args.no_cache,
        verbose=args.verbose,
    )

    out_stream = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        for rec in _load_pairs(args):
            if needs_source and not rec.get("source"):
                print(f"[warn] skipping pair (missing 'source' required by {needs_source}): "
                      f"{rec.get('ref','')[:50]!r}", file=sys.stderr)
                continue
            try:
                scores = evaluate_pair(
                    rec["ref"], rec["cand"],
                    source=rec.get("source"),
                    le=rec.get("le"),
                    selected=selected,
                    emb_kw=emb_kw,
                    bertscore_mode=args.bertscore_mode,
                    comet_model=args.comet_model,
                    comet_qe_model=args.comet_qe_model,
                    comet_gpus=args.comet_gpus,
                )
            except (urlerror.URLError, RuntimeError) as e:
                print(f"[error] {e}", file=sys.stderr)
                scores = {"error": str(e)}
            out_rec = {**rec, "scores": scores}
            out_stream.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
            out_stream.flush()
    finally:
        if out_stream is not sys.stdout:
            out_stream.close()


if __name__ == "__main__":
    main()
