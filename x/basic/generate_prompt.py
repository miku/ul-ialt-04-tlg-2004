#!/usr/bin/env python3
"""Generate a translation prompt from source to target language.

Accepts ISO 639-1 two-letter codes (e.g. 'de', 'hy') or full English
language names (e.g. 'german', 'armenian').

Usage:
    python gen_prompt.py -f de -t en
    python gen_prompt.py --from german --to armenian
    echo "Hallo Welt" | python gen_prompt.py -f de -t en
    python gen_prompt.py -f de -t en input.txt
    python gen_prompt.py -f de -t hy --model hy input.txt
    python gen_prompt.py -f de -t en --model google input.txt
"""

import argparse
import os
import sys

# Complete ISO 639-1 two-letter code → English language name mapping
_ISO639_1 = {
    "aa": "Afar",
    "ab": "Abkhazian",
    "af": "Afrikaans",
    "ak": "Akan",
    "am": "Amharic",
    "an": "Aragonese",
    "ar": "Arabic",
    "as": "Assamese",
    "av": "Avaric",
    "ay": "Aymara",
    "az": "Azerbaijani",
    "ba": "Bashkir",
    "be": "Belarusian",
    "bg": "Bulgarian",
    "bh": "Bihari languages",
    "bi": "Bislama",
    "bm": "Bambara",
    "bn": "Bengali",
    "bo": "Tibetan",
    "br": "Breton",
    "bs": "Bosnian",
    "ca": "Catalan",
    "ce": "Chechen",
    "ch": "Chamorro",
    "co": "Corsican",
    "cr": "Cree",
    "cs": "Czech",
    "cu": "Church Slavic",
    "cv": "Chuvash",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "dv": "Divehi",
    "dz": "Dzongkha",
    "ee": "Ewe",
    "el": "Greek",
    "en": "English",
    "eo": "Esperanto",
    "es": "Spanish",
    "et": "Estonian",
    "eu": "Basque",
    "fa": "Persian",
    "ff": "Fulah",
    "fi": "Finnish",
    "fj": "Fijian",
    "fo": "Faroese",
    "fr": "French",
    "fy": "Western Frisian",
    "ga": "Irish",
    "gd": "Scottish Gaelic",
    "gl": "Galician",
    "gn": "Guarani",
    "gu": "Gujarati",
    "gv": "Manx",
    "ha": "Hausa",
    "he": "Hebrew",
    "hi": "Hindi",
    "ho": "Hiri Motu",
    "hr": "Croatian",
    "ht": "Haitian",
    "hu": "Hungarian",
    "hy": "Armenian",
    "hz": "Herero",
    "ia": "Interlingua",
    "id": "Indonesian",
    "ie": "Interlingue",
    "ig": "Igbo",
    "ii": "Sichuan Yi",
    "ik": "Inupiaq",
    "io": "Ido",
    "is": "Icelandic",
    "it": "Italian",
    "iu": "Inuktitut",
    "ja": "Japanese",
    "jv": "Javanese",
    "ka": "Georgian",
    "kg": "Kongo",
    "ki": "Kikuyu",
    "kj": "Kuanyama",
    "kk": "Kazakh",
    "kl": "Kalaallisut",
    "km": "Central Khmer",
    "kn": "Kannada",
    "ko": "Korean",
    "kr": "Kanuri",
    "ks": "Kashmiri",
    "ku": "Kurdish",
    "kv": "Komi",
    "kw": "Cornish",
    "ky": "Kirghiz",
    "la": "Latin",
    "lb": "Luxembourgish",
    "lg": "Ganda",
    "li": "Limburgan",
    "ln": "Lingala",
    "lo": "Lao",
    "lt": "Lithuanian",
    "lu": "Luba-Katanga",
    "lv": "Latvian",
    "mg": "Malagasy",
    "mh": "Marshallese",
    "mi": "Maori",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mn": "Mongolian",
    "mr": "Marathi",
    "ms": "Malay",
    "mt": "Maltese",
    "my": "Burmese",
    "na": "Nauru",
    "nb": "Norwegian Bokmål",
    "nd": "North Ndebele",
    "ne": "Nepali",
    "ng": "Ndonga",
    "nl": "Dutch",
    "nn": "Norwegian Nynorsk",
    "no": "Norwegian",
    "nr": "South Ndebele",
    "nv": "Navajo",
    "ny": "Chichewa",
    "oc": "Occitan",
    "oj": "Ojibwa",
    "om": "Oromo",
    "or": "Oriya",
    "os": "Ossetian",
    "pa": "Panjabi",
    "pi": "Pali",
    "pl": "Polish",
    "ps": "Pashto",
    "pt": "Portuguese",
    "qu": "Quechua",
    "rm": "Romansh",
    "rn": "Rundi",
    "ro": "Romanian",
    "ru": "Russian",
    "rw": "Kinyarwanda",
    "sa": "Sanskrit",
    "sc": "Sardinian",
    "sd": "Sindhi",
    "se": "Northern Sami",
    "sg": "Sango",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sm": "Samoan",
    "sn": "Shona",
    "so": "Somali",
    "sq": "Albanian",
    "sr": "Serbian",
    "ss": "Swati",
    "st": "Southern Sotho",
    "su": "Sundanese",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "tg": "Tajik",
    "th": "Thai",
    "ti": "Tigrinya",
    "tk": "Turkmen",
    "tl": "Tagalog",
    "tn": "Tswana",
    "to": "Tonga",
    "tr": "Turkish",
    "ts": "Tsonga",
    "tt": "Tatar",
    "tw": "Twi",
    "ty": "Tahitian",
    "ug": "Uighur",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "ve": "Venda",
    "vi": "Vietnamese",
    "vo": "Volapük",
    "wa": "Walloon",
    "wo": "Wolof",
    "xh": "Xhosa",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "za": "Zhuang",
    "zh": "Chinese",
    "zu": "Zulu",
}

