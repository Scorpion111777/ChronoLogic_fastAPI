import pandas as pd
from collections import defaultdict
from typing import List, Dict, Any
import io


# ... імпорти без змін

def process_operations(csv_bytes: bytes, workers: List[Dict[str, Any]]) -> Dict[str, Any]:
    # === ЧИТАННЯ CSV ===
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes), encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(csv_bytes), encoding="windows-1251")

    time_col = "Затрати часу, хв"
    if time_col not in df.columns:
        raise ValueError(f"CSV must contain '{time_col}' column")

    df[time_col] = (
        df[time_col]
        .astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce").fillna(0.0).round(2)

    # === ОЧИЩЕННЯ РОЗРЯДУ: NaN → 0 ===
    if "Розряд" not in df.columns:
        raise ValueError("CSV must contain 'Розряд' column")

    df["Розряд"] = (
        df["Розряд"]
        .astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    # Перетворюємо в число, заповнюємо NaN нулями (або 1, якщо це логічніше)
    # і одразу перетворюємо на ціле число (int)
    df["Розряд"] = pd.to_numeric(df["Розряд"], errors="coerce").fillna(0).astype(int)

    # === СОРТУВАННЯ ===
    if "№ п/п" in df.columns:
        df["№ п/п"] = pd.to_numeric(df["№ п/п"], errors="coerce")
        df = df.sort_values(by="№ п/п", ignore_index=True)

    # === РОЗПОДІЛ ===
    assignments = defaultdict(list)
    worker_loads = defaultdict(float)

    for equipment, group in df.groupby("Обладнання"):
        available_workers = [w for w in workers if w["equipment"].strip().lower() == str(equipment).strip().lower()]
        for _, row in group.iterrows():
            op_grade = row["Розряд"]
            eligible = [w for w in available_workers if int(w["grade"]) >= op_grade]
            if not eligible:
                continue
            chosen_worker = min(eligible, key=lambda w: worker_loads[w["id"]])
            assignments[chosen_worker["id"]].append(row)
            # ← БЕЗПЕЧНЕ ДОДАВАННЯ: NaN → 0.0
            time_val = float(row[time_col]) if pd.notna(row[time_col]) else 0.0
            worker_loads[chosen_worker["id"]] += time_val

    # === ВИХІДНА ТАБЛИЦЯ ===
    rows_out = []
    for w in workers:
        wid = w["id"]
        total_time = worker_loads[wid]
        assigned_ops = pd.DataFrame(assignments[wid]) if assignments[wid] else pd.DataFrame(columns=df.columns)

        if "№ п/п" in assigned_ops.columns:
            assigned_ops["№ п/п"] = pd.to_numeric(assigned_ops["№ п/п"], errors="coerce")
            assigned_ops = assigned_ops.sort_values(by="№ п/п", ignore_index=True)

        for _, r in assigned_ops.iterrows():
            time_val = float(r[time_col]) if pd.notna(r[time_col]) else 0.0  # ← NaN → 0.0
            rows_out.append({
                "Робітник": wid,
                "Розряд": w["grade"],
                "Обладнання": w["equipment"],
                "№ п/п": r.get("№ п/п", ""),
                "№ тех.оп.": r.get("№ тех.оп.", ""),
                "Назва технологічної операції": r.get("Назва технологічної операції", ""),
                "Затрати часу, хв": round(time_val, 2),  # ← БЕЗПЕЧНО
                "Технічні умови": r.get("Технічні умови", "")
            })

        # "ВСЬОГО ДЛЯ РОБІТНИКА"
        rows_out.append({
            "Робітник": wid,
            "Розряд": w["grade"],
            "Обладнання": w["equipment"],
            "№ п/п": "-",
            "№ тех.оп.": "-",
            "Назва технологічної операції": "ВСЬОГО ДЛЯ РОБІТНИКА",
            "Затрати часу, хв": round(total_time, 2),
            "Технічні умови": ""
        })

    result_df = pd.DataFrame(rows_out)
    if "№ п/п" in result_df.columns:
        result_df["№ п/п"] = pd.to_numeric(result_df["№ п/п"], errors="coerce")
        result_df = result_df.sort_values(by=["№ п/п"], ignore_index=True)

    # === ПІДСУМКИ ===
    real_operations = df[
        ~df["Назва технологічної операції"].str.contains("ВСЬОГО ДЛЯ РОБІТНИКА", na=False)
    ]
    total_sum = round(float(pd.to_numeric(real_operations[time_col], errors='coerce').sum()), 2)
    max_parallel_time = round(float(pd.Series(list(worker_loads.values())).sum(skipna=True)), 2)
    # --- ЦЕЙ РЯДОК ВЖЕ НА МІСЦІ І ВСЕ ВИПРАВЛЯЄ ---
    result_df = result_df.where(pd.notna(result_df), None)

    return {
        "table": result_df.to_dict(orient="records"),
        "total_sum": total_sum,
        "max_parallel_time": max_parallel_time,
        "result_csv": result_df.to_csv(index=False, encoding="utf-8-sig")
    }


import time


def process_fixed_operations(csv_bytes: bytes) -> Dict[str, Any]:
    """
    Process the fixed_operations.csv file: read, clean, filter, and return structured data.
    """
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