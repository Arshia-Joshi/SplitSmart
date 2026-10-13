import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from .models import Bill, BillCharge, BillItem, BillPerson, User, db
from .split import calculate_split

load_dotenv()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def database_url():
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not url:
        print("DATABASE_URL not set, using local SQLite file splitsmart.db")
        return "sqlite:///splitsmart.db"
    # Neon/Heroku style URLs start with postgres://, SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def create_app(test_config=None):
    app = Flask(__name__)
    on_vercel = bool(os.getenv("VERCEL"))

    secret = os.getenv("SECRET_KEY")
    if not secret:
        if on_vercel:
            raise RuntimeError("SECRET_KEY must be set in production")
        secret = "dev-only-secret"

    app.config.update(
        SECRET_KEY=secret,
        SQLALCHEMY_DATABASE_URI=database_url(),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=on_vercel,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(error="Please log in"), 401
        return f(*args, **kwargs)
    return wrapper


def error(message, status=400):
    return jsonify(error=message), status


def register_routes(app):

    @app.errorhandler(413)
    def too_large(_):
        return error("Image is too large (max 5 MB)", 413)

    @app.get("/api/health")
    def health():
        return jsonify(ok=True)

    # ---------- auth ----------

    def start_session(user):
        session.clear()
        session.permanent = True
        session["user_id"] = user.id

    @app.post("/api/auth/signup")
    def signup():
        data = request.get_json(silent=True) or {}
        username = str(data.get("username", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

        if not username or not email or not password:
            return error("All fields are required")
        if "@" not in email:
            return error("Enter a valid email")
        if len(password) < 6:
            return error("Password must be at least 6 characters")
        if User.query.filter((User.email == email) | (User.username == username)).first():
            return error("Username or email already exists")

        user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return error("Username or email already exists")
        start_session(user)
        return jsonify(user=user.to_dict()), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return error("Invalid email or password", 401)
        start_session(user)
        return jsonify(user=user.to_dict())

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.get("/api/auth/me")
    def me():
        user = db.session.get(User, session.get("user_id")) if "user_id" in session else None
        if not user:
            session.clear()
            return error("Not logged in", 401)
        return jsonify(user=user.to_dict())

    # ---------- scan & split ----------

    @app.post("/api/scan")
    @login_required
    def scan():
        file = request.files.get("bill")
        if not file or not file.filename:
            return error("Choose a bill photo")
        if file.mimetype not in ALLOWED_TYPES:
            return error("Use a JPG, PNG or WEBP image")

        from .ocr import read_bill  # imported here so the app still runs without Gemini
        try:
            return jsonify(read_bill(file.read(), file.mimetype))
        except Exception as e:
            print(f"Scan failed: {e}")
            return error("Couldn't read this bill. Try a clearer photo or enter it manually.", 502)

    def split_from_request(data):
        return calculate_split(
            people=data.get("people", []),
            items=data.get("items", []),
            charges=data.get("charges", []),
            discount=data.get("discount", 0),
        )

    @app.post("/api/split/preview")
    @login_required
    def preview():
        try:
            return jsonify(split_from_request(request.get_json(silent=True) or {}))
        except (ValueError, TypeError, AttributeError) as e:
            return error(str(e))

    # ---------- bills ----------

    @app.get("/api/bills")
    @login_required
    def list_bills():
        bills = (Bill.query.filter_by(user_id=session["user_id"])
                 .order_by(Bill.created_at.desc()).all())
        return jsonify(bills=[b.summary() for b in bills])

    @app.post("/api/bills")
    @login_required
    def save_bill():
        data = request.get_json(silent=True) or {}
        try:
            result = split_from_request(data)
        except (ValueError, TypeError, AttributeError) as e:
            return error(str(e))
        if not data.get("items"):
            return error("Add at least one item")

        bill = Bill(
            user_id=session["user_id"],
            restaurant_name=(str(data.get("restaurant_name", "")).strip() or "Restaurant")[:120],
            items_total=result["items_total"],
            charges_total=result["charges_total"],
            discount=result["discount"],
            total=result["total"],
        )
        n = len(result["people"])
        for pos, item in enumerate(data["items"]):
            assigned = sorted({int(i) for i in item.get("assigned", []) if 0 <= int(i) < n})
            bill.items.append(BillItem(position=pos, name=str(item.get("name", "")).strip()[:200] or f"Item {pos + 1}",
                                       price=item.get("price", 0), assigned=assigned))
        for pos, ch in enumerate(result["charges"]):
            bill.charges.append(BillCharge(position=pos, name=ch["name"][:100], amount=ch["amount"]))
        for pos, p in enumerate(result["people"]):
            bill.people.append(BillPerson(position=pos, name=p["name"][:100], items_total=p["items_total"],
                                          extras=p["extras"], total=p["total"], items=p["items"]))
        db.session.add(bill)
        db.session.commit()
        return jsonify(bill=bill.to_dict()), 201

    def own_bill(bill_id):
        return Bill.query.filter_by(id=bill_id, user_id=session["user_id"]).first()

    @app.get("/api/bills/<int:bill_id>")
    @login_required
    def get_bill(bill_id):
        bill = own_bill(bill_id)
        if not bill:
            return error("Bill not found", 404)
        return jsonify(bill=bill.to_dict())

    @app.delete("/api/bills/<int:bill_id>")
    @login_required
    def delete_bill(bill_id):
        bill = own_bill(bill_id)
        if not bill:
            return error("Bill not found", 404)
        db.session.delete(bill)
        db.session.commit()
        return jsonify(ok=True)


if __name__ == "__main__":
    create_app().run(port=5000, debug=True)
