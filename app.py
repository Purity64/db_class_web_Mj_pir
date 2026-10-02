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
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500


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
    return safe(db.create_customer, request.json)

@app.route("/api/customers/<int:_id>", methods=["PUT"])
def customer_update(_id):
    return safe(db.update_customer, _id, request.json)

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
    return safe(db.create_role, request.json)

@app.route("/api/roles/<int:_id>", methods=["PUT"])
def role_update(_id):
    return safe(db.update_role, _id, request.json)

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
    return safe(db.create_product, request.json)

@app.route("/api/products/<int:_id>", methods=["PUT"])
def product_update(_id):
    return safe(db.update_product, _id, request.json)

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
    return safe(db.create_order, request.json)

@app.route("/api/orders/<int:_id>", methods=["PUT"])
def order_update(_id):
    return safe(db.update_order, _id, request.json)

@app.route("/api/orders/<int:_id>", methods=["DELETE"])
def order_delete(_id):
    return safe(db.delete_order, _id)

@app.route("/api/orders/customer", methods=["POST"])
def order_create_customer():
    return safe(db.create_customer_order, request.json)

# ---- ที่อยู่ ----
@app.route("/api/addresses", methods=["GET"])
def addresses_list():
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.list_addresses, filters)

@app.route("/api/addresses", methods=["POST"])
def address_create():
    return safe(db.create_address, request.json)

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
    return safe(db.create_category, request.json)

@app.route("/api/categories/<int:_id>", methods=["PUT"])
def category_update(_id):
    return safe(db.update_category, _id, request.json)

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
