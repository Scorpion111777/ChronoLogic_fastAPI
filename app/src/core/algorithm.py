import pandas as pd
from collections import defaultdict
from typing import List, Dict, Any
import io
import time



def process_fixed_operations(csv_bytes: bytes) -> Dict[str, Any]:
    start_time = time.time()

    # === ЧИТАННЯ CSV ===
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Error reading CSV: {str(e)}")

    total_before = len(df)

    time_col = "Затрати часу, хв"
    if time_col not in df.columns:
        raise ValueError(f"CSV must contain '{time_col}' column")

    # === ОЧИЩЕННЯ ДАНИХ ===
    # Очистка часу: аналогічно існуючій логіці, для забезпечення числових значень >=0
    df[time_col] = (
        df[time_col]
        .astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0.0).round(2)
    df = df[df[time_col] >= 0]  # Фільтр: видалити негативні значення часу, бо вони не мають сенсу в контексті затрат

    # Очистка розряду: аналогічно, для цілих невід'ємних значень
    if "Розряд" not in df.columns:
        raise ValueError("CSV must contain 'Розряд' column")
    df["Розряд"] = (
        df["Розряд"]
        .astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df["Розряд"] = pd.to_numeric(df["Розряд"], errors="coerce").fillna(0).astype(int)
    df = df[df["Розряд"] >= 0]  # Фільтр: видалити негативні розряди, бо розряд не може бути негативним

    # Очистка № п/п: для сортування та числових значень
    if "№ п/п" in df.columns:
        df["№ п/п"] = pd.to_numeric(df["№ п/п"], errors="coerce")

    # Фільтрація: видалити рядки з порожньою назвою операції (критичне поле)
    if "Назва технологічної операції" in df.columns:
        df = df[df["Назва технологічної операції"].notna() & (df["Назва технологічної операції"].str.strip() != "")]

    # Видалити дублікати: повні дублікати рядків, бо вони можуть бути помилками вводу
    df = df.drop_duplicates()

    # Сортування: аналогічно існуючій, для послідовності
    if "№ п/п" in df.columns:
        df = df.sort_values(by="№ п/п", ignore_index=True)

    # Заміна NaN на None для сумісності з JSON
    df = df.where(pd.notna(df), None)

    total_after = len(df)
    filtered_count = total_before - total_after
    processing_time_sec = round(time.time() - start_time, 2)

    return {
        "total_before": total_before,
        "total_after": total_after,
        "filtered_count": filtered_count,
        "processing_time_sec": processing_time_sec,
        "data": df.to_dict(orient="records")
    }