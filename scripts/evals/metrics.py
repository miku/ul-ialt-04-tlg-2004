#!/usr/bin/env python3
"""
Self-contained implementation of common translation and text similarity metrics.
Implemented in pure Python without external dependencies.
"""

import collections
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
    bp = 1.0 if c >= r else (2.718281828459 ** (1 - r/c))

    return bp * geom_mean

def calculate_rouge_n(reference, candidate, n=1):
    """
    Simplified ROUGE-N (Recall-Oriented Understudy for Gisting Evaluation).
    Focuses on recall: how many n-grams of the reference are present in the candidate.
    """
    ref_tokens = tokenize(reference)
    cand_tokens = tokenize(candidate)
    
    ref_ngrams = n_grams(ref_tokens, n)
    cand_ngrams = set(n_grams(cand_tokens, n))
    
    if not ref_ngrams:
        return 0.0
        
    matches = sum(1 for ngram in ref_ngrams if ngram in cand_ngrams)
    return matches / len(ref_ngrams)

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

    print(f"{'Reference':<35} | {'Candidate':<35} | {'Jac':<6} | {'BLEU':<6} | {'ROUGE-1':<6}")
    print("-" * 120)

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
        
        print(f"{ref:<35} | {cand:<35} | {jac:.3f} | {bleu:.3f} | {rouge1:.3f}")

if __name__ == "__main__":
    main()
