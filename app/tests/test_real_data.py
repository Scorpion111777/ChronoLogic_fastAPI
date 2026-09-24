import pytest
from src.core.algorithm import process_fixed_operations
from src.core.xlsx_utils import (
    read_xlsx_to_dataframe, export_to_xlsx,
    _find_column_mapping, _detect_time_unit,
)
from src.utils import llm_utils
from src.utils.llm_utils import ensure_template_columns, LLMError, _parse_llm_mapping
import pandas as pd

@pytest.fixture
def raw_csv_bytes():
    csv_contents = """Робітник,Розряд,Обладнання,№ п/п,№ тех.оп.,Назва технологічної операції,"Затрати часу, хв",Технічні умови
1,4,ВТО,,-,ВСЬОГО ДЛЯ РОБІТНИКА,1.4,
2,4,УМ,,-,ВСЬОГО ДЛЯ РОБІТНИКА,21.15,
3,4,закріпочна НА,,-,ВСЬОGO ДЛЯ РОБІТНИКА,3,
4,4,закріпочна НА,,-,ВСЬОГО ДЛЯ РОБІТНИКА,3.64,
5,4,зіг заг,,-,ВСЬОГО ДЛЯ РОБІТНИКА,7.95,
6,4,оверлок ,,-,ВСЬОГО ДЛЯ РОБІТНИКА,4,
7,4,пакування,,-,ВСЬОГО ДЛЯ РОБІТНИКА,1.6,
8,4,ручні роботи,,-,ВСЬОГО ДЛЯ РОБІТНИКА,2.71,
9,4,ручні роботи,,-,ВСЬОГО ДЛЯ РОБІТНИКА,2.71,
2,4,УМ,1,Б 2.62.06,З'єднати зрізи виточок деталей чашки та підкладки,1.8,"Урівняти зрізи, з'єднати. Ширина припуска шва 0,2-0,3см, на ділянці вершини виточки 0,6-0,7см. Частота строчки 6-7ст/см. " """

    return csv_contents.encode('UTF-8')


def test_process_real_data(raw_csv_bytes):

    result = process_fixed_operations(raw_csv_bytes)

    assert isinstance(result, dict)

    total_row = next(r for r in result["data"] if "ВСЬОГО" in r["Назва технологічної операції"])
    assert total_row["Затрати часу, хв"] == 1.4

    assert result["total_after"] == 10

    for row in result["data"]:
        assert isinstance(row["Розряд"], int)
        assert isinstance(row["Затрати часу, хв"], (float, int))

def test_missing_required_column(monkeypatch):
    monkeypatch.setattr(llm_utils, "GROQ_API_KEY", "")
    bad_csv = "Робітник,Назва,Інше\n1,Тест,123".encode("utf-8")

    with pytest.raises(ValueError) as excinfo:
        process_fixed_operations(bad_csv)

    msg = str(excinfo.value)
    assert "не відповідають шаблону" in msg
    assert "Затрати часу, хв" in msg or "Розряд" in msg


def test_column_mapping_regex():
    mapping = _find_column_mapping([
        "Name of Operation", "Worker Name", "Rank", "Equipment Type",
        "Seq No.", "Tech Operation", "Time Cost", "Notes",
    ])
    assert mapping.get("Назва технологічної операції") == "Name of Operation"
    assert mapping.get("Розряд") == "Rank"
    assert mapping.get("Затрати часу, хв") == "Time Cost"


def test_column_mapping_ukrainian():
    mapping = _find_column_mapping([
        "Блок", "Робітник", "Розряд", "Обладнання",
        "№ п/п", "№ тех.оп.", "Назва технологічної операції",
        "Затрати часу, хв", "Технічні умови",
    ])
    assert len(mapping) == 9


def test_time_unit_detection_minutes():
    assert _detect_time_unit([1.5, 2.0, 3.5]) == "minutes"


def test_time_unit_detection_seconds():
    assert _detect_time_unit([120, 300, 45]) == "seconds"


