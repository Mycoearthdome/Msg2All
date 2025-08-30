#!/usr/bin/env python3
"""
Translate a document into every language supported by Google Cloud Translation v3.
- Lists supported languages dynamically
- Detects source language
- Translates concurrently with live progress
- Saves one output file per language

Usage:
  python translate_all.py --project YOUR_PROJECT_ID --input /path/to/input.txt --outdir out
"""

from __future__ import annotations
import argparse
import concurrent.futures
import os
import pathlib
import textwrap
from typing import Iterable, List, Tuple

from google.cloud import translate_v3 as translate

# -----------------------------
# Helpers
# -----------------------------
def chunk_text(text: str, max_chars: int = 4500) -> List[str]:
    """Conservative chunker to avoid per-request size limits."""
    if len(text) <= max_chars:
        return [text]
    chunks, buf = [], []
    count = 0
    for line in text.splitlines(keepends=True):
        if count + len(line) > max_chars and buf:
            chunks.append("".join(buf))
            buf, count = [], 0
        buf.append(line)
        count += len(line)
    if buf:
        chunks.append("".join(buf))
    return chunks

def ensure_outdir(path: str | os.PathLike) -> str:
    p = pathlib.Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return str(p)

# -----------------------------
# Core API wrappers
# -----------------------------
def get_client() -> translate.TranslationServiceClient:
    return translate.TranslationServiceClient()

def get_parent(project_id: str, location: str = "global") -> str:
    return f"projects/{project_id}/locations/{location}"

def list_supported_languages(client: translate.TranslationServiceClient, parent: str) -> List[translate.SupportedLanguage]:
    # You can pass display_language_code="en" if you want English names
    response = client.get_supported_languages(request={"parent": parent})
    return list(response.languages)

def detect_source_language(client: translate.TranslationServiceClient, parent: str, text: str) -> str:
    resp = client.detect_language(
        request={
            "parent": parent,
            "content": text[:5000],  # sample from the start
            "mime_type": "text/plain",
        }
    )
    return resp.languages[0].language_code  # highest confidence

def translate_chunk(
    client: translate.TranslationServiceClient,
    parent: str,
    text_chunk: str,
    target_lang: str,
    source_lang: str | None = None,
    mime_type: str = "text/plain",
    model: str | None = None,  # e.g. "general/nmt"
) -> str:
    req = {
        "parent": parent,
        "contents": [text_chunk],
        "target_language_code": target_lang,
        "mime_type": mime_type,
    }
    if source_lang:
        req["source_language_code"] = source_lang
    if model:
        req["model"] = f"projects/{parent.split('/')[1]}/locations/{parent.split('/')[3]}/models/{model}"
    resp = client.translate_text(request=req)
    return "".join(t.translated_text for t in resp.translations)

def translate_full_text(
    client: translate.TranslationServiceClient,
    parent: str,
    text: str,
    target_lang: str,
    source_lang: str | None = None,
) -> str:
    pieces = []
    for chunk in chunk_text(text):
        pieces.append(translate_chunk(client, parent, chunk, target_lang, source_lang))
    return "".join(pieces)

# -----------------------------
# Orchestration
# -----------------------------
def do_translate_all(
    project_id: str,
    input_path: str,
    outdir: str,
    include_language_names: bool = True,
    exclude: Iterable[str] = (),
    max_workers: int = 8,
) -> None:
    client = get_client()
    parent = get_parent(project_id)

    # Load input
    text = pathlib.Path(input_path).read_text(encoding="utf-8")

    # Supported languages
    supported = list_supported_languages(client, parent)
    supported_codes = [lang.language_code for lang in supported]

    # Detect source
    source_lang = detect_source_language(client, parent, text)

    # Build worklist (skip source and exclusions)
    to_translate: List[Tuple[str, str]] = []
    name_by_code = {lang.language_code: (lang.display_name or lang.language_code) for lang in supported}
    for code in supported_codes:
        if code == source_lang:
            continue
        if code in exclude:
            continue
        to_translate.append((code, name_by_code.get(code, code)))

    print(f"Detected source language: {source_lang}")
    print(f"Found {len(supported_codes)} supported languages; translating into {len(to_translate)} targets.")
    ensure_outdir(outdir)

    # Concurrent translation with live progress (as results complete)
    results = {}
    errors = {}

    def _task(lang_code: str) -> str:
        return translate_full_text(client, parent, text, lang_code, source_lang)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {ex.submit(_task, code): (code, name) for code, name in to_translate}
        completed = 0
        total = len(future_map)
        print(f"Starting translation…")
        for future in concurrent.futures.as_completed(future_map):
            lang_code, lang_name = future_map[future]
            try:
                translated = future.result()
                results[lang_code] = translated
                # Write file per language
                out_file = pathlib.Path(outdir, f"{pathlib.Path(input_path).stem}.{lang_code}.txt")
                out_file.write_text(translated, encoding="utf-8")
                completed += 1
                label = f"{lang_code}" + (f" ({lang_name})" if include_language_names and lang_name else "")
                print(f"[{completed}/{total}] ✅ {label}")
            except Exception as e:
                errors[lang_code] = str(e)
                completed += 1
                print(f"[{completed}/{total}] ❌ {lang_code} — {e}")

    # Summary
    print("\nDone.")
    if errors:
        print("Some languages failed:")
        for code, err in errors.items():
            print(f"  - {code}: {err}")
    else:
        print("All languages translated successfully.")

# -----------------------------
# CLI
# -----------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Translate a document into every language supported by Google Cloud Translation v3."
    )
    p.add_argument("--project", required=True, help="Google Cloud Project ID")
    p.add_argument("--input", required=True, help="Path to UTF-8 text file to translate")
    p.add_argument("--outdir", default="translations_out", help="Directory to write outputs")
    p.add_argument("--exclude", default="", help="Comma-separated language codes to skip (e.g. 'en,fr,ja')")
    p.add_argument("--workers", type=int, default=8, help="Max concurrent translations")
    return p.parse_args()

def main():
    args = parse_args()
    exclude = [x.strip() for x in args.exclude.split(",") if x.strip()]
    do_translate_all(
        project_id=args.project,
        input_path=args.input,
        outdir=args.outdir,
        exclude=exclude,
        max_workers=max(1, args.workers),
    )

if __name__ == "__main__":
    main()