# Reverse lookup: lowercase English name → code
_NAME_TO_CODE = {v.lower(): k for k, v in _ISO639_1.items()}
# Also index by lowercase code for case-insensitive lookup
_CODE_LOWER = {k.lower(): k for k in _ISO639_1}

TEMPLATES = {
    "translategemma": (
        "You are a professional {source_lang} ({src_lang_code}) to {target_lang} "
        "({tgt_lang_code}) translator. Your goal is to accurately convey the meaning "
        "and nuances of the original {source_lang} text while adhering to "
        "{target_lang} grammar, vocabulary, and cultural sensitivities. Produce only "
        "the {target_lang} translation, without any additional explanations or "
        "commentary. Please translate the following {source_lang} text into "
        "{target_lang}:\n\n<<TEXT_PLACEHOLDER>>"
    ),
    "hy-mt-1.5": (
        "Translate the following segment into {target_lang}, without additional "
        "explanation.\n\n<<TEXT_PLACEHOLDER>>\n"
    ),
}

# Optional aliases that map to a canonical template name.
_MODEL_ALIASES = {
    "google": "translategemma",
    "gemma": "translategemma",
}


def resolve_template(model_input: str) -> str:
    """Resolve a model prefix (or alias prefix) to a canonical template name."""
    key = model_input.strip().lower()
    if not key:
        print("Error: --model value is empty.", file=sys.stderr)
        sys.exit(1)

    matches: set[str] = set()
    for name in TEMPLATES:
        if name.lower().startswith(key):
            matches.add(name)
    for alias, target in _MODEL_ALIASES.items():
        if alias.startswith(key):
            matches.add(target)

    if len(matches) == 1:
        return next(iter(matches))
    if not matches:
        print(
            f"Error: no template matches '{model_input}'. "
            f"Available: {', '.join(sorted(TEMPLATES))}.",
            file=sys.stderr,
        )
    else:
        print(
            f"Error: ambiguous --model '{model_input}', matches: "
            f"{', '.join(sorted(matches))}.",
            file=sys.stderr,
        )
    sys.exit(1)


def resolve_language(lang_input: str) -> tuple[str, str]:
    """Resolve a language string to (display_name, iso639_1_code).

    Accepts ISO 639-1 two-letter codes or full English language names
    (case-insensitive).
    """
    key = lang_input.strip().lower()

    # Try as an ISO 639-1 code first
    if key in _CODE_LOWER:
        real_code = _CODE_LOWER[key]
        return _ISO639_1[real_code], real_code

    # Try as a language name
    if key in _NAME_TO_CODE:
        code = _NAME_TO_CODE[key]
        return _ISO639_1[code], code

    print(
        f"Error: unrecognized language '{lang_input}'.\n"
        "Provide an ISO 639-1 two-letter code (e.g. 'de') or a full English "
        "language name (e.g. 'german').",
        file=sys.stderr,
    )
    sys.exit(1)


def build_prompt(
    template_name: str,
    src_name: str,
    src_code: str,
    tgt_name: str,
    tgt_code: str,
    text: str,
) -> str:
    """Fill the chosen prompt template with language info and the source text."""
    template = TEMPLATES[template_name]
    result = template.format(
        source_lang=src_name,
        src_lang_code=src_code,
        target_lang=tgt_name,
        tgt_lang_code=tgt_code,
    )
    result = result.replace("<<TEXT_PLACEHOLDER>>", text)
    return result


def read_text_file(filepath: str) -> str:
    """Read text from a file."""
    if not os.path.isfile(filepath):
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def read_stdin_if_piped() -> str | None:
    """Read stdin only if it's piped (not a tty) and non-empty.
    Returns None when stdin is a tty or has no content.
    """
    if sys.stdin.isatty():
        return None
    data = sys.stdin.read()
    return data if data else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a translation prompt template."
    )
    parser.add_argument(
        "-f",
        "--from",
        dest="source",
        default="de",
        help="Source language (ISO 639-1 code or English name, e.g. 'de' or 'german')",
    )
    parser.add_argument(
        "-t",
        "--to",
        dest="target",
        default="en",
        help="Target language (ISO 639-1 code or English name, e.g. 'en' or 'english')",
    )
    parser.add_argument(
        "-m",
        "--model",
        dest="model",
        default="translategemma",
        help=(
            "Template to use, matched by prefix against template names "
            f"({', '.join(sorted(TEMPLATES))}) or aliases "
            f"({', '.join(sorted(_MODEL_ALIASES))}). E.g. 'google', 'hy'."
        ),
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Optional text file whose contents fill the {text} placeholder",
    )
    args = parser.parse_args()

    template_name = resolve_template(args.model)
    src_name, src_code = resolve_language(args.source)
    tgt_name, tgt_code = resolve_language(args.target)

    # Determine the text payload: file arg wins, then piped stdin, else placeholder
    text: str = "{text}"
    if args.file:
        text = read_text_file(args.file)
    else:
        stdin_text = read_stdin_if_piped()
        if stdin_text is not None:
            text = stdin_text

    prompt = build_prompt(
        template_name, src_name, src_code, tgt_name, tgt_code, text
    )
    print(prompt)


if __name__ == "__main__":
    main()