def test_export_xlsx_roundtrip():
    rows = [
        {"block": "A", "worker": "Іванов", "rank": 4, "equipment": "ВТО",
         "num": 1, "techNum": "Б 2.62", "name": "З'єднання", "time": 1.8,
         "conditions": "Тест"},
    ]
    xlsx_bytes = export_to_xlsx(rows)
    assert len(xlsx_bytes) > 0

    df, meta = read_xlsx_to_dataframe(xlsx_bytes)
    assert "Затрати часу, хв" in df.columns
    assert "Розряд" in df.columns
    assert meta["mapped_count"] >= 5


FAKE_LLM_MAPPING = {
    "Блок": None,
    "Робітник": "Співробітник",
    "Розряд": "Грейд",
    "Обладнання": "Механізм обробки",
    "№ п/п": None,
    "№ тех.оп.": None,
    "Назва технологічної операції": "Суть операції",
    "Затрати часу, хв": "Хронометраж",
    "Технічні умови": None,
}


@pytest.fixture
def fake_llm(monkeypatch):
    monkeypatch.setattr(llm_utils, "GROQ_API_KEY", "fake-key")
    monkeypatch.setattr(llm_utils, "_regex_mapping", lambda headers: {})
    monkeypatch.setattr(
        llm_utils,
        "map_columns_with_llm",
        lambda headers, sample_rows=None: dict(FAKE_LLM_MAPPING),
    )
    return FAKE_LLM_MAPPING


def _fail_llm(headers, sample_rows=None):
    raise AssertionError("LLM не мав викликатись")


def test_parse_llm_mapping():
    text = (
        "```json\n"
        '{"Блок": null, "Робітник": "Worker Name", "Розряд": "Rank", "Обладнання": null, '
        '"№ п/п": null, "№ тех.оп.": null, "Назва технологічної операції": "Name of Operation", '
        '"Затрати часу, хв": "Time Cost", "Технічні умови": null}\n'
        "```"
    )
    mapping = _parse_llm_mapping(text)
    assert mapping["Розряд"] == "Rank"
    assert mapping["Затрати часу, хв"] == "Time Cost"
    assert mapping["Блок"] is None


def test_ensure_template_columns_uses_llm(fake_llm):
    df = pd.DataFrame({
        "Співробітник": ["Іван"], "Грейд": ["4"], "Механізм обробки": ["ВТО"],
        "Хронометраж": ["1.8"], "Суть операції": ["З'єднати"],
    })
    new_df, meta = ensure_template_columns(df)
    assert meta["used_llm"] is True
    assert "Затрати часу, хв" in new_df.columns
    assert "Розряд" in new_df.columns
    assert "Робітник" in new_df.columns
    assert new_df.loc[0, "Затрати часу, хв"] == "1.8"


def test_canonical_columns_do_not_trigger_llm(fake_llm, monkeypatch):
    monkeypatch.setattr(llm_utils, "map_columns_with_llm", _fail_llm)
    df = pd.DataFrame({
        "Блок": ["A"], "Розряд": ["4"], "Затрати часу, хв": ["1.8"],
    })
    new_df, meta = ensure_template_columns(df)
    assert meta["used_llm"] is False


def test_llm_mapping_failure_raises_error(fake_llm, monkeypatch):
    monkeypatch.setattr(
        llm_utils,
        "map_columns_with_llm",
        lambda headers, sample_rows=None: {"Розряд": "Грейд", "Блок": None},
    )
    df = pd.DataFrame({"Грейд": ["4"], "Примітка": ["x"]})
    with pytest.raises(LLMError) as excinfo:
        ensure_template_columns(df)
    assert "Затрати часу, хв" in str(excinfo.value)


