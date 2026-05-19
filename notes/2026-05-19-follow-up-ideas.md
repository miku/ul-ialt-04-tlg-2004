# Follow-up Ideas for LLM Translation Research

Based on the current repository state, here are some interesting next steps to deepen the understanding of LLMs and translation.

## 1. Implement an "Agentic Translation Pipeline"
The `x/agentic` directory is currently empty of code. A multi-step pipeline can significantly improve quality over a single-shot translation.
**Proposed Workflow:**
1. **Draft:** Initial translation using a specialized model (e.g., `translategemma`).
2. **Critique:** Use a larger general-purpose model (e.g., Llama 3.1 or GPT-4) to identify errors in nuance, grammar, or terminology.
3. **Refine:** Feed the draft and critique back into the translation model for a second pass.
4. **Verify:** Check if glossary terms from `x/terminology/Glossary-Computing.md` are correctly used.

## 2. Automated Quality Evaluation (LLM-as-a-Judge)
Implement a script that automates the "Vibe Check" mentioned in the README.
- **Implementation:** create a script that takes a source text, generates translations from 3 different models (e.g., `translategemma`, `HY-MT1.5`, and a generic `Llama-3`), and then uses a "Judge LLM" to rank them based on a rubric (accuracy, fluency, style).
- **Metric:** Compare the LLM judge's ranking with a human's ranking to see the correlation.

## 3. Few-Shot Prompting Experiment
The current `generate_prompt.py` uses zero-shot templates.
- **Experiment:** Create a "few-shot" version of the prompt generator that injects 3-5 high-quality translation pairs (examples) before the actual text to be translated.
- **Comparison:** Test if few-shot prompting on a generic model (e.g., Qwen) outperforms a specialized model (e.g., `translategemma`) on a specific domain (like Computing).

## 4. Terminology Constraint Testing
Expand the `x/terminology` experiments.
- **Idea:** Create a "Stress Test" for glossary adherence. Provide a text with ambiguous terms and a glossary that forces a specific (perhaps non-obvious) translation.
- **Code:** A script that calculates "Glossary Adherence Rate" (percentage of glossary terms correctly translated in the output).

## 5. Context Window Analysis
Since `translategemma` has a limited context (2K), explore how different chunking strategies affect translation consistency.
- **Experiment:** Translate a long document (like the PDFs in `static/`) using:
    - Simple sentence-by-sentence translation.
    - Overlapping window translation.
    - Recursive summarization (summarize previous chunks to provide context for the current chunk).
