import pytest
from src.core.algorithm import process_fixed_operations

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

def test_missing_required_column():
    bad_csv = "Робітник,Назва,Інше\n1,Тест,123".encode("utf-8")

    with pytest.raises(ValueError) as excinfo:
        process_fixed_operations(bad_csv)

    assert "CSV must contain" in str(excinfo.value)