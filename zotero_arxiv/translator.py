from __future__ import annotations

from typing import Optional

import requests

from .config import TranslationConfig


def _call_deepseek(
    text: str,
    api_key: str,
    model: str,
    base_url: str,
    source_lang: str,
    target_lang: str,
) -> Optional[str]:
    if not text.strip():
        return ""

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional bilingual translator for quantum physics and "
                    "quantum computing papers. Translate the user message from "
                    f"{source_lang} to natural, technical {target_lang}. "
                    "Preserve all equations, symbols, arXiv IDs, and technical terms "
                    "(e.g., VQE, QAOA, transmon) in Latin characters. "
                    "Output only the translated text, no explanations."
                ),
            },
            {"role": "user", "content": text},
        ],
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return None
    return choices[0].get("message", {}).get("content", "")


def _enabled(tcfg: TranslationConfig) -> bool:
    return (tcfg.api_key or "").strip() != "" and (tcfg.provider or "").strip().lower() == "deepseek"


def translate_en_to_target(text: str, tcfg: TranslationConfig) -> str:
    """
    Translate English text to `tcfg.target_lang` using DeepSeek.

    If translation isn't configured (no api_key), returns the original text.
    """
    text = text or ""
    if not _enabled(tcfg):
        return text

    # Fill placeholders in prompt template.
    # (We keep the prompt logic here to avoid embedding target_lang in multiple places.)
    try:
        out = _call_deepseek(
            text,
            tcfg.api_key,
            tcfg.model,
            tcfg.base_url,
            tcfg.source_lang,
            tcfg.target_lang,
        )
    except Exception:
        return text
    return out or text


def translate_title_en_to_target(title: str, tcfg: TranslationConfig) -> str:
    return translate_en_to_target(title, tcfg)