def test_xlsx_llm_fallback(fake_llm):
    from openpyxl import Workbook
    import io as _io
    wb = Workbook()
    ws = wb.active
    ws.append(["Співробітник", "Грейд", "Хронометраж", "Суть операції", "Механізм обробки"])
    ws.append(["Іван", 4, 1.8, "З'єднати", "ВТО"])
    buf = _io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()

    df, meta = read_xlsx_to_dataframe(xlsx_bytes)
    assert meta["used_llm"] is True
    assert "Затрати часу, хв" in df.columns
    assert "Розряд" in df.columns
    assert float(df["Затрати часу, хв"].iloc[0]) == 1.8


def test_llm_recognition_synonyms_and_rephrase(monkeypatch):
    """Test recognition when all columns use synonyms, rephrasing, or foreign language."""
    synonym_headers = [
        "Section", "Worker Name", "Rank Level", "Machine Type",
        "Sequence", "Tech Number", "Process Description", "Allowed Minutes", "Notes",
    ]
    mock_mapping = {
        "Блок": "Section",
        "Робітник": "Worker Name",
        "Розряд": "Rank Level",
        "Обладнання": "Machine Type",
        "№ п/п": "Sequence",
        "№ тех.оп.": "Tech Number",
        "Назва технологічної операції": "Process Description",
        "Затрати часу, хв": "Allowed Minutes",
        "Технічні умови": "Notes",
    }
    monkeypatch.setattr(llm_utils, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_utils, "map_columns_with_llm", lambda h, s=None: dict(mock_mapping))

    df = pd.DataFrame({
        "Section": ["A"], "Worker Name": ["John"], "Rank Level": [4],
        "Machine Type": ["Overlock"], "Sequence": [1], "Tech Number": ["T-01"],
        "Process Description": ["Join seam"], "Allowed Minutes": [1.5], "Notes": ["Check seam"],
    })
    new_df, meta = ensure_template_columns(df)
    assert meta["used_llm"] is True
    for col in llm_utils.TEMPLATE_COLUMNS:
        assert col in new_df.columns
    assert meta["input_to_template"]["Worker Name"] == "Робітник"
    assert meta["input_to_template"]["Rank Level"] == "Розряд"
    assert meta["input_to_template"]["Allowed Minutes"] == "Затрати часу, хв"
    assert meta["column_mapping"]["Робітник"] == "Worker Name"


def test_llm_recognition_mixed_same_and_synonyms(monkeypatch):
    """Test where some columns are identical to template and some are synonyms/rephrased."""
    mock_mapping = {
        "Блок": None,
        "Робітник": "Робітник",  # Same!
        "Розряд": "Тарифний розряд",  # Synonym!
        "Обладнання": "Верстат",  # Synonym!
        "№ п/п": None,
        "№ тех.оп.": None,
        "Назва технологічної операції": "Зміст роботи",  # Rephrase!
        "Затрати часу, хв": "Час (хв)",  # Synonym!
        "Технічні умови": None,
    }
    monkeypatch.setattr(llm_utils, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_utils, "map_columns_with_llm", lambda h, s=None: dict(mock_mapping))

    df = pd.DataFrame({
        "Робітник": ["Іван"],
        "Тарифний розряд": [3],
        "Верстат": ["ВТО"],
        "Зміст роботи": ["Обметати край"],
        "Час (хв)": [2.4],
    })
    new_df, meta = ensure_template_columns(df)
    assert meta["used_llm"] is True
    assert "Робітник" in new_df.columns
    assert "Розряд" in new_df.columns
    assert "Обладнання" in new_df.columns
    assert "Назва технологічної операції" in new_df.columns
    assert "Затрати часу, хв" in new_df.columns
    assert meta["column_mapping"]["Робітник"] == "Робітник"
    assert meta["column_mapping"]["Розряд"] == "Тарифний розряд"
    assert meta["column_mapping"]["Обладнання"] == "Верстат"
    assert meta["column_mapping"]["Назва технологічної операції"] == "Зміст роботи"
    assert meta["column_mapping"]["Затрати часу, хв"] == "Час (хв)"
    assert meta["input_to_template"]["Тарифний розряд"] == "Розряд"


