"""Read a bill photo with Gemini and return items, charges and totals."""
import json
import os

from google import genai
from google.genai import types

from .split import to_paise

PROMPT = """You are reading a restaurant or shop bill. Return ONLY JSON in this shape:
{
  "restaurant_name": string,
  "items": [{"name": string, "quantity": number, "price": number}],
  "charges": [{"name": string, "amount": number}],
  "discount": number,
  "total": number
}
Rules:
- "price" is the final amount printed for that line (quantity x rate), not the unit rate.
- Do not put weights or pack sizes (like 200 g, 0.5 KG) in price.
- "charges" are amounts ADDED on top of the items to reach the total: CGST, SGST, GST, VAT,
  service charge, packing charge, round off (round off can be negative).
- If taxes are already included in the item prices (only shown as a "GST break up"),
  do NOT list them in charges.
- "discount" is a positive number taken off the bill, 0 if none.
- "total" is the final amount payable printed on the bill, 0 if not visible.
- Use plain numbers, no currency symbols. Skip lines you can't read."""


def _number(value):
    try:
        return round(float(str(value).replace(",", "").replace("₹", "").strip()), 2)
    except (TypeError, ValueError):
        return 0.0


def clean_result(raw):
    """Turn Gemini's JSON into safe numbers and make the parts add up."""
    items = []
    for item in raw.get("items") or []:
        name = str(item.get("name", "")).strip()
        price = _number(item.get("price"))
        qty = _number(item.get("quantity")) or 1
        if not name or price <= 0:
            continue
        if qty != 1:
            name = f"{name} x{qty:g}"
        items.append({"name": name, "price": price})

    charges = []
    for ch in raw.get("charges") or []:
        amount = _number(ch.get("amount"))
        if amount:
            charges.append({"name": str(ch.get("name", "")).strip() or "Charge", "amount": amount})

    discount = abs(_number(raw.get("discount")))
    printed_total = _number(raw.get("total"))

    items_paise = sum(to_paise(i["price"]) for i in items)
    charges_paise = sum(to_paise(c["amount"]) for c in charges)
    discount_paise = to_paise(discount)
    total_paise = to_paise(printed_total)

    if total_paise and charges and abs(items_paise - discount_paise - total_paise) <= 100:
        # Items already add up to the total, so the "charges" were a tax break up
        # that is included in the prices. Adding them again would overcharge.
        charges = []
        charges_paise = 0

    gap = total_paise - (items_paise + charges_paise - discount_paise)
    if total_paise and gap and abs(gap) <= 100:
        charges.append({"name": "Round off", "amount": gap / 100})

    return {
        "restaurant_name": str(raw.get("restaurant_name") or "").strip()[:120] or "Restaurant",
        "items": items,
        "charges": charges,
        "discount": discount,
        "printed_total": printed_total,
    }


def read_bill(image_bytes, mime_type):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    try:
        raw = json.loads(response.text)
    except (TypeError, json.JSONDecodeError):
        raise RuntimeError("Could not read the bill, try a clearer photo")
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    return clean_result(raw)
