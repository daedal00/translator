"""
Translation via NLLB-200-distilled-600M (CTranslate2 backend).
License: CC-BY-NC 4.0 — non-commercial only. Swap model for commercial use.
"""
import asyncio
import threading
from typing import Protocol

import ctranslate2
from transformers import NllbTokenizer

# FLORES-200 language codes for NLLB
LANG_CODES: dict[str, str] = {
    "en": "eng_Latn",
    "ko": "kor_Hang",
    "es": "spa_Latn",
    "zh": "zho_Hans",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "pt": "por_Latn",
    "ar": "arb_Arab",
    "vi": "vie_Latn",
    "tl": "tgl_Latn",
}

_CACHE_MAX = 1024


class Translator(Protocol):
    async def translate(self, text: str, source: str, target: str) -> str: ...


class NLLBTranslator:
    def __init__(self, model_name: str = "facebook/nllb-200-distilled-600M", device: str = "cuda") -> None:
        self._tokenizer = NllbTokenizer.from_pretrained(model_name)
        self._translator = ctranslate2.Translator(
            model_name,
            device=device,
            inter_threads=4 if device == "cuda" else 1,
            compute_type="float16" if device == "cuda" else "int8",
        )
        self._lock = threading.Lock()
        self._cache: dict[tuple[str, str, str], str] = {}

    async def translate(self, text: str, source: str, target: str) -> str:
        if source == target:
            return text
        key = (text, source, target)
        if key in self._cache:
            return self._cache[key]

        result = await asyncio.get_running_loop().run_in_executor(None, self._translate_sync, text, source, target)

        if len(self._cache) >= _CACHE_MAX:
            self._cache.clear()
        self._cache[key] = result
        return result

    def _translate_sync(self, text: str, source: str, target: str) -> str:
        src_code = LANG_CODES.get(source)
        tgt_code = LANG_CODES.get(target)
        if not src_code or not tgt_code:
            return text

        with self._lock:
            self._tokenizer.src_lang = src_code
            tokens = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(text))

        results = self._translator.translate_batch([tokens], target_prefix=[[tgt_code]])
        output_tokens = results[0].hypotheses[0][1:]
        return self._tokenizer.decode(
            self._tokenizer.convert_tokens_to_ids(output_tokens), skip_special_tokens=True
        )
