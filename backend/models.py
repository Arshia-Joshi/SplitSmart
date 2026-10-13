from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now_utc():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)

    bills = db.relationship("Bill", backref="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email}


class Bill(db.Model):
    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    restaurant_name = db.Column(db.String(120), nullable=False, default="Restaurant")
    items_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    charges_total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc, index=True)

    items = db.relationship("BillItem", backref="bill", cascade="all, delete-orphan",
                            order_by="BillItem.position")
    charges = db.relationship("BillCharge", backref="bill", cascade="all, delete-orphan",
                              order_by="BillCharge.position")
    people = db.relationship("BillPerson", backref="bill", cascade="all, delete-orphan",
                             order_by="BillPerson.position")

    def summary(self):
        return {
            "id": self.id,
            "restaurant_name": self.restaurant_name,
            "total": float(self.total),
            "people_count": len(self.people),
            "item_count": len(self.items),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_dict(self):
        data = self.summary()
        data.update({
            "items_total": float(self.items_total),
            "charges_total": float(self.charges_total),
            "discount": float(self.discount),
            "items": [i.to_dict() for i in self.items],
            "charges": [c.to_dict() for c in self.charges],
            "people": [p.to_dict() for p in self.people],
        })
        return data


class BillItem(db.Model):
    __tablename__ = "bill_items"

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    assigned = db.Column(db.JSON, nullable=False, default=list)  # person positions

    def to_dict(self):
        return {"name": self.name, "price": float(self.price), "assigned": self.assigned or []}


class BillCharge(db.Model):
    __tablename__ = "bill_charges"

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    def to_dict(self):
        return {"name": self.name, "amount": float(self.amount)}


class BillPerson(db.Model):
    __tablename__ = "bill_people"

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    name = db.Column(db.String(100), nullable=False)
    items_total = db.Column(db.Numeric(10, 2), nullable=False)
    extras = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    items = db.Column(db.JSON, nullable=False, default=list)  # [{name, share, shared_with}]

    def to_dict(self):
        return {
            "name": self.name,
            "items_total": float(self.items_total),
            "extras": float(self.extras),
            "total": float(self.total),
            "items": self.items or [],
        }
