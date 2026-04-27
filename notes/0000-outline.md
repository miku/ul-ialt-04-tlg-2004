# Outline

> 04-TLG-2004, **Probleme und Methoden der Übersetzung** (2 SWS)

> Im Mittelpunkt dieses Seminars stehen typische Herausforderungen beim
> Übersetzen, insbesondere bei Fachtexten. Die Teilnehmenden lernen,
> Texteigenschaften systematisch zu erkennen, Merkmale von Textsorten zu
> unterscheiden und Übersetzungsstrategien begründet anzuwenden (EN↔DE).  Wir
> arbeiten mit Korpora und digitalen Ressourcen zur Qualitätssicherung und
> beziehen KI‑basierte Übersetzungssysteme ein.

> Wir analysieren Stärken und Schwächen von LLM-Übersetzungen, entwickeln
> linguistisch fundierte Prompts und führen Evaluationsverfahren durch. Ein
> abschließendes Praxisprojekt ermöglicht die vertiefte Anwendung der
> erarbeiteten Methoden.

## Abstract

We introduce open weights large language models and some hosting options. The
participants will learn about the typical API boundary, hosting options and
client programs. We may install a desktop application or will use web
interfaces to alternatives hosting sites. We will learn about the most
important openly available models. In the context of translation, we will
describe some important benchmarks and evaluations, we will see, how prompts
influence the outcome and how one can build up a prompt library. Finally, we
also want to get a glipse into the agentic world. This may be more of an
outlook, in that it will be more of a demonstration and description of the
agentic tool use paradigm.

In about 90 minutes, the students should get a good overview of the current
local large language model landscape with an emphasis on translation,
especially for text using technical terms.

## LLM reflections

### Initial Assessment & Recommendations

**Timing Reality Check**: 90 minutes is ambitious for the scope described. Consider:
- Core focus: Local LLM setup + translation-specific prompting + one hands-on evaluation
- Move "agentic workflows" to optional/outlook material or a follow-up session
- Suggested time split: 20min theory, 40min hands-on, 20min evaluation/discussion, 10min wrap-up

**Key Content Additions to Consider**:

1. **Model Recommendations for Translation**:
   - Qwen2.5-72B-Instruct (strong multilingual, good EN↔DE)
   - Llama-3.1-70B-Instruct (solid performance, widely available)
   - Smaller options for local hardware: Qwen2.5-7B, Mistral-7B-Instruct-v0.3
   - Specialized: NLLB (No Language Left Behind) for translation-specific tasks

2. **Essential Papers & Reading**:
   - *"Large Language Models are State-of-the-Art Translators"* (Zhu et al., 2024) - arXiv:2401.01319
   - *"Prompting Large Language Models for Machine Translation"* (Briggs et al.)
   - *"The Curious Case of Hallucinations in LLM Translation"* - important for critical discussion
   - Flores-101 evaluation dataset paper (Goyal et al., 2022)
   - *"Translation Quality Estimation with LLMs"* - emerging area

3. **Datasets to Inspect/Evaluate**:
   - **Flores-101**: 101 languages, dev/devtest splits - good for quick evaluation
   - **WMT23/24 shared task data**: Professional translation references
   - **TED2020**: Parallel corpus, domain variety
   - **EuroParl**: European parliament proceedings (EN↔DE rich)
   - Suggestion: Pre-download a small subset (e.g., 50-100 sentences) for in-session evaluation

4. **Practical Topics to Cover**:
   - **Terminology consistency**: How to prompt LLMs to maintain term consistency across documents
   - **Domain adaptation**: Few-shot examples for technical texts
   - **Quality estimation**: Using LLMs to score their own translations (with caveats)
   - **Post-editing workflows**: LLM output + human refinement
   - **Common failure modes**: False friends, cultural references, idioms, technical term hallucination

5. **Hands-On Exercise Ideas**:
   - Compare 3 different models on the same 5 technical sentences
   - Build a prompt template for medical/legal/technical translation
   - Run a mini-evaluation: LLM translation vs. reference using COMET or simple accuracy
   - Inspect attention patterns or token probabilities (if using accessible tools)

6. **Tools to Demo**:
   - **Ollama**: Simplest local setup (`ollama run qwen2.5:7b`)
   - **LM Studio**: GUI for model download and chat
   - **llama.cpp**: For advanced users, quantization discussion
   - **Open WebUI**: Self-hosted ChatGPT-like interface
   - **Argo Translate** + LLM hybrid approaches

7. **Critical Discussion Points**:
   - When NOT to use LLMs for translation (legal certification, high-stakes domains)
   - Data privacy concerns with cloud vs. local models
   - Bias in training data affecting translation quality
   - The "uncanny valley" of fluent-but-wrong translations
   - Impact on the translation profession

8. **Prompt Library Starter**:
   ```
   You are a professional translator specializing in [DOMAIN]. 
   Translate the following text from [SOURCE] to [TARGET].
   Maintain technical terminology consistency.
   Do not add explanations, output only the translation.
   
   Key terms to preserve: [TERM1], [TERM2], ...
   
   Text: [INPUT]
   ```

### Open Questions for Development
- What hardware can students reasonably be expected to have? (determines model size recommendations)
- Should we prepare a Colab notebook as backup for those without local GPU?
- Do we want to include any German-specific translation challenges (case, compound nouns, word order)?
- Should we contrast LLM translation with traditional NMT (e.g., DeepL, Google Translate)?
