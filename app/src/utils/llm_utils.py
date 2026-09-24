import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:
    pass

GROQ_API_KEY = (
    os.getenv("GROQ_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("LLM_API_KEY")
    or ""
).strip()

GROQ_BASE_URL = (
    os.getenv("GROQ_BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or os.getenv("LLM_BASE_URL")
    or "https://api.groq.com/openai/v1"
).strip()

# User requirement: "There are connected LLM openai/gpt-oss-20b via API. ... Use only this LLM."
GROQ_MODEL = (
    os.getenv("GROQ_MODEL")
    or os.getenv("OPENAI_MODEL")
    or os.getenv("LLM_MODEL")
    or "openai/gpt-oss-20b"
).strip()
if not GROQ_MODEL:
    GROQ_MODEL = "openai/gpt-oss-20b"

TEMPLATE_COLUMNS = [
    "Блок",
    "Робітник",
    "Розряд",
    "Обладнання",
    "№ п/п",
    "№ тех.оп.",
    "Назва технологічної операції",
    "Затрати часу, хв",
    "Технічні умови",
]

REQUIRED_COLUMNS = ["Затрати часу, хв", "Розряд"]

SAMPLE_ROWS_LIMIT = 5


class LLMError(ValueError):
    """Raised when LLM column mapping fails or is misconfigured."""


class MappingResult(dict):
    """Dictionary containing column mapping with optional metadata attributes."""
    time_unit: str = "minutes"


TEMPLATE_DESCRIPTIONS = {
    "Блок": "блок / група / секція / вузол виробу, конструктивна частина",
    "Робітник": "виконавець операції (ім'я, прізвище, табельний номер, код робітника)",
    "Розряд": "кваліфікаційний розряд / грейд / клас робітника (ціле число)",
    "Обладнання": "тип обладнання / верстата / машини / станка / робочого місця",
    "№ п/п": "порядковий номер рядка / операції",
    "№ тех.оп.": "номер / код / шифр технологічної операції",
    "Назва технологічної операції": "найменування або детальний опис технологічної операції",
    "Затрати часу, хв": "затрати часу на операцію у хвилинах",
    "Технічні умови": "технічні умови, вимоги, примітки, параметри обробки",
}

SYSTEM_PROMPT = """\
Ти — провідний експерт з аналізу та нормалізації табличних виробничих даних (технологічні карти та швейне/текстильне виробництво).
Твоє завдання — розпізнати ВСІ колонки вхідного файлу та пов'язати їх зі стандартним шаблоном колонок системи.

СТАНДАРТНИЙ ШАБЛОН КОЛОНОК (9 колонок):
1. "Блок" — назва або позначення блоку, групи, секції, вузла або частини виробу (наприклад: "Блок А", "Чашка", "Пояс", "Спинка", "Section", "Group", "Вузол").
2. "Робітник" — виконавець операції (ім'я, прізвище, табельний номер, код робітника, наприклад: "Іванов І.І.", "Швачка 1", "1", "2", "Operator", "Worker", "Співробітник").
3. "Розряд" — кваліфікаційний розряд / грейд / клас робітника (число, наприклад: 1, 2, 3, 4, 5, 6, "Rank", "Grade", "Клас", "Тарифний розряд").
4. "Обладнання" — тип верстата, обладнання, машини, інструменту або робочого місця (наприклад: "ВТО", "УМ", "оверлок", "закріпочна НА", "зіг заг", "пакування", "ручні роботи", "Machine", "Equipment", "Верстат", "Устаткування").
5. "№ п/п" — порядковий номер рядка / операції (наприклад: 1, 2, 3, 4, "Seq", "Sequence", "№", "Порядковий номер", "Step").
6. "№ тех.оп." — шифр, номер або код технологічної операції (наприклад: "Б 2.62.06", "ТО-01", "010", "Tech Op No", "Код операції", "Шифр").
7. "Назва технологічної операції" — найменування або детальний опис дії / технологічної операції (наприклад: "З'єднати зрізи виточок", "Обметати зріз", "Вшити блискавку", "Operation name", "Description", "Зміст роботи", "Найменування").
8. "Затрати часу, хв" — затрати часу на операцію у хвилинах. Може називатися: "Час", "Норма часу", "Трудомісткість", "Тривалість", "Хронометраж", "Time", "Duration", "Час (хв)", "Час, с". Якщо одиниця виміру секунди — зазнач це у time_unit.
9. "Технічні умови" — технічні умови, параметри, примітки, вимоги до обробки, інструкції до виконання (наприклад: "Урівняти зрізи, з'єднати...", "Частота 6ст/см", "Примітки", "Notes", "Technical conditions", "Вимоги").

ПРАВИЛА РОЗПІЗНАВАННЯ:
1. Деякі колонки вхідного файлу можуть називатися ТОЧНО ТАК САМО, як у шаблоні.
2. Деякі колонки можуть використовувати СИНОНІМИ, скорочення, іншу мову (укр, англ, польська, тощо) або перефразовані назви.
3. ОБОВ'ЯЗКОВО аналізуй перші рядки даних (sample values) для кожної колонки:
   - Якщо назва колонки нетипова чи коротка (наприклад "1", "Кол_А", "Дані"), визначай її суть за вмістом клітинок.
   - Числові значення типу 1.4, 21.15, 1.8 вказують на час; цілі числа 1-6 можуть бути розрядом або порядковим номером; детальні описи швів вказують на назву операції тощо.
4. Значенням кожного поля у mapping має бути ТОЧНА назва колонки зі списку вхідних колонок (без змін), або null якщо для цієї колонки шаблону немає відповідника у вхідному файлі.
5. Кожна вхідна колонка може бути призначена не більше ніж одній колонці шаблону.
6. Вхідні колонки, які не відповідають жодній колонці шаблону (наприклад: штрихкод, ціна, статус), не повинні прив'язуватися до шаблону.
7. Визнач "time_unit": "seconds" якщо за назвою колонки часу або за значеннями видно, що час вимірюється в секундах (наприклад: у назві є "с", "сек", "sec", "second" або середній час > 50), інакше "minutes".
8. Результат — ВИКЛЮЧНО валідний JSON-об'єкт наступної структури:
{
  "mapping": {
    "Блок": "<точна назва з вхідних колонок або null>",
    "Робітник": "<точна назва з вхідних колонок або null>",
    "Розряд": "<точна назва з вхідних колонок або null>",
    "Обладнання": "<точна назва з вхідних колонок або null>",
    "№ п/п": "<точна назва з вхідних колонок або null>",
    "№ тех.оп.": "<точна назва з вхідних колонок або null>",
    "Назва технологічної операції": "<точна назва з вхідних колонок або null>",
    "Затрати часу, хв": "<точна назва з вхідних колонок або null>",
    "Технічні умови": "<точна назва з вхідних колонок або null>"
  },
  "time_unit": "minutes"
}
"""


def _truncate_cell(value: Any, limit: int = 120) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def _format_sample_rows(sample_rows: Optional[List[Any]]) -> List[List[str]]:
    rows = sample_rows or []
    out = []
    for row in rows[:SAMPLE_ROWS_LIMIT]:
        cells = []
        for c in row:
            cells.append(_truncate_cell(c))
        out.append(cells)
    return out


def _format_column_samples(headers: List[str], sample_rows: Optional[List[Any]]) -> List[Dict[str, Any]]:
    rows = sample_rows or []
    col_samples = []
    for idx, header in enumerate(headers):
        samples: List[str] = []
        for row in rows:
            if idx < len(row):
                val = row[idx]
                if val is not None and str(val).strip() != "":
                    cleaned_val = _truncate_cell(val)
                    if cleaned_val not in samples:
                        samples.append(cleaned_val)
            if len(samples) >= SAMPLE_ROWS_LIMIT:
                break
        col_samples.append({
            "header": str(header),
            "sample_values": samples,
        })
    return col_samples


def _build_user_prompt(headers: List[str], sample_rows: Optional[List[Any]]) -> str:
    col_samples = _format_column_samples(headers, sample_rows)
    raw_preview = _format_sample_rows(sample_rows)
    payload = {
        "columns_with_samples": col_samples,
        "sample_rows_preview": raw_preview[:3],
    }
    return (
        "Проаналізуй структуру вхідного файлу, заголовки колонок та перші рядки даних.\n"
        "Зістав кожну колонку вхідного файлу з відповідною колонкою стандартного шаблону.\n"
        "Вхідні дані файлу:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("LLM відповідь не містить валідного JSON")
    return json.loads(cleaned[start : end + 1])


def _match_header(source_str: Optional[str], headers: List[str]) -> Optional[str]:
    if not source_str:
        return None
    s = str(source_str).strip()
    if not s or s.lower() == "null" or s.lower() == "none":
        return None
    if s in headers:
        return s

    s_lower = s.lower()
    for h in headers:
        if h.lower() == s_lower:
            return h

    # Match normalized without punctuation
    s_clean = re.sub(r"[^\w\s]", "", s_lower).strip()
    for h in headers:
        h_clean = re.sub(r"[^\w\s]", "", h.lower()).strip()
        if s_clean and h_clean and (s_clean == h_clean or s_clean in h_clean or h_clean in s_clean):
            return h

    return s


def _parse_llm_mapping(text: str, headers: Optional[List[str]] = None) -> MappingResult:
    try:
        data = _extract_json(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"LLM повернув некоректний JSON: {e}. Відповідь: {text[:500]}")

    if not isinstance(data, dict):
        raise LLMError("LLM повернув некоректний формат відповіді (очікувався JSON-об'єкт)")

    if "mapping" in data and isinstance(data["mapping"], dict):
        mapping_data = data["mapping"]
    else:
        mapping_data = data

    time_unit = str(data.get("time_unit", "minutes")).strip().lower()
    if time_unit not in ("seconds", "minutes"):
        time_unit = "minutes"

    mapping = MappingResult()
    mapping.time_unit = time_unit
    mapping["_time_unit"] = time_unit

    normalized = {str(k).strip(): v for k, v in mapping_data.items()}

    used_sources = set()
    for target in TEMPLATE_COLUMNS:
        val = normalized.get(target)
        if val is None and target.lower() not in {k.lower() for k in normalized}:
            val = next((v for k, v in normalized.items() if k.lower() == target.lower()), None)

        if val is None:
            mapping[target] = None
            continue

        raw_source = str(val).strip()
        if not raw_source or raw_source.lower() in ("null", "none"):
            mapping[target] = None
            continue

        resolved_source = _match_header(raw_source, headers) if headers else raw_source
        if resolved_source and resolved_source not in used_sources:
            mapping[target] = resolved_source
            used_sources.add(resolved_source)
        else:
            mapping[target] = resolved_source

    return mapping


def _get_active_api_config() -> Tuple[str, str, str]:
    return GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL


def map_columns_with_llm(
    headers: List[str],
    sample_rows: Optional[List[Any]] = None,
) -> MappingResult:
    """
    Recognize all columns in the input file using openai/gpt-oss-20b.
    Returns MappingResult ({canonical_template_column: original_input_header | None}).
    """
    api_key, base_url, model = _get_active_api_config()
    if not api_key:
        raise LLMError(
            "GROQ_API_KEY не налаштовано. Додайте ключ у файл app/.env "
            "(GROQ_API_KEY=...), щоб увімкнути LLM-аналіз колонок."
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise LLMError("Бібліотека 'openai' не встановлена. Виконайте: pip install openai")

    client = OpenAI(api_key=api_key, base_url=base_url)
    user_content = _build_user_prompt(headers, sample_rows)

    last_error: Optional[Exception] = None
    for use_json_mode in (True, False):
        try:
            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0,
            }
            if use_json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            content = (response.choices[0].message.content or "").strip()
            if not content:
                raise LLMError("LLM повернув порожню відповідь")
            return _parse_llm_mapping(content, headers=headers)
        except Exception as e:
            last_error = e

    raise LLMError(
        f"Не вдалось отримати відповідь від LLM ({model}): {last_error}"
    )


def _regex_mapping(headers: List[str]) -> Dict[str, str]:
    try:
        from src.core.xlsx_utils import _find_column_mapping
        return _find_column_mapping(headers)
    except Exception:
        return {}


def _detect_time_unit_from_values(values: List[float]) -> str:
    clean = [v for v in values if v > 0]
    if not clean:
        return "minutes"
    avg = sum(clean) / len(clean)
    if avg > 50:
        return "seconds"
    return "minutes"


def resolve_column_mapping(
    headers: List[str],
    sample_rows: Optional[List[Any]] = None,
    time_unit: Optional[str] = None,
) -> Tuple[Dict[str, str], bool, Dict[str, Any]]:
    """
    Resolve in-file headers to canonical template columns using openai/gpt-oss-20b.

    Provides bidirectional connection and handles exact names, synonyms, and rephrasing.
    Returns (mapping, used_llm, llm_info).
    """
    string_headers = [str(h) for h in headers]
    mapping: Dict[str, str] = {}

    # Check if all headers are already canonical template columns and required columns exist
    is_canonical = (
        all(h in TEMPLATE_COLUMNS for h in string_headers)
        and all(r in string_headers for r in REQUIRED_COLUMNS)
    )

    api_key, _, model = _get_active_api_config()

    if is_canonical:
        # File is already 100% formatted to the canonical template, no LLM call needed
        for target in TEMPLATE_COLUMNS:
            if target in string_headers:
                mapping[target] = target
        used_llm = False
        llm_info: Dict[str, Any] = {
            "attempted": False,
            "model": model,
            "time_unit": time_unit or "minutes",
        }
        return mapping, used_llm, llm_info

    # Input file has columns that require recognition (synonyms, rephrasing, etc.)
    used_llm = False
    llm_info = {"attempted": False, "model": model, "time_unit": time_unit or "minutes"}

    if not api_key:
        missing = [t for t in REQUIRED_COLUMNS if t not in string_headers]
        raise LLMError(
            "Назви колонок вхідного файлу не відповідають шаблону, а GROQ_API_KEY "
            "не налаштовано. Не розпізнано обов'язкові колонки: "
            + ", ".join(f'"{t}"' for t in missing)
            + ". Задайте GROQ_API_KEY у файлі app/.env або перейменуйте "
            "колонки відповідно до шаблону."
        )

    try:
        raw_llm_res = map_columns_with_llm(string_headers, sample_rows)
    except Exception:
        raise

    used_llm = True
    llm_info["attempted"] = True

    if isinstance(raw_llm_res, dict):
        llm_mapping = raw_llm_res
        detected_time_unit = getattr(raw_llm_res, "time_unit", raw_llm_res.get("_time_unit", "minutes"))
    else:
        llm_mapping = dict(raw_llm_res)
        detected_time_unit = "minutes"

    llm_info["response"] = llm_mapping
    llm_info["time_unit"] = time_unit or detected_time_unit

    # Connect template columns to recognized input columns
    used_headers = set()
    for target in TEMPLATE_COLUMNS:
        source = llm_mapping.get(target)
        if source and source in string_headers and source not in used_headers:
            mapping[target] = source
            used_headers.add(source)

    # If some template column wasn't mapped by LLM but has an identical unmapped header
    for target in TEMPLATE_COLUMNS:
        if target not in mapping and target in string_headers and target not in used_headers:
            mapping[target] = target
            used_headers.add(target)

    # Fallback to regex only for remaining unmapped columns if LLM left them empty
    for target, source in _regex_mapping(string_headers).items():
        if target not in mapping and source in string_headers and source not in used_headers:
            mapping[target] = source
            used_headers.add(source)

    still_missing = [t for t in REQUIRED_COLUMNS if t not in mapping]
    if still_missing:
        proposed = {t: llm_mapping.get(t) for t in still_missing}
        raise LLMError(
            "Не вдалось розпізнати обов'язкові колонки вхідного файлу: "
            + ", ".join(f'"{t}"' for t in still_missing)
            + ". "
            + "Відповідність, запропонована LLM: "
            + json.dumps(proposed, ensure_ascii=False)
            + ". Будь ласка, перейменуйте колонки файлу відповідно до шаблону."
        )

    return mapping, used_llm, llm_info


def ensure_template_columns(
    df: pd.DataFrame,
    sample_rows: Optional[List[Any]] = None,
    time_unit: Optional[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Bring a DataFrame's columns to the canonical template structure using openai/gpt-oss-20b.

    Recognizes synonyms, rephrasing, and identical columns, connects input headers
    to template columns, converts units if needed, and orders columns canonical first.
    Returns (renamed_df, meta).
    """
    headers = [str(c) for c in df.columns]
    if sample_rows is None:
        sample_rows = df.head(SAMPLE_ROWS_LIMIT).values.tolist()

    mapping, used_llm, llm_info = resolve_column_mapping(headers, sample_rows, time_unit=time_unit)

    # Detect or extract time unit
    detected_time_unit = time_unit or llm_info.get("time_unit")
    if not detected_time_unit or detected_time_unit not in ("seconds", "minutes"):
        mapped_time_source = mapping.get("Затрати часу, хв")
        raw_vals: List[float] = []
        if mapped_time_source and mapped_time_source in df.columns:
            for v in df[mapped_time_source].dropna():
                try:
                    num_val = float(str(v).replace(",", ".").replace(" ", "").replace("\xa0", ""))
                    raw_vals.append(num_val)
                except (ValueError, TypeError):
                    pass
        detected_time_unit = _detect_time_unit_from_values(raw_vals)

    # Rename mapped columns
    rename_dict = {src: tgt for tgt, src in mapping.items() if src in df.columns and src != tgt}
    new_df = df.rename(columns=rename_dict)

    # Convert time from seconds to minutes if detected
    time_target = "Затрати часу, хв"
    if detected_time_unit == "seconds" and time_target in new_df.columns:
        new_df[time_target] = (
            new_df[time_target].astype(str)
            .str.replace('\xa0', '', regex=False)
            .str.replace('\u00a0', '', regex=False)
            .str.replace(' ', '', regex=False)
            .str.replace(',', '.', regex=False)
        )
        new_df[time_target] = pd.to_numeric(new_df[time_target], errors="coerce").fillna(0.0)
        new_df[time_target] = (new_df[time_target] / 60.0).round(4)

    # Ensure all 9 template columns exist
    for col in TEMPLATE_COLUMNS:
        if col not in new_df.columns:
            new_df[col] = ""

    # Reorder columns: 9 template columns first, then any extra columns
    existing = [c for c in TEMPLATE_COLUMNS if c in new_df.columns]
    other = [c for c in new_df.columns if c not in TEMPLATE_COLUMNS]
    new_df = new_df[existing + other]

    # Build bidirectional mapping connection
    input_to_template = {}
    for tgt, src in mapping.items():
        if src:
            input_to_template[src] = tgt
    for h in headers:
        if h not in input_to_template:
            input_to_template[h] = None

    mapped_count = len([v for v in mapping.values() if v is not None])

    meta = {
        "used_llm": used_llm,
        "llm_info": llm_info,
        "column_mapping": mapping,
        "input_to_template": input_to_template,
        "detected_time_unit": detected_time_unit,
        "mapped_count": mapped_count,
        "total_columns": len(headers),
        "original_headers": headers,
    }

    return new_df, meta