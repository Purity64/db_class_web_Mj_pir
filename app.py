# ============================================================
#  app.py — เว็บแอป Flask (ทำให้เสร็จแล้ว ★ ไม่ต้องแก้)
#  รัน:  python app.py  แล้วเปิด http://127.0.0.1:5000
# ============================================================
from flask import Flask, request, jsonify, render_template
import db

app = Flask(__name__)


def safe(fn, *args, **kwargs):
    try:
        return jsonify({"ok": True, "data": fn(*args, **kwargs)})
    except NotImplementedError as e:
        return jsonify({"ok": False, "todo": True, "error": str(e)}), 501
    except ValueError as e:
        # ข้อมูลผิดรูปแบบ (validate ไม่ผ่าน) -> 400 ไม่ใช่ 500
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500


def body():
    """อ่าน JSON จาก request อย่างปลอดภัย (ไม่ crash เมื่อไม่ได้ส่ง body)"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("ต้องส่งข้อมูล JSON ที่ถูกต้อง")
    return data


def safe_body(fn, *args):
    """เรียก fn(... , body) โดยอ่าน JSON ภายใน safe() — ถ้า body ผิดรูปจะได้ 400"""
    return safe(lambda: fn(*args, body()))


@app.route("/")
def page_home():
    return render_template("index.html")

@app.route("/report")
def page_report():
    return render_template("report.html")


# ---- ลูกค้า ----
@app.route("/api/customers", methods=["GET"])
def customers_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.search_customers, filters)

@app.route("/api/customers/<int:_id>", methods=["GET"])
def customer_get(_id):
    return safe(db.get_customer, _id)

@app.route("/api/customers", methods=["POST"])
def customer_create():
    return safe_body(db.create_customer)

@app.route("/api/customers/<int:_id>", methods=["PUT"])
def customer_update(_id):
    return safe_body(db.update_customer, _id)

@app.route("/api/customers/<int:_id>", methods=["DELETE"])
def customer_delete(_id):
    return safe(db.delete_customer, _id)

# ---- สิทธิ์ (role) ----
@app.route("/api/roles", methods=["GET"])
def roles_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.list_roles, filters)

@app.route("/api/roles/<int:_id>", methods=["GET"])
def role_get(_id):
    return safe(db.get_role, _id)

@app.route("/api/roles", methods=["POST"])
def role_create():
    return safe_body(db.create_role)

@app.route("/api/roles/<int:_id>", methods=["PUT"])
def role_update(_id):
    return safe_body(db.update_role, _id)

@app.route("/api/roles/<int:_id>", methods=["DELETE"])
def role_delete(_id):
    return safe(db.delete_role, _id)

# ---- สินค้า ----
@app.route("/api/products", methods=["GET"])
def products_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.search_products, filters)

@app.route("/api/products/<int:_id>", methods=["GET"])
def product_get(_id):
    return safe(db.get_product, _id)

@app.route("/api/products", methods=["POST"])
def product_create():
    return safe_body(db.create_product)

@app.route("/api/products/<int:_id>", methods=["PUT"])
def product_update(_id):
    return safe_body(db.update_product, _id)

@app.route("/api/products/<int:_id>", methods=["DELETE"])
def product_delete(_id):
    return safe(db.delete_product, _id)

# ---- ออเดอร์ ----
@app.route("/api/orders", methods=["GET"])
def orders_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.search_orders, filters)

@app.route("/api/orders/<int:_id>", methods=["GET"])
def order_get(_id):
    return safe(db.get_order, _id)

@app.route("/api/orders", methods=["POST"])
def order_create():
    return safe_body(db.create_order)

@app.route("/api/orders/<int:_id>", methods=["PUT"])
def order_update(_id):
    return safe_body(db.update_order, _id)

@app.route("/api/orders/<int:_id>/items", methods=["GET"])
def order_items(_id):
    return safe(db.get_order_items, _id)

@app.route("/api/orders/<int:_id>/items", methods=["PUT"])
def order_items_update(_id):
    return safe_body(lambda _i, d: db.set_order_items(_i, d.get("items")), _id)

@app.route("/api/orders/<int:_id>/payments", methods=["GET"])
def order_payments(_id):
    return safe(db.get_order_payments, _id)

@app.route("/api/orders/<int:_id>", methods=["DELETE"])
def order_delete(_id):
    return safe(db.delete_order, _id)

@app.route("/api/orders/customer", methods=["POST"])
def order_create_customer():
    return safe_body(db.create_customer_order)

# ---- ที่อยู่ ----
@app.route("/api/addresses", methods=["GET"])
def addresses_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.list_addresses, filters)

@app.route("/api/addresses/<int:_id>", methods=["GET"])
def address_get(_id):
    return safe(db.get_address, _id)

@app.route("/api/addresses", methods=["POST"])
def address_create():
    return safe_body(db.create_address)

@app.route("/api/addresses/<int:_id>", methods=["PUT"])
def address_update(_id):
    return safe_body(db.update_address, _id)

@app.route("/api/addresses/<int:_id>", methods=["DELETE"])
def address_delete(_id):
    return safe(db.delete_address, _id)

# ---- การชำระเงิน ----
@app.route("/api/payments", methods=["GET"])
def payments_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.search_payments, filters)

@app.route("/api/payments/<int:_id>", methods=["GET"])
def payment_get(_id):
    return safe(db.get_payment, _id)

@app.route("/api/payments", methods=["POST"])
def payment_create():
    return safe_body(db.create_payment)

@app.route("/api/payments/<int:_id>", methods=["PUT"])
def payment_update(_id):
    return safe_body(db.update_payment, _id)

@app.route("/api/payments/<int:_id>", methods=["DELETE"])
def payment_delete(_id):
    return safe(db.delete_payment, _id)

@app.route("/api/payments/<int:_id>/verify", methods=["POST"])
def payment_verify(_id):
    return safe(db.verify_payment, _id)

# ---- รีวิว ----
@app.route("/api/reviews", methods=["GET"])
def reviews_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.search_reviews, filters)

@app.route("/api/reviews/<int:_id>", methods=["GET"])
def review_get(_id):
    return safe(db.get_review, _id)

@app.route("/api/products/<int:_id>/reviews", methods=["GET"])
def product_reviews(_id):
    return safe(db.get_product_reviews, _id)

@app.route("/api/reviews", methods=["POST"])
def review_create():
    return safe_body(db.create_review)

@app.route("/api/reviews/<int:_id>", methods=["PUT"])
def review_update(_id):
    return safe_body(db.update_review, _id)

@app.route("/api/reviews/<int:_id>", methods=["DELETE"])
def review_delete(_id):
    return safe(db.delete_review, _id)

# ---- หมวดหมู่ ----
@app.route("/api/categories", methods=["GET"])
def categories_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.list_categories, filters)

@app.route("/api/categories/<int:_id>", methods=["GET"])
def category_get(_id):
    return safe(db.get_category, _id)

@app.route("/api/categories", methods=["POST"])
def category_create():
    return safe_body(db.create_category)

@app.route("/api/categories/<int:_id>", methods=["PUT"])
def category_update(_id):
    return safe_body(db.update_category, _id)

@app.route("/api/categories/<int:_id>", methods=["DELETE"])
def category_delete(_id):
    return safe(db.delete_category, _id)


@app.route("/api/reports/summary")
def report_summary():
    return safe(db.report_summary)

@app.route("/api/reports/best-selling")
def route_report_best_selling():
    return safe(db.report_best_selling)

@app.route("/api/reports/top-customers")
def route_report_customers_above_avg():
    return safe(db.report_customers_above_avg)

@app.route("/api/reports/high-rated")
def route_report_high_rated():
    return safe(db.report_high_rated)

@app.route("/api/reports/sales-by-month")
def report_sales_month():
    months = request.args.get("months", 6)
    try:
        months = max(1, min(24, int(months)))
    except (TypeError, ValueError):
        months = 6
    return safe(db.report_sales_by_month, months)


if __name__ == "__main__":
    app.run(debug=True, port=5000)