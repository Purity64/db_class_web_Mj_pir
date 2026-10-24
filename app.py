# ============================================================
#  app.py — เว็บแอป Flask (ทำให้เสร็จแล้ว ★ ปกติไม่ต้องแก้)
#  รัน:  python app.py  แล้วเปิด http://127.0.0.1:5000
#  ★ เพิ่มรายงานใหม่ไม่ต้องแก้ไฟล์นี้ — ไปเพิ่มที่ REPORTS ท้าย db.py
# ============================================================
from datetime import date, datetime
from decimal import Decimal
from flask import Flask, request, jsonify, render_template, session, redirect
from flask.json.provider import DefaultJSONProvider
import db


class JSONProvider(DefaultJSONProvider):
    """- ส่งวันที่เป็นรูปแบบ YYYY-MM-DD ให้ช่อง <input type="date"> ในฟอร์มอ่านได้
       - ไม่เรียงชื่อคอลัมน์ใหม่ → หัวตารางเรียงตามลำดับใน SELECT"""
    sort_keys = False

    @staticmethod
    def default(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        return DefaultJSONProvider.default(o)


app = Flask(__name__)
app.secret_key = "db69-demo-secret"
app.json = JSONProvider(app)


def safe(fn, *args, **kwargs):
    try:
        return jsonify({"ok": True, "data": fn(*args, **kwargs)})
    except NotImplementedError as e:
        return jsonify({"ok": False, "todo": True, "error": str(e)}), 501
    except ValueError as e:
        # ข้อผิดพลาดที่ db.py ตั้งใจแจ้งผู้ใช้ เช่น raise ValueError("คลาสนี้เต็มแล้ว")
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500


COOKIE_AGE = 60 * 60 * 24 * 7   


def current_user_id():
    v = request.cookies.get("user_id")
    return int(v) if v and v.isdigit() else None


def current_role():
    return request.cookies.get("role", "")


@app.route("/")
def page_home():
    return render_template("index.html")

@app.route("/home")
def page_login():
    if current_user_id() is None:
        return redirect("/")
    if current_role() != "user": return redirect("/admin")
    return render_template("home.html")

@app.route("/admin")
def page_admin():
    uid = current_user_id()
    if uid is None: return redirect("/")
    if current_role() != "admin": return redirect("/home")
    return render_template("admin.html")

@app.route("/test")
def page_test():
    return render_template("test.html")


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

# ---- รีวิวของสินค้า (สาธารณะ) — ปุ่ม "ดูรีวิว" ที่ตารางสินค้า ----
@app.route("/api/products/<int:_id>/reviews", methods=["GET"])
def product_reviews(_id):
    return safe(db.get_product_reviews, _id)

# ---- สต็อก (product_detail) ของสินค้า — /admin จัดการ ----
@app.route("/api/products/<int:_id>/stock", methods=["GET"])
def product_stock_list(_id):
    return safe(db.get_product_stock, _id)

@app.route("/api/products/<int:_id>/stock", methods=["POST"])
def product_stock_add(_id):
    d = request.get_json(silent=True) or {}
    return safe(db.add_product_stock, _id,
                d.get("qty", 0),
                (d.get("username") or "").strip() or None,
                (d.get("password") or "").strip() or None)

@app.route("/api/product-details/<int:pd_id>", methods=["PUT"])
def product_detail_update(pd_id):
    d = request.get_json(silent=True) or {}
    return safe(db.update_product_detail, pd_id,
                (d.get("username") or "").strip(),
                (d.get("password") or "").strip(),
                1 if str(d.get("use", 0)) == "1" else 0)

@app.route("/api/product-details/<int:pd_id>", methods=["DELETE"])
def product_detail_delete(pd_id):
    return safe(db.delete_product_detail, pd_id)

# ---- โค้ดส่วนลด (code) — /admin จัดการ ----
@app.route("/api/codes", methods=["GET"])
def code_list():
    return safe(db.search_codes, request.args.to_dict())

@app.route("/api/codes", methods=["POST"])
def code_create():
    return safe(db.create_code, request.get_json(silent=True) or {})

@app.route("/api/codes/<int:_id>", methods=["GET"])
def code_get(_id):
    return safe(db.get_code, _id)

@app.route("/api/codes/<int:_id>", methods=["PUT"])
def code_update(_id):
    return safe(db.update_code, _id, request.get_json(silent=True) or {})

@app.route("/api/codes/<int:_id>", methods=["DELETE"])
def code_delete(_id):
    return safe(db.delete_code, _id)


# ---- ออเดอร์ user / ตะกร้า ----
def _require_user():
    uid = current_user_id()
    if uid is None:
        return None, (jsonify({"ok": False, "error": "กรุณาเข้าสู่ระบบ"}), 401)
    if not db.get_customer(uid):
        resp = jsonify({"ok": False, "error": "บัญชีนี้ถูกลบแล้ว กรุณาเข้าสู่ระบบใหม่"})
        resp.delete_cookie("user_id")
        resp.delete_cookie("role")
        return None, (resp, 401)
    return uid, None


@app.route("/api/cart", methods=["GET"])
def cart_get():
    uid, err = _require_user()
    if err: return err
    return safe(db.get_cart, uid)

@app.route("/api/cart/items", methods=["POST"])
def cart_add():
    uid, err = _require_user()
    if err: return err
    return safe(db.add_to_Order, request.json, uid)

@app.route("/api/cart/items/<int:pid>", methods=["PUT"])
def cart_set_qty(pid):
    uid, err = _require_user()
    if err: return err
    return safe(db.set_cart_qty, uid, pid, request.json)

@app.route("/api/cart/items/<int:pid>", methods=["DELETE"])
def cart_remove(pid):
    uid, err = _require_user()
    if err: return err
    return safe(db.remove_cart_item, uid, pid)

REPORTS = []
def report_summary():
    return {}

@app.route("/api/cart/confirm", methods=["GET"])
def cart_confirm():
    uid, err = _require_user()
    if err: return err
    return safe(db.confirm_cart, db.Check_myorder(uid))

@app.route("/api/orders", methods=["GET"])
def orders_list():
    uid, err = _require_user()
    if err: return err
    filters = {k: v for k, v in request.args.items() if v}
    return safe(db.search_orders_user, filters, uid)

@app.route("/api/orders/<int:_id>", methods=["GET"])
def order_get(_id):
    # IDOR guard: ออเดอร์ต้องเป็นของตัวเอง (เช็คจากรายการออเดอร์ของ user นี้)
    uid, err = _require_user()
    if err:
        return err
    try:
        mine = db.search_orders_user({}, uid)
    except NotImplementedError as e:
        return jsonify({"ok": False, "todo": True, "error": str(e)}), 501
    if not any(o.get("order_id") == _id for o in (mine or [])):
        return jsonify({"ok": False, "error": "ไม่พบออเดอร์นี้ของคุณ"}), 403
    return safe(db.get_order, _id)


@app.route("/api/orders/<int:_id>/payments", methods=["GET"])
def order_payments(_id):
    # IDOR guard: ประวัติการชำระเงินดูได้เฉพาะเจ้าของออเดอร์
    uid, err = _require_user()
    if err:
        return err
    mine = db.search_orders_user({}, uid)
    if not any(o.get("order_id") == _id for o in (mine or [])):
        return jsonify({"ok": False, "error": "ไม่พบออเดอร์นี้ของคุณ"}), 403
    return safe(db.get_order_payments, _id)


# ---- รีวิว (review) หลังชำระเงิน ----
@app.route("/api/reviews", methods=["GET"])
def review_list():
    uid, err = _require_user()
    if err:
        return err
    order_id = request.args.get("order_id", type=int)
    if not order_id:
        return jsonify({"ok": False, "error": "ต้องระบุ order_id"}), 400
    return safe(db.get_my_reviews, uid, order_id)

@app.route("/api/reviews", methods=["POST"])
def review_save():
    uid, err = _require_user()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    if not d.get("order_id"):
        return jsonify({"ok": False, "error": "ต้องระบุ order_id"}), 400
    return safe(db.save_reviews, uid, int(d.get("order_id")), d.get("items") or [])



@app.route("/api/orders/<int:_id>/pay", methods=["POST"])
def order_pay(_id):
    uid, err = _require_user()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    result = d.get("result") if d.get("result") in ("success", "failed") else "success"
    return safe(db.pay_order, uid, _id,
                (d.get("code_name") or "").strip() or None, result)


@app.route("/api/orders/<int:_id>/check-code", methods=["POST"])
def order_check_code(_id):
    uid, err = _require_user()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    return safe(db.check_order_code, uid, _id, (d.get("code_name") or "").strip())


@app.route("/api/orders/<int:_id>/cancel", methods=["POST"])
def order_cancel(_id):
    uid, err = _require_user()
    if err:
        return err
    return safe(db.cancel_order, uid, _id)


# ---- รายงาน ----
@app.route("/api/reports/summary")
def report_summary():
    return safe(db.report_summary)

@app.route("/api/reports")
def report_list():
    """รายชื่อรายงานทั้งหมด (อ่านจาก db.REPORTS) ให้หน้าเว็บสร้างกล่องรายงาน"""
    data = [{"key": k, "title": t} for k, t, _ in db.REPORTS]
    
    # print แสดงโครงสร้างข้อมูลจริงใน Console
    print({"ok": True, "data": data})
    
    return jsonify({"ok": True, "data": data})

@app.route("/api/reports/<key>")
def report_run(key):
    """รันรายงานตามชื่อ เช่น /api/reports/overdue"""
    for k, _, fn in db.REPORTS:
        if k == key:
            return safe(fn)
    return jsonify({"ok": False, "error": f"ไม่พบรายงาน '{key}' ใน db.REPORTS"}), 404

# -- login 
@app.route("/api/signin", methods=["POST"])
def singin_():
    try:
        user = db.singin(request.json)    
    except NotImplementedError as e:
        return jsonify({"ok": False, "todo": True, "error": str(e)}), 501
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
    resp = jsonify({"ok": True, "data": user})
    resp.set_cookie("user_id", str(user["user_id"]), max_age=COOKIE_AGE,
                    httponly=False, samesite="Lax")
    resp.set_cookie("role", user["role"], max_age=COOKIE_AGE,
                    httponly=False, samesite="Lax")
    return resp

@app.route("/api/signup", methods=["POST"])
def signup_():
    try:
        user = db.signup(request.json)
    except NotImplementedError as e:
        return jsonify({"ok": False, "todo": True, "error": str(e)}), 501
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}"}), 500
    resp = jsonify({"ok": True, "data": user})
    resp.set_cookie("user_id", str(user["user_id"]), max_age=COOKIE_AGE,
                    httponly=False, samesite="Lax")
    resp.set_cookie("role", user["role"], max_age=COOKIE_AGE,
                    httponly=False, samesite="Lax")
    return resp

@app.route("/api/me")
def me():
    uid = current_user_id()
    if uid is None:
        return jsonify({"ok": True, "data": None})
    if not db.get_customer(uid):
        resp = jsonify({"ok": True, "data": None})
        resp.delete_cookie("user_id")
        resp.delete_cookie("role")
        return resp
    return jsonify({"ok": True, "data": {
        "user_id": uid, "role": current_role()}})

@app.route("/api/logout", methods=["POST"])
def logout():
    resp = jsonify({"ok": True})
    resp.delete_cookie("user_id")
    resp.delete_cookie("role")
    return resp


# home
@app.route("/api/categories")
def categories_():
    return safe(db.list_categories)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
