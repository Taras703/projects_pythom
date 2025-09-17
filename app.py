from flask import Flask, render_template, request, redirect, url_for, current_app
from config import Config
from robokassa_client import build_payment_url, verify_signature_from_result
from decimal import Decimal
from typing import Dict, Any, Optional
import logging

app = Flask(__name__)
app.config.from_object(Config)
logging.basicConfig(level=logging.INFO)

# --- Простая имитация БД ---
ORDERS: Dict[str, Dict[str, Any]] = {}

# --- Тестовые заказы ---
def create_test_orders():
    test_orders = {
        "1001": {
            "id": "1001",
            "amount": Decimal("100.00"),
            "description": "Базовый тестовый заказ",
            "status": "created",
            "shp": {"user": "1", "product": "basic"}
        },
        "1002": {
            "id": "1002",
            "amount": Decimal("250.50"),
            "description": "Премиум подписка",
            "status": "created",
            "shp": {"user": "2", "product": "premium"}
        }
    }
    ORDERS.update(test_orders)

create_test_orders()

# --- Вспомогательные функции ---
class OrderNotFoundError(Exception):
    pass

def _get_order_data(order_id: str) -> Dict[str, Any]:
    order = ORDERS.get(str(order_id))
    if not order:
        raise OrderNotFoundError(f"Order {order_id} not found")
    return order

def _validate_order_parameters(order_id: str, amount: Decimal, description: str) -> None:
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if not description:
        raise ValueError("Description required")

def _update_order_status(order_id: str, status: str, robokassa_data: Optional[Dict[str, Any]] = None) -> None:
    order = ORDERS.get(str(order_id))
    if not order:
        ORDERS[str(order_id)] = {"id": str(order_id), "status": status}
        return
    order["status"] = status
    if robokassa_data:
        order.setdefault("robokassa", {}).update(robokassa_data)

# --- Роуты сайта ---
@app.route("/")
def index():
    return render_template("index.html", orders=ORDERS)

@app.route("/create-order", methods=["POST"])
def create_order():
    amount = request.form.get("amount", "0").strip()
    description = request.form.get("description", "Заказ").strip()
    order_id = request.form.get("order_id") or str(len(ORDERS) + 1000)

    try:
        amount_dec = Decimal(amount)
    except Exception:
        return "Некорректная сумма", 400

    ORDERS[str(order_id)] = {
        "id": str(order_id),
        "amount": amount_dec,
        "description": description,
        "status": "created",
        "shp": {"user": "demo"}
    }
    return redirect(url_for("index"))

@app.route("/create-payment", methods=["POST"])
def create_payment():
    order_id = request.form.get("order_id")
    if not order_id:
        return "order_id required", 400

    try:
        order = _get_order_data(order_id)
    except OrderNotFoundError:
        return "Order not found", 404

    amount = order.get("amount")
    description = order.get("description", "")
    shp = order.get("shp", {})

    try:
        _validate_order_parameters(order_id, Decimal(amount), description)
    except ValueError as e:
        return str(e), 400

    cfg = current_app.config

    try:
        url = build_payment_url(
            merchant_login=cfg["ROBOKASSA_MERCHANT_LOGIN"],
            password1=cfg["ROBOKASSA_PASSWORD1"],
            out_sum=str(amount),
            inv_id=str(order_id),
            description=description,
            shp=shp,
            is_test=cfg["ROBOKASSA_TEST_MODE"],
        )
        _update_order_status(order_id, "pending")
        return redirect(url, code=302)
    except Exception as e:
        return f"Ошибка создания платежа: {e}", 500

@app.route("/payment/success")
def payment_success():
    inv_id = request.args.get("InvId", "")
    try:
        order = _get_order_data(inv_id)
    except OrderNotFoundError:
        order = {"id": inv_id, "status": "unknown"}
    return render_template("success.html", order_id=inv_id, payment_data=order)

@app.route("/payment/fail")
def payment_fail():
    inv_id = request.args.get("InvId", "")
    return render_template("fail.html", order_id=inv_id, error_message="Платёж отменён")

@app.route("/payment/result", methods=["POST"])
def payment_result():
    out_sum = request.form.get("OutSum", "")
    inv_id = request.form.get("InvId", "")
    signature = request.form.get("SignatureValue", "")
    shp = {k[4:]: v for k, v in request.form.items() if k.startswith("Shp_")}

    cfg = current_app.config
    valid = verify_signature_from_result(out_sum, inv_id, signature, cfg["ROBOKASSA_PASSWORD2"], shp)
    if not valid:
        return "Invalid signature", 400

    _update_order_status(inv_id, "paid", {"OutSum": out_sum, "shp": shp})
    return f"OK{inv_id}"

# --- Роуты для открытия страниц напрямую ---
@app.route("/success")
def success_page():
    return render_template("success.html", order_id="demo", payment_data={"amount": "100", "status": "paid"})

@app.route("/fail")
def fail_page():
    return render_template("fail.html", order_id="demo", error_message="Тестовая ошибка")

@app.route("/pending")
def pending_page():
    return render_template("pending.html", order_id="demo")

@app.route("/payment-form")
def payment_form():
    return render_template("payment_form.html")

if __name__ == "__main__":
    app.run(debug=True)
