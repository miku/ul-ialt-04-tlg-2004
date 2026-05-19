#!/usr/bin/env python3
"""
Self-contained implementation of common translation and text similarity metrics.
Implemented in pure Python without external dependencies.
"""

import collections
import math
import re
import sys

def tokenize(text):
    """Simple whitespace and punctuation tokenizer."""
    return re.findall(r'\w+', text.lower())

def jaccard_similarity(set1, set2):
    """Calculates the Jaccard similarity coefficient between two sets."""
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0.0

def n_grams(tokens, n):
    """Generates n-grams from a list of tokens."""
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

def calculate_bleu(reference, candidate):
    """
    A simplified BLEU (Bilingual Evaluation Understudy) implementation.
    Calculates precision for n-grams (1 to 4) and applies a simple brevity penalty.
    """
    ref_tokens = tokenize(reference)
    cand_tokens = tokenize(candidate)
    
    if not cand_tokens:
        return 0.0

    # BLEU is usually calculated over a corpus. For a single sentence,
    # n-grams higher than the sentence length will naturally be 0.
    # We only calculate precisions for n up to the length of the shorter string.
    max_n = min(4, len(ref_tokens), len(cand_tokens))
    if max_n == 0:
        return 0.0

    precisions = []
    for n in range(1, max_n + 1):
        ref_ngrams = n_grams(ref_tokens, n)
        cand_ngrams = n_grams(cand_tokens, n)
        
        if not cand_ngrams:
            precisions.append(0.0)
            continue
            
        # Count matches with clipping (standard BLEU)
        matches = 0
        ref_counts = collections.Counter(ref_ngrams)
        cand_counts = collections.Counter(cand_ngrams)
        
        for ngram, count in cand_counts.items():
            matches += min(count, ref_counts[ngram])
            
        precisions.append(matches / len(cand_ngrams))

    # Geometric mean of precisions
    # If we didn't reach 4-grams, we only average over the n-grams we actually calculated
    geom_mean = 1.0
    for p in precisions:
        smoothed_p = p if p > 0 else 0.0001 
        geom_mean *= smoothed_p
    
    geom_mean = geom_mean ** (1 / len(precisions))

    # Brevity Penalty
    r = len(ref_tokens)
    c = len(cand_tokens)
    bp = 1.0 if c >= r else math.exp(1 - r/c)

    return bp * geom_mean

def calculate_rouge_n(reference, candidate, n=1):
    """
    Simplified ROUGE-N (Recall-Oriented Understudy for Gisting Evaluation).
    Focuses on recall: how many n-grams of the reference are present in the candidate.
    """
    ref_tokens = tokenize(reference)
    cand_tokens = tokenize(candidate)
    
    ref_ngrams = n_grams(ref_tokens, n)
    cand_ngrams = n_grams(cand_tokens, n)

    if not ref_ngrams:
        return 0.0

    ref_counts = collections.Counter(ref_ngrams)
    cand_counts = collections.Counter(cand_ngrams)

    # Clipped matching: a candidate ngram can only be credited up to its count in the reference.
    matches = sum(min(count, cand_counts[ngram]) for ngram, count in ref_counts.items())
    return matches / len(ref_ngrams)

def calculate_chrf_plus(reference, candidate, beta=2):
    """
    Simplified CHrF++ (Character n-gram F-score).
    Computes F-beta over character n-grams (1-6) and word n-grams (1-2) separately,
    then averages. Beta=2 matches Popović's chrF / chrF++ definition (recall-weighted).
    """
    def get_char_ngrams(text, n):
        return [text[i:i+n] for i in range(len(text)-n+1)]

    def get_word_ngrams(text, n):
        tokens = tokenize(text)
        return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

    def f_beta(matches, total_cand, total_ref):
        if total_cand == 0 or total_ref == 0:
            return 0.0
        p = matches / total_cand
        r = matches / total_ref
        if p + r == 0:
            return 0.0
        b2 = beta * beta
        return (1 + b2) * p * r / (b2 * p + r)

    def ngram_f(ngram_fn, ns):
        # Average F-beta across the n-gram orders in `ns`.
        scores = []
        for n in ns:
            ref_ngrams = ngram_fn(reference, n)
            cand_ngrams = ngram_fn(candidate, n)
            ref_counts = collections.Counter(ref_ngrams)
            cand_counts = collections.Counter(cand_ngrams)
            matches = sum(min(c, ref_counts[g]) for g, c in cand_counts.items())
            scores.append(f_beta(matches, len(cand_ngrams), len(ref_ngrams)))
        return sum(scores) / len(scores) if scores else 0.0

    char_f = ngram_f(get_char_ngrams, range(1, 7))
    word_f = ngram_f(get_word_ngrams, range(1, 3))

    return (char_f + word_f) / 2


def main():
    # Example cases
    test_cases = [
        {
            "ref": "The cat sits on the mat",
            "cand": "The cat is sitting on the mat",
        },
        {
            "ref": "Hello world",
            "cand": "Hello world",
        },
        {
            "ref": "This is a complex translation test",
            "cand": "Something completely different",
        },
    ]

    print(f"{'Reference':<35} | {'Candidate':<35} | {'Jac':<6} | {'BLEU':<6} | {'ROUGE-1':<6} | {'CHrF++':<6}")
    print("-" * 135)

    for case in test_cases:
        ref = case["ref"]
        cand = case["cand"]
        
        # Jaccard
        set_ref = set(tokenize(ref))
        set_cand = set(tokenize(cand))
        jac = jaccard_similarity(set_ref, set_cand)
        
        # BLEU
        bleu = calculate_bleu(ref, cand)
        
        # ROUGE-1
        rouge1 = calculate_rouge_n(ref, cand, n=1)
        
        # CHrF++
        chrf = calculate_chrf_plus(ref, cand)
        
        print(f"{ref:<35} | {cand:<35} | {jac:.3f} | {bleu:.3f} | {rouge1:.3f} | {chrf:.3f}")

if __name__ == "__main__":
    main()
