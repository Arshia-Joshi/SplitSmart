import pytest

from backend.app import create_app
from backend.models import db


@pytest.fixture
def client(tmp_path):
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}", "TESTING": True})
    with app.app_context():
        db.create_all()
    return app.test_client()


def signup(client, name="asha"):
    return client.post("/api/auth/signup", json={"username": name, "email": f"{name}@x.com", "password": "secret1"})


BILL = {
    "restaurant_name": "Cafe",
    "people": ["Asha", "Ravi"],
    "items": [{"name": "Pizza", "price": 400, "assigned": [0, 1]},
              {"name": "Coke", "price": 60, "assigned": [1]}],
    "charges": [{"name": "GST", "amount": 23}],
    "discount": 0,
}


def test_needs_login(client):
    assert client.get("/api/bills").status_code == 401


def test_signup_login_logout(client):
    assert signup(client).status_code == 201
    assert signup(client).status_code == 400  # duplicate
    assert client.get("/api/auth/me").json["user"]["username"] == "asha"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "asha@x.com", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ASHA@x.com", "password": "secret1"}).status_code == 200


def test_save_and_fetch_bill(client):
    signup(client)
    res = client.post("/api/bills", json=BILL)
    assert res.status_code == 201
    bill = res.json["bill"]
    assert bill["total"] == 483
    assert [p["total"] for p in bill["people"]] == [211.5, 271.5]

    bills = client.get("/api/bills").json["bills"]
    assert len(bills) == 1 and bills[0]["people_count"] == 2

    detail = client.get(f"/api/bills/{bill['id']}").json["bill"]
    assert detail["items"][1]["assigned"] == [1]


def test_users_cant_see_each_others_bills(client):
    signup(client, "asha")
    bill_id = client.post("/api/bills", json=BILL).json["bill"]["id"]
    client.post("/api/auth/logout")
    signup(client, "ravi")
    assert client.get(f"/api/bills/{bill_id}").status_code == 404
    assert client.delete(f"/api/bills/{bill_id}").status_code == 404


def test_delete_bill(client):
    signup(client)
    bill_id = client.post("/api/bills", json=BILL).json["bill"]["id"]
    assert client.delete(f"/api/bills/{bill_id}").status_code == 200
    assert client.get("/api/bills").json["bills"] == []


def test_preview_validation(client):
    signup(client)
    assert client.post("/api/split/preview", json={"people": [], "items": []}).status_code == 400
    ok = client.post("/api/split/preview", json=BILL)
    assert ok.status_code == 200 and ok.json["total"] == 483
