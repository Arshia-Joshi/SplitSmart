"""Bill split calculation.

All maths is done in integer paise so the shares always add up to the
bill total exactly (no floating point drift).

Rules:
- An item assigned to some people is divided equally between them.
- An item assigned to nobody is divided equally between everyone.
- Charges (taxes, service charge, round off) minus discount are divided
  equally between everyone.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def to_paise(value):
    try:
        amount = Decimal(str(value).strip() or "0")
    except InvalidOperation:
        raise ValueError(f"'{value}' is not a valid amount")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_rupees(paise):
    return paise / 100


def split_paise(paise, n, start=0):
    """Split paise into n parts that add up exactly. Leftover paise go one
    each to people starting from `start`, so no one person always pays extra."""
    base, extra = divmod(paise, n)
    parts = [base] * n
    for k in range(extra):
        parts[(start + k) % n] += 1
    return parts


def calculate_split(people, items, charges=None, discount=0):
    """
    people:  ["Asha", "Ravi", ...]
    items:   [{"name": "Pizza", "price": 300, "assigned": [0, 2]}, ...]
             assigned = indexes into people; empty means everyone
    charges: [{"name": "CGST", "amount": 7.5}, ...]
    discount: amount taken off the bill
    """
    charges = charges or []
    names = [str(p).strip() for p in people]
    if not names:
        raise ValueError("Add at least one person")
    if any(not n for n in names):
        raise ValueError("Every person needs a name")
    n = len(names)

    result = [{"name": name, "items": [], "items_paise": 0} for name in names]
    items_total = 0
    unassigned = []

    for idx, item in enumerate(items):
        name = str(item.get("name", "")).strip() or f"Item {idx + 1}"
        price = to_paise(item.get("price", 0))
        if price < 0:
            raise ValueError(f"Price of '{name}' can't be negative")
        items_total += price

        assigned = sorted({int(i) for i in item.get("assigned", []) if 0 <= int(i) < n})
        if not assigned:
            assigned = list(range(n))
            unassigned.append(name)

        shares = split_paise(price, len(assigned), start=idx)
        for person_idx, share in zip(assigned, shares):
            result[person_idx]["items"].append({
                "name": name,
                "share": to_rupees(share),
                "shared_with": len(assigned),
            })
            result[person_idx]["items_paise"] += share

    charges_total = 0
    clean_charges = []
    for ch in charges:
        amount = to_paise(ch.get("amount", 0))
        charges_total += amount
        clean_charges.append({"name": str(ch.get("name", "")).strip() or "Charge",
                              "amount": to_rupees(amount)})

    discount_paise = to_paise(discount)
    if discount_paise < 0:
        raise ValueError("Discount can't be negative")

    extras = charges_total - discount_paise
    total = items_total + extras
    if total < 0:
        raise ValueError("Discount is bigger than the bill")

    extra_shares = split_paise(extras, n)
    people_out = []
    for person, extra in zip(result, extra_shares):
        people_out.append({
            "name": person["name"],
            "items": person["items"],
            "items_total": to_rupees(person["items_paise"]),
            "extras": to_rupees(extra),
            "total": to_rupees(person["items_paise"] + extra),
        })

    return {
        "people": people_out,
        "items_total": to_rupees(items_total),
        "charges": clean_charges,
        "charges_total": to_rupees(charges_total),
        "discount": to_rupees(discount_paise),
        "total": to_rupees(total),
        "unassigned_items": unassigned,
    }
