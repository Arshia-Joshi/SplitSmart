import pytest

from backend.split import calculate_split, split_paise
from backend.ocr import clean_result


def totals(result):
    return [p["total"] for p in result["people"]]


def test_shared_item_is_divided_not_duplicated():
    # Old bug: each of the 3 people was charged the full 300
    r = calculate_split(["A", "B", "C"], [{"name": "Pizza", "price": 300, "assigned": [0, 1, 2]}])
    assert totals(r) == [100, 100, 100]
    assert r["total"] == 300


def test_items_assigned_to_one_person():
    r = calculate_split(["A", "B"], [
        {"name": "Burger", "price": 250, "assigned": [0]},
        {"name": "Coffee", "price": 120, "assigned": [1]},
    ])
    assert totals(r) == [250, 120]


def test_unassigned_item_split_between_everyone():
    r = calculate_split(["A", "B"], [{"name": "Fries", "price": 100, "assigned": []}])
    assert totals(r) == [50, 50]
    assert r["unassigned_items"] == ["Fries"]


def test_taxes_split_equally():
    r = calculate_split(
        ["A", "B"],
        [{"name": "Thali", "price": 900, "assigned": [0]}, {"name": "Tea", "price": 100, "assigned": [1]}],
        charges=[{"name": "CGST", "amount": 25}, {"name": "SGST", "amount": 25}],
    )
    assert totals(r) == [925, 125]
    assert r["total"] == 1050


def test_discount_split_equally():
    r = calculate_split(["A", "B"], [{"name": "X", "price": 200, "assigned": [0, 1]}], discount=50)
    assert totals(r) == [75, 75]
    assert r["total"] == 150


def test_rounding_always_adds_up_to_total():
    r = calculate_split(
        ["A", "B", "C"],
        [{"name": "Dosa", "price": 100, "assigned": [0, 1, 2]},
         {"name": "Idli", "price": 100, "assigned": [0, 1, 2]}],
        charges=[{"name": "Service", "amount": 10}],
    )
    assert round(sum(totals(r)), 2) == r["total"] == 210
    # leftover paise rotate instead of always hitting person A
    assert totals(r) == [70.01, 70.0, 69.99]


def test_negative_split_for_round_off():
    assert split_paise(-100, 3) == [-33, -33, -34]


def test_errors():
    with pytest.raises(ValueError):
        calculate_split([], [])
    with pytest.raises(ValueError):
        calculate_split(["A"], [{"name": "X", "price": -5}])
    with pytest.raises(ValueError):
        calculate_split(["A"], [{"name": "X", "price": "abc"}])
    with pytest.raises(ValueError):
        calculate_split(["A"], [{"name": "X", "price": 10}], discount=50)


def test_ocr_drops_included_gst_breakup():
    # Chitale bill from data/receipts: items already add to 389, GST is a break up
    raw = {
        "restaurant_name": "Chitale Bandhu",
        "items": [{"name": "Nachani Ladoo", "quantity": 1, "price": 210},
                  {"name": "Chakli Sticks", "quantity": 1, "price": 80},
                  {"name": "Kaju Katli", "quantity": 1, "price": 99}],
        "charges": [{"name": "CGST", "amount": 11.65}, {"name": "SGST", "amount": 11.65}],
        "discount": 0,
        "total": 389,
    }
    out = clean_result(raw)
    assert out["charges"] == []


def test_ocr_adds_round_off_and_cleans_values():
    raw = {
        "items": [{"name": "Paneer", "quantity": 2, "price": "₹ 420.00"}, {"name": "", "price": 10},
                  {"name": "Bad", "price": "n/a"}],
        "charges": [{"name": "GST 5%", "amount": 21}],
        "total": 441.5,
    }
    out = clean_result(raw)
    assert out["items"] == [{"name": "Paneer x2", "price": 420.0}]
    assert out["charges"][-1] == {"name": "Round off", "amount": 0.5}
    assert out["restaurant_name"] == "Restaurant"
