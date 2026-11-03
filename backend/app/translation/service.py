"""Translation Service for Janvaani.

Orchestrates Bhashini NMT (ai4bharat/indictrans-v2-all-gpu) as primary
with automated Gemini fallback and persistent 2-tier caching for ultra-fast,
reliable translation of schemes, eligibility rules, and citizen interface.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.config import PROJECT_ROOT

# Ensure environment is loaded
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from google import genai
from google.genai import types

from app.translation.bhashini_translation_client import (
    BhashiniTranslationClient,
    BhashiniTranslationError,
)

logger = logging.getLogger(__name__)

# Language Name Mapping for Prompt Quality
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "gu": "Gujarati",
    "mr": "Marathi",
    "or": "Odia",
    "pa": "Punjabi",
    "as": "Assamese",
}

# Cache directory & file
CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"
CACHE_FILE = CACHE_DIR / "translations_cache.json"


class TranslationService:
    def __init__(self) -> None:
        self.bhashini_client = BhashiniTranslationClient()
        self._cache: dict[str, str] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
        except Exception as exc:
            logger.warning("Failed to load translation cache: %s", exc)

    def _persist_cache(self) -> None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("Failed to persist translation cache: %s", exc)

    def _cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        return f"{source_lang}:{target_lang}:{text.strip()}"

    def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "en",
    ) -> str:
        """Translate a single string from source_language to target_language."""
        if not text or not text.strip():
            return text

        target_lang = target_language.lower().strip()
        source_lang = source_language.lower().strip()

        if target_lang == source_lang or target_lang == "en":
            return text

        cache_key = self._cache_key(text, source_lang, target_lang)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Batch translate handles the logic and fallbacks cleanly
        results = self.translate_batch([text], target_lang, source_lang)
        if results:
            return results[0]
        return text

    def translate_batch(
        self,
        texts: list[str],
        target_language: str,
        source_language: str = "en",
    ) -> list[str]:
        """Translate a list of strings with Bhashini NMT primary + Gemini fallback."""
        if not texts:
            return []

        target_lang = target_language.lower().strip()
        source_lang = source_language.lower().strip()

        if target_lang == source_lang or target_lang == "en":
            return texts

        # Identify which strings are cached vs uncached
        results: list[str | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for idx, text in enumerate(texts):
            if not text or not text.strip():
                results[idx] = text
                continue

            ckey = self._cache_key(text, source_lang, target_lang)
            if ckey in self._cache:
                results[idx] = self._cache[ckey]
            else:
                uncached_indices.append(idx)
                uncached_texts.append(text)

        if not uncached_texts:
            return [r if r is not None else "" for r in results]

        # 1. Try Bhashini Translation First
        translated_uncached: list[str] | None = None
        try:
            translated_uncached = self.bhashini_client.translate_texts(
                uncached_texts,
                target_language=target_lang,
                source_language=source_lang,
            )
        except (BhashiniTranslationError, Exception) as exc:
            logger.info("Bhashini translation unavailable (%s); using Gemini fallback", exc)

        # 2. Resilient Gemini Fallback if Bhashini failed or returned incomplete results
        if not translated_uncached or len(translated_uncached) != len(uncached_texts):
            translated_uncached = self._gemini_translate_batch(
                uncached_texts, target_lang, source_lang
            )

        # Store in cache & populate results
        cache_updated = False
        for original_idx, trans_text, orig_text in zip(
            uncached_indices, translated_uncached, uncached_texts
        ):
            results[original_idx] = trans_text
            # Only cache if translation succeeded and produced non-identical output
            if trans_text and trans_text != orig_text:
                ckey = self._cache_key(orig_text, source_lang, target_lang)
                self._cache[ckey] = trans_text
                cache_updated = True

        if cache_updated:
            self._persist_cache()

        return [r if r is not None else "" for r in results]

    def _gemini_translate_batch(
        self,
        texts: list[str],
        target_language: str,
        source_language: str = "en",
    ) -> list[str]:
        """Translate a batch of texts using Gemini JSON mode."""
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            logger.warning("GEMINI_API_KEY not configured for translation fallback")
            return texts

        target_lang_name = LANGUAGE_NAMES.get(target_language, target_language)
        source_lang_name = LANGUAGE_NAMES.get(source_language, source_language)

        prompt = (
            f"You are an expert official government translator for Indian public schemes.\n"
            f"Translate the following list of texts from {source_lang_name} ({source_language}) into natural, "
            f"fluent, and accurate {target_lang_name} ({target_language}).\n"
            f"Preserve technical terms, numbers, scheme acronyms (like PM-KISAN, PM-JAY, APY), and official names accurately.\n\n"
            f"Input JSON array of strings to translate:\n"
            f"{json.dumps(texts, ensure_ascii=False)}\n\n"
            f"Respond ONLY with a valid JSON array of translated strings in the EXACT same order and length."
        )

        candidate_models = [
            os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-3.8-flash",
        ]

        client = genai.Client(api_key=api_key)

        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                if response and response.text:
                    cleaned_text = response.text.strip()
                    # Strip markdown block if wrapped
                    if cleaned_text.startswith("```"):
                        cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
                        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
                    parsed = json.loads(cleaned_text)
                    if isinstance(parsed, list) and len(parsed) == len(texts):
                        return [str(item) for item in parsed]
                    if isinstance(parsed, dict) and "translations" in parsed:
                        t_list = parsed["translations"]
                        if isinstance(t_list, list) and len(t_list) == len(texts):
                            return [str(item) for item in t_list]
            except Exception as exc:
                logger.warning("Gemini translation attempt with %s failed: %s", model_name, exc)
                continue

        logger.error("All Gemini translation attempts failed. Returning original texts.")
        return texts

    # --- Domain-Specific Scheme Translators ---

    def translate_scheme_summary(
        self, scheme_dict: dict[str, Any], target_language: str
    ) -> dict[str, Any]:
        """Translate scheme list items (title, authority, description)."""
        if target_language == "en":
            return scheme_dict

        translated = dict(scheme_dict)
        items_to_translate: list[str] = [
            scheme_dict.get("title") or "",
            scheme_dict.get("administering_authority") or "",
        ]

        versions = scheme_dict.get("versions", [])
        for v in versions:
            items_to_translate.append(v.get("description") or "")

        translated_items = self.translate_batch(items_to_translate, target_language)

        translated["title"] = translated_items[0]
        translated["administering_authority"] = translated_items[1]

        t_idx = 2
        new_versions = []
        for v in versions:
            new_v = dict(v)
            new_v["language"] = target_language
            new_v["description"] = translated_items[t_idx]
            t_idx += 1
            new_versions.append(new_v)
        translated["versions"] = new_versions

        return translated

    def translate_scheme_detail(
        self, scheme_dict: dict[str, Any], target_language: str
    ) -> dict[str, Any]:
        """Translate full scheme details including benefits, required documents, and application process."""
        if target_language == "en":
            return scheme_dict

        translated = dict(scheme_dict)
        texts_to_translate: list[str] = [
            scheme_dict.get("title") or "",
            scheme_dict.get("administering_authority") or "",
        ]

        # Extract textual fields from versions[0]
        v0 = scheme_dict.get("versions", [{}])[0] if scheme_dict.get("versions") else {}
        desc = v0.get("description") or ""
        texts_to_translate.append(desc)

        # Benefits (string, list, or dict)
        raw_benefits = v0.get("benefits")
        benefits_text_indices: list[int] = []
        benefits_cond_indices: list[tuple[int, int, int]] = []  # (benefit_idx, cond_idx, text_idx)
        if isinstance(raw_benefits, str):
            benefits_text_indices.append(len(texts_to_translate))
            texts_to_translate.append(raw_benefits)
        elif isinstance(raw_benefits, list):
            for b_idx, b in enumerate(raw_benefits):
                if isinstance(b, str):
                    benefits_text_indices.append(len(texts_to_translate))
                    texts_to_translate.append(b)
                elif isinstance(b, dict):
                    if b.get("description"):
                        benefits_text_indices.append(len(texts_to_translate))
                        texts_to_translate.append(b["description"])
                    if isinstance(b.get("conditions"), list):
                        for c_idx, c in enumerate(b["conditions"]):
                            if isinstance(c, str) and c.strip():
                                benefits_cond_indices.append((b_idx, c_idx, len(texts_to_translate)))
                                texts_to_translate.append(c)

        # Required documents (list of strings or dicts)
        raw_docs = v0.get("required_documents") or []
        doc_text_indices: list[int] = []
        doc_cond_indices: list[tuple[int, int]] = []  # (doc_idx, text_idx)
        if isinstance(raw_docs, list):
            for d_idx, d in enumerate(raw_docs):
                if isinstance(d, str):
                    doc_text_indices.append(len(texts_to_translate))
                    texts_to_translate.append(d)
                elif isinstance(d, dict):
                    name = d.get("name") or d.get("document_type") or d.get("title") or ""
                    doc_text_indices.append(len(texts_to_translate))
                    texts_to_translate.append(name)
                    if d.get("condition"):
                        doc_cond_indices.append((d_idx, len(texts_to_translate)))
                        texts_to_translate.append(d["condition"])

        # Application process (string or list of step dicts)
        raw_process = v0.get("application_process") or ""
        process_index = -1
        proc_step_indices: list[tuple[int, str, int]] = []  # (step_idx, field_key, text_idx)
        if isinstance(raw_process, str) and raw_process.strip():
            process_index = len(texts_to_translate)
            texts_to_translate.append(raw_process)
        elif isinstance(raw_process, list):
            for s_idx, step in enumerate(raw_process):
                if isinstance(step, str):
                    proc_step_indices.append((s_idx, "text", len(texts_to_translate)))
                    texts_to_translate.append(step)
                elif isinstance(step, dict):
                    if step.get("description"):
                        proc_step_indices.append((s_idx, "description", len(texts_to_translate)))
                        texts_to_translate.append(step["description"])
                    if step.get("title"):
                        proc_step_indices.append((s_idx, "title", len(texts_to_translate)))
                        texts_to_translate.append(step["title"])

        # Run translation
        translated_texts = self.translate_batch(texts_to_translate, target_language)

        translated["title"] = translated_texts[0]
        translated["administering_authority"] = translated_texts[1]

        if scheme_dict.get("versions"):
            new_v0 = dict(v0)
            new_v0["language"] = target_language
            new_v0["description"] = translated_texts[2]

            # Rebuild benefits
            b_cursor = 0
            if isinstance(raw_benefits, str):
                new_v0["benefits"] = translated_texts[benefits_text_indices[0]]
            elif isinstance(raw_benefits, list):
                new_b_list = []
                for b_idx, b in enumerate(raw_benefits):
                    if isinstance(b, str):
                        new_b_list.append(translated_texts[benefits_text_indices[b_cursor]])
                        b_cursor += 1
                    elif isinstance(b, dict):
                        b_copy = dict(b)
                        if b.get("description"):
                            b_copy["description"] = translated_texts[benefits_text_indices[b_cursor]]
                            b_cursor += 1
                        matching_conds = [c for c in benefits_cond_indices if c[0] == b_idx]
                        if matching_conds and isinstance(b.get("conditions"), list):
                            new_conds = list(b["conditions"])
                            for _, c_idx, t_idx in matching_conds:
                                new_conds[c_idx] = translated_texts[t_idx]
                            b_copy["conditions"] = new_conds
                        new_b_list.append(b_copy)
                    else:
                        new_b_list.append(b)
                new_v0["benefits"] = new_b_list

            # Rebuild required documents
            d_cursor = 0
            if isinstance(raw_docs, list):
                new_doc_list = []
                for d_idx, d in enumerate(raw_docs):
                    if isinstance(d, str):
                        new_doc_list.append(translated_texts[doc_text_indices[d_cursor]])
                        d_cursor += 1
                    elif isinstance(d, dict):
                        d_copy = dict(d)
                        key_name = "name" if "name" in d else "document_type" if "document_type" in d else "title"
                        d_copy[key_name] = translated_texts[doc_text_indices[d_cursor]]
                        d_cursor += 1
                        matching_cond = next((c for c in doc_cond_indices if c[0] == d_idx), None)
                        if matching_cond:
                            d_copy["condition"] = translated_texts[matching_cond[1]]
                        new_doc_list.append(d_copy)
                    else:
                        new_doc_list.append(d)
                new_v0["required_documents"] = new_doc_list

            # Rebuild application process
            if process_index != -1:
                new_v0["application_process"] = translated_texts[process_index]
            elif isinstance(raw_process, list):
                new_proc_list = []
                for s_idx, step in enumerate(raw_process):
                    if isinstance(step, str):
                        step_t = next((t_idx for idx, key, t_idx in proc_step_indices if idx == s_idx and key == "text"), None)
                        new_proc_list.append(translated_texts[step_t] if step_t is not None else step)
                    elif isinstance(step, dict):
                        step_copy = dict(step)
                        for idx, key, t_idx in proc_step_indices:
                            if idx == s_idx:
                                step_copy[key] = translated_texts[t_idx]
                        new_proc_list.append(step_copy)
                    else:
                        new_proc_list.append(step)
                new_v0["application_process"] = new_proc_list

            translated["versions"] = [new_v0]

        return translated

    def translate_eligibility_result(
        self, result_dict: dict[str, Any], target_language: str
    ) -> dict[str, Any]:
        """Translate eligibility summary and rule explanations."""
        if target_language == "en":
            return result_dict

        translated = dict(result_dict)
        texts_to_translate: list[str] = [result_dict.get("summary") or ""]

        conditions = result_dict.get("conditions", [])
        for cond in conditions:
            texts_to_translate.append(cond.get("explanation") or "")

        translated_texts = self.translate_batch(texts_to_translate, target_language)

        translated["summary"] = translated_texts[0]

        new_conditions = []
        for idx, cond in enumerate(conditions):
            c_copy = dict(cond)
            c_copy["explanation"] = translated_texts[1 + idx]
            new_conditions.append(c_copy)
        translated["conditions"] = new_conditions

        return translated

    def translate_readiness_result(
        self, result_dict: dict[str, Any], target_language: str
    ) -> dict[str, Any]:
        """Translate application readiness scheme title, notes, and checklist items."""
        if target_language == "en":
            return result_dict

        translated = dict(result_dict)
        texts_to_translate: list[str] = [result_dict.get("scheme_title") or ""]

        checklist = result_dict.get("checklist", [])
        for item in checklist:
            texts_to_translate.append(item.get("document_type") or "")
            texts_to_translate.append(item.get("note") or "")

        translated_texts = self.translate_batch(texts_to_translate, target_language)

        translated["scheme_title"] = translated_texts[0]

        new_checklist = []
        cursor = 1
        for item in checklist:
            item_copy = dict(item)
            item_copy["document_type"] = translated_texts[cursor]
            item_copy["note"] = translated_texts[cursor + 1]
            cursor += 2
            new_checklist.append(item_copy)
        translated["checklist"] = new_checklist

        return translated


# Global singleton instance
translation_service = TranslationService()