def test_llm_time_unit_seconds_conversion(monkeypatch):
    """Test that detected seconds are converted to minutes."""
    from src.utils.llm_utils import MappingResult
    mock_res = MappingResult({
        "Блок": None,
        "Робітник": "Співробітник",
        "Розряд": "Грейд",
        "Обладнання": None,
        "№ п/п": None,
        "№ тех.оп.": None,
        "Назва технологічної операції": "Операція",
        "Затрати часу, хв": "Час (сек)",
        "Технічні умови": None,
    })
    mock_res.time_unit = "seconds"

    monkeypatch.setattr(llm_utils, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_utils, "map_columns_with_llm", lambda h, s=None: mock_res)

    df = pd.DataFrame({
        "Співробітник": ["Олена"],
        "Грейд": [4],
        "Операція": ["Вшити блискавку"],
        "Час (сек)": [120],  # 120 seconds = 2.0 minutes
    })
    new_df, meta = ensure_template_columns(df)
    assert meta["detected_time_unit"] == "seconds"
    assert float(new_df["Затрати часу, хв"].iloc[0]) == 2.0


def test_sample_rows_passed_to_llm(monkeypatch):
    """Test that first rows are properly formatted and passed to map_columns_with_llm."""
    captured_args = {}

    def mock_map(headers, sample_rows=None):
        captured_args["headers"] = headers
        captured_args["sample_rows"] = sample_rows
        return {
            "Блок": None,
            "Робітник": headers[0],
            "Розряд": headers[1],
            "Обладнання": None,
            "№ п/п": None,
            "№ тех.оп.": None,
            "Назва технологічної операції": None,
            "Затрати часу, хв": headers[2],
            "Технічні умови": None,
        }

    monkeypatch.setattr(llm_utils, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_utils, "map_columns_with_llm", mock_map)

    df = pd.DataFrame({
        "Col_A": ["Іванов", "Петров"],
        "Col_B": [4, 5],
        "Col_C": [1.5, 2.5],
    })
    ensure_template_columns(df)
    assert captured_args["headers"] == ["Col_A", "Col_B", "Col_C"]
    assert len(captured_args["sample_rows"]) == 2
    assert captured_args["sample_rows"][0] == ["Іванов", 4, 1.5]


def test_live_llm_recognition_gpt_oss_20b():
    """Live API test verifying openai/gpt-oss-20b column recognition and bidirectional mapping."""
    if not llm_utils.GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY is not set, skipping live API test")

    df = pd.DataFrame({
        "Співробітник": ["Швачка 1", "Швачка 2"],
        "Тарифний розряд": [4, 5],
        "Устаткування": ["Оверлок", "ВТО"],
        "Суть операції": ["Обметати кишеню", "Випрасувати пояс"],
        "Хронометраж (хв)": [1.4, 3.2],
        "Вимоги": ["Шов 0.5см", "Частота 6ст/см"],
    })

    new_df, meta = ensure_template_columns(df)
    assert meta["used_llm"] is True
    assert meta["llm_info"]["model"] == "openai/gpt-oss-20b"
    assert "Робітник" in new_df.columns
    assert "Розряд" in new_df.columns
    assert "Обладнання" in new_df.columns
    assert "Назва технологічної операції" in new_df.columns
    assert "Затрати часу, хв" in new_df.columns
    assert "Технічні умови" in new_df.columns

    # Verify connection between input columns and template columns
    assert meta["column_mapping"]["Робітник"] == "Співробітник"
    assert meta["column_mapping"]["Розряд"] == "Тарифний розряд"
    assert meta["column_mapping"]["Обладнання"] == "Устаткування"
    assert meta["column_mapping"]["Назва технологічної операції"] == "Суть операції"
    assert meta["column_mapping"]["Затрати часу, хв"] == "Хронометраж (хв)"
    assert meta["column_mapping"]["Технічні умови"] == "Вимоги"

    assert meta["input_to_template"]["Співробітник"] == "Робітник"
    assert meta["input_to_template"]["Тарифний розряд"] == "Розряд"
    assert meta["input_to_template"]["Хронометраж (хв)"] == "Затрати часу, хв"

    assert float(new_df["Затрати часу, хв"].iloc[0]) == 1.4
    assert int(new_df["Розряд"].iloc[0]) == 4


def test_normalize_equipment_and_matching():
    from src.core.algorithm import normalize_equipment_token, is_equipment_match, extract_equipment_list

    assert normalize_equipment_token('  "ВТО"  ') == "вто"
    assert normalize_equipment_token('«Оверлок»\xa0') == "оверлок"
    assert normalize_equipment_token('закріпочна–НА') == "закріпочна-на"

    worker = {
        "name": "Іван",
        "rank": 4,
        "equipment_types": ["ВТО", "Оверлок"],
        "equipment_type": "УМ / ручні роботи",
    }
    eq_list = extract_equipment_list(worker)
    assert "вто" in eq_list
    assert "оверлок" in eq_list
    assert "ум" in eq_list
    assert "ручні роботи" in eq_list

    # Match tests with quotes, spaces
    assert is_equipment_match('  "ВТО"  ', eq_list) is True
    assert is_equipment_match('«Оверлок»', eq_list) is True
    assert is_equipment_match('закріпочна НА', eq_list) is False


def test_worker_distribution_and_workload_balancing():
    from src.core.algorithm import assign_tasks_to_workers

    # Two workers with identical rank 4 and ВТО
    workers = [
        {"name": "Швачка А", "rank": 4, "equipment_types": ["ВТО"], "equipment_quantity": 1},
        {"name": "Швачка Б", "rank": 4, "equipment_types": ["ВТО"], "equipment_quantity": 1},
    ]

    df = pd.DataFrame({
        "Розряд": [4, 4, 4, 4],
        "Обладнання": ["ВТО", "«ВТО»", "  ВТО  ", "ВТО"],
        "Затрати часу, хв": [10.0, 10.0, 10.0, 10.0],
        "Назва технологічної операції": ["Оп 1", "Оп 2", "Оп 3", "Оп 4"],
        "№ тех.оп.": ["1", "2", "3", "4"],
    })

    res_df, mismatches, unmatched = assign_tasks_to_workers(df, workers)
    assigned = list(res_df["Робітник"])

    # Both workers must receive tasks (balanced workload: 2 tasks each)
    assert assigned.count("Швачка А") == 2
    assert assigned.count("Швачка Б") == 2
    assert len(mismatches) == 0
    assert len(unmatched) == 0


def test_equipment_mismatch_detection():
    from src.core.algorithm import assign_tasks_to_workers

    # Workers only have ВТО and Оверлок
    workers = [
        {"name": "Іванов", "rank": 4, "equipment_types": ["ВТО"]},
        {"name": "Петров", "rank": 5, "equipment_types": ["Оверлок"]},
    ]

    df = pd.DataFrame({
        "Розряд": [4, 4],
        "Обладнання": ["ВТО", "закріпочна НА"],  # закріпочна НА is missing in profile
        "Затрати часу, хв": [2.0, 3.5],
        "Назва технологічної операції": ["Прасування", "Закріпка кишені"],
        "№ тех.оп.": ["01", "02"],
    })

    res_df, mismatches, unmatched = assign_tasks_to_workers(df, workers)

    assert res_df.loc[0, "Робітник"] == "Іванов"
    # Row 1 has equipment mismatch
    assert len(mismatches) == 1
    assert mismatches[0]["equipment_in_file"] == "закріпочна НА"
    assert "Не знайдено робітника" in mismatches[0]["reason"]
    assert len(unmatched) == 1
    assert unmatched[0]["equipment"] == "закріпочна НА"
    assert unmatched[0]["affected_operations"] == 1