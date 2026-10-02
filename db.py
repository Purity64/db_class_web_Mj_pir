# ============================================================
#  db.py — ชั้นติดต่อฐานข้อมูล  ★★★ นิสิตเขียน SQL ในไฟล์นี้ ★★★
#  มองหาคำว่า  # TODO  ทุกฟังก์ชัน — ใช้ %s เป็น placeholder เสมอ (กัน SQL injection)
# ============================================================
import mysql.connector
import config
import uuid

ORDER_STATUSES = ("pending", "waiting_paid", "paid", "delivered", "cancelled", "succeed", "shipped")


def get_connection():
    return mysql.connector.connect(
        host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD,
        database=config.DB_NAME, port=config.DB_PORT)


def run_query(sql, params=None):
    """รัน SELECT คืนผลเป็น list ของ dict"""
    conn = get_connection(); cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ()); rows = cur.fetchall()
    cur.close(); conn.close(); return rows


def run_command(sql, params=None):
    """รัน INSERT / UPDATE / DELETE แล้ว commit"""
    conn = get_connection(); cur = conn.cursor()
    cur.execute(sql, params or ()); conn.commit()
    out = {"new_id": cur.lastrowid, "affected": cur.rowcount}
    cur.close(); conn.close(); return out


# ---------- ลูกค้า (customer) ----------
def search_customers(filters):
    sql = """SELECT ur.user_id, ur.name, ur.email, ur.role, uc.tier, uc.money, r.name AS position
             FROM users ur
             LEFT JOIN user_customer uc ON uc.customer_id = ur.user_id
             LEFT JOIN user_employee ue ON ue.employee_id = ur.user_id
             LEFT JOIN role_line rl ON rl.role_line_id = ue.role_line_id
             LEFT JOIN `role` r ON r.role_id = rl.role_id
             WHERE 1=1"""
    param = []
    if filters.get("role"):
        sql += " AND ur.role = %s"
        param.append(filters["role"])
    if filters.get("tier"):
        sql += " AND uc.tier = %s"
        param.append(filters["tier"])

    if filters.get("name"):
        sql += " AND ur.name LIKE %s"
        param.append(f"%{filters['name']}%")

    if filters.get("email"):
        sql += " AND ur.email LIKE %s"
        param.append(f"%{filters['email']}%")

    return run_query(sql, param)


def get_customer(user_id):
    sql = """SELECT ur.user_id, ur.name, ur.email, ur.role, uc.tier, uc.money,
                    rl.role_id, r.name AS position
             FROM users ur
             LEFT JOIN user_customer uc ON uc.customer_id = ur.user_id
             LEFT JOIN user_employee ue ON ue.employee_id = ur.user_id
             LEFT JOIN role_line rl ON rl.role_line_id = ue.role_line_id
             LEFT JOIN `role` r ON r.role_id = rl.role_id
             WHERE ur.user_id = %s"""
    rows = run_query(sql, (user_id,))
    if rows:
        return rows[0]
    return None


def create_customer(data):
    token = "usr_tok_" + uuid.uuid4().hex[:12]
    role = data.get("role") or "customer"
    if role not in ("customer", "employee"):
        raise ValueError("สิทธิไม่ถูกต้อง: ต้องเป็น customer หรือ employee")
    if role == "employee" and not data.get("role_id"):
        raise ValueError("กรุณาเลือกตำแหน่งพนักงาน")

    # บันทึกลงตาราง users ก่อน
    sql_user = "INSERT INTO users (name, email, password, role, user_token) VALUES (%s, %s, %s, %s, %s)"
    res = run_command(sql_user, (data.get("name"), data.get("email"), "123456", role, token))
    new_user_id = res["new_id"]

    # user_customer เก็บเฉพาะลูกค้า 
    if role == "customer":
        tier = data.get("tier", "normal")
        money = float(data.get("money") or 0.0)
        run_command(
            "INSERT INTO user_customer (customer_id, tier, money) VALUES (%s, %s, %s)",
            (new_user_id, tier, money))
    else:
        role_id = data.get("role_id")
        if not role_id:
            raise ValueError("กรุณาเลือกตำแหน่งพนักงาน")
        rl = run_command("INSERT INTO role_line (role_id) VALUES (%s)", (int(role_id),))
        run_command(
            "INSERT INTO user_employee (employee_id, role_line_id) VALUES (%s, %s)",
            (new_user_id, rl["new_id"]))

    return res


def update_customer(user_id, data):
    rows = run_query("SELECT role FROM users WHERE user_id = %s", (user_id,))
    if not rows:
        return {"affected": 0}

    old_role = rows[0]["role"]
    new_role = data.get("role") or old_role
    if new_role not in ("customer", "employee"):
        raise ValueError("สิทธิไม่ถูกต้อง: ต้องเป็น customer หรือ employee")
    if new_role == "employee" and old_role != "employee" and not data.get("role_id"):
        raise ValueError("กรุณาเลือกตำแหน่งพนักงาน")

    res = run_command(
        "UPDATE users SET name = %s, email = %s, role = %s WHERE user_id = %s",
        (data.get("name"), data.get("email"), new_role, user_id))

    if old_role == "customer" and new_role == "employee":
        run_command("DELETE FROM user_customer WHERE customer_id = %s", (user_id,))
        role_id = data.get("role_id")
        if not role_id:
            raise ValueError("กรุณาเลือกตำแหน่งพนักงาน")
        rl = run_command("INSERT INTO role_line (role_id) VALUES (%s)", (int(role_id),))
        run_command(
            "INSERT INTO user_employee (employee_id, role_line_id) VALUES (%s, %s)",
            (user_id, rl["new_id"]))
    elif old_role == "employee" and new_role == "customer":
        rows2 = run_query("SELECT role_line_id FROM user_employee WHERE employee_id = %s", (user_id,))
        if rows2:
            run_command("DELETE FROM user_employee WHERE employee_id = %s", (user_id,))
            run_command("DELETE FROM role_line WHERE role_line_id = %s", (rows2[0]["role_line_id"],))
        tier = data.get("tier") or "normal"
        run_command("INSERT INTO user_customer (customer_id, tier) VALUES (%s, %s)", (user_id, tier))
    elif new_role == "employee":
        role_id = data.get("role_id")
        if role_id:
            run_command(
                """UPDATE role_line rl
                   INNER JOIN user_employee ue ON ue.role_line_id = rl.role_line_id
                   SET rl.role_id = %s
                   WHERE ue.employee_id = %s""",
                (int(role_id), user_id))
    elif new_role == "customer" and data.get("tier"):
        run_command("UPDATE user_customer SET tier = %s WHERE customer_id = %s", (data.get("tier"), user_id))
    return res


def delete_customer(user_id):
    # ตาราง user_customer มี ON DELETE CASCADE อยู่แล้ว ลบ users ตัวเดียวได้เลย
    return run_command("DELETE FROM users WHERE user_id = %s", (user_id,))


# ---------- สิทธิ์ (role) ----------
def list_roles(filters=None):
    filters = filters or {}
    sql = "SELECT role_id, name FROM `role` WHERE 1=1"
    param = []
    if filters.get("name"):
        sql += " AND name LIKE %s"
        param.append("%" + filters["name"] + "%")
    sql += " ORDER BY role_id"
    return run_query(sql, param)


def get_role(role_id):
    rows = run_query("SELECT role_id, name FROM `role` WHERE role_id = %s", (role_id,))
    if rows:
        return rows[0]
    return None


def create_role(data):
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("กรุณากรอกชื่อตำแหน่ง")
    return run_command("INSERT INTO `role` (name) VALUES (%s)", (name,))


def update_role(role_id, data):
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("กรุณากรอกชื่อตำแหน่ง")
    return run_command("UPDATE `role` SET name = %s WHERE role_id = %s", (name, role_id))


def delete_role(role_id):
    used = run_query("SELECT COUNT(*) AS c FROM role_line WHERE role_id = %s", (role_id,))[0]["c"]
    if used:
        raise ValueError("ลบไม่ได้: มีพนักงาน %d คนใช้ตำแหน่งนี้อยู่" % used)
    return run_command("DELETE FROM `role` WHERE role_id = %s", (role_id,))


# ---------- หมวดหมู่ (category) ----------
def list_categories(filters=None):
    filters = filters or {}
    sql = "SELECT category_id, name, category_token FROM category WHERE 1=1"
    param = []
    if filters.get("name"):
        sql += " AND name LIKE %s"
        param.append("%" + filters["name"] + "%")
    sql += " ORDER BY category_id"
    return run_query(sql, param)


def get_category(category_id):
    rows = run_query("SELECT * FROM category WHERE category_id = %s", (category_id,))
    if rows:
        return rows[0]
    return None


def create_category(data):
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("กรุณากรอกชื่อหมวดหมู่")
    token = "cat_tok_" + uuid.uuid4().hex[:12]
    return run_command(
        "INSERT INTO category (name, category_token) VALUES (%s, %s)",
        (name, token))


def update_category(category_id, data):
    return run_command(
        "UPDATE category SET name = %s WHERE category_id = %s",
        (data.get("name"), category_id)
    )


def delete_category(category_id):
    # ลบใน category_line ก่อน แล้วค่อยลบหมวดหมู่
    cat = get_category(category_id)
    if cat:
        run_command("DELETE FROM category_line WHERE category_token = %s", (cat["category_token"],))
        return run_command("DELETE FROM category WHERE category_id = %s", (category_id,))
    return {"affected": 0}


# ---------- สินค้า (product) ----------
def search_products(filters):
    sql = """SELECT DISTINCT p.product_id, p.name, p.detail, p.price, p.total AS stock, 
                    p.isOpen, p.product_token, p.employee_id, p.created_at
             FROM product p
             LEFT JOIN category_line cl ON p.product_token = cl.product_token
             LEFT JOIN category c ON cl.category_token = c.category_token
             WHERE 1=1"""
    param = []
    if filters.get("name"):
        sql += " AND p.name LIKE %s"
        param.append("%" + filters["name"] + "%")
    if filters.get("category"):
        sql += " AND c.name = %s"
        param.append(filters["category"])
        
    sql += " ORDER BY p.product_id"
    return run_query(sql, param)


def get_product(product_id):
    rows = run_query("SELECT *, total AS stock FROM product WHERE product_id = %s", (product_id,))
    if not rows:
        return None
    product = rows[0]
    product["categories"] = get_product_categories(product_id)
    return product


def create_product(data):
    product_token = "prd_tok_" + uuid.uuid4().hex[:12]

    raw_open = data.get("isOpen", True)
    if isinstance(raw_open, str):
        is_open = raw_open.strip().lower() in ("1", "true", "yes", "on")
    else:
        is_open = bool(raw_open)
    user_id = int(data.get("employee_id") or data.get("user_id") or 1)

    res = run_command(
        "INSERT INTO product (`name`, `detail`, `price`, `total`, `isOpen`, `product_token`, `employee_id`) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (data.get("name", ""), data.get("detail", ""), float(data.get("price") or 0),
         int(data.get("stock") or 0), is_open, product_token, user_id))
    for name in data.get("categories") or []:
        run_command(
            "INSERT INTO category_line (category_token, product_token) "
            "SELECT category_token, %s FROM category WHERE `name` = %s", (product_token, name))
    return res


def get_product_categories(product_id):
    sql = """SELECT c.name 
             FROM product p
             INNER JOIN category_line cl ON p.product_token = cl.product_token
             INNER JOIN category c ON cl.category_token = c.category_token
             WHERE p.product_id = %s"""
    rows = run_query(sql, (product_id,))
    categories = []
    for r in rows:
        categories.append(r["name"])
    return categories


def set_product_categories(product_id, categories):
    rows = run_query("SELECT product_token FROM product WHERE product_id = %s", (product_id,))
    if not rows:
        return
    token = rows[0]["product_token"]
    
    # ลบหมวดหมู่เดิมทิ้ง
    run_command("DELETE FROM category_line WHERE product_token = %s", (token,))
    for name in categories or []:
        run_command(
            "INSERT INTO category_line (category_token, product_token) "
            "SELECT category_token, %s FROM category WHERE `name` = %s", (token, name))


def update_product(product_id, data):
    sql = "UPDATE product SET name = %s, detail = %s, price = %s, total = %s WHERE product_id = %s"
    res = run_command(sql, (data.get("name"), data.get("detail"), float(data.get("price") or 0), int(data.get("stock") or 0), product_id))
    
    if "categories" in data:
        set_product_categories(product_id, data.get("categories"))
    return res


def delete_product(product_id):
    rows = run_query("SELECT product_token FROM product WHERE product_id = %s", (product_id,))
    if rows:
        token = rows[0]["product_token"]
        run_command("DELETE FROM category_line WHERE product_token = %s", (token,))
        return run_command("DELETE FROM product WHERE product_id = %s", (product_id,))
    return {"affected": 0}


# ---------- ที่อยู่ (address) ----------
def list_addresses(filters=None):
    filters = filters or {}
    sql = """SELECT address_token, user_id, full_name, phone, house_address, sub_district, district, province
             FROM address WHERE 1=1"""
    param = []
    if filters.get("user_id"):
        sql += " AND user_id = %s"
        param.append(filters["user_id"])
    sql += " ORDER BY address_id"
    return run_query(sql, param)


def create_address(data):
    if not data.get("user_id"):
        raise ValueError("กรุณาเลือกลูกค้าก่อน")
    required = [("full_name", "ชื่อผู้รับ"), ("phone", "เบอร์โทร"), ("house_address", "บ้านเลขที่"),
                ("sub_district", "ตำบล/แขวง"), ("district", "อำเภอ/เขต"),
                ("province", "จังหวัด"), ("postal_code", "รหัสไปรษณีย์")]
    for key, label in required:
        if not str(data.get(key) or "").strip():
            raise ValueError("กรุณากรอก" + label)
    token = "addr_tok_" + uuid.uuid4().hex[:12]
    return run_command(
        """INSERT INTO address (user_id, full_name, phone, house_address, moo, soi, road,
                                sub_district, district, province, postal_code, note, address_token)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (int(data["user_id"]), data.get("full_name"), data.get("phone"), data.get("house_address"),
         data.get("moo") or "-", data.get("soi") or "-", data.get("road") or "-",
         data.get("sub_district"), data.get("district"), data.get("province"),
         int(data.get("postal_code") or 0), data.get("note"), token))


# ---------- ออเดอร์ (shop_order) ----------
def search_orders(filters):
    sql = """SELECT o.order_id, o.customer_id, u.name AS user_name, o.order_date, 
                    o.total_amount, o.status, o.address_token
             FROM shop_order o
             INNER JOIN users u ON o.customer_id = u.user_id
             WHERE 1=1"""
    param = []
    if filters.get("customer_id") or filters.get("user_id"):
        sql += " AND o.customer_id = %s"
        param.append(filters.get("customer_id") or filters.get("user_id"))
    if filters.get("status"):
        sql += " AND o.status = %s"
        param.append(filters["status"])
        
    sql += " ORDER BY o.order_id DESC"
    return run_query(sql, param)


def get_order(order_id):
    rows = run_query("SELECT * FROM shop_order WHERE order_id = %s", (order_id,))
    if rows:
        return rows[0]
    return None


def create_order(data):
    cols = ["customer_id", "address_token", "total_amount", "status"]
    vals = [data.get("customer_id") or data.get("user_id"), data.get("address_token"),
            float(data.get("total_amount") or 0.0), data.get("status") or "pending"]
    if data.get("order_date"):
        cols.append("order_date")
        vals.append(data["order_date"])

    sql = "INSERT INTO shop_order (`" + "`, `".join(cols) + "`) VALUES (" + \
          ", ".join(["%s"] * len(cols)) + ")"
    return run_command(sql, tuple(vals))


def update_order(order_id, data):
    status = data.get("status") or "pending"
    if status not in ORDER_STATUSES:
        raise ValueError("สถานะไม่ถูกต้อง: " + str(status))
    sets = ["status = %s", "address_token = %s", "total_amount = %s"]
    vals = [status, data.get("address_token"), float(data.get("total_amount") or 0.0)]
    if data.get("order_date"):
        sets.append("order_date = %s")
        vals.append(data["order_date"])
    vals.append(order_id)

    sql = "UPDATE shop_order SET " + ", ".join(sets) + " WHERE order_id = %s"
    return run_command(sql, tuple(vals))


def create_customer_order(data):
    """ลูกค้าสร้างออเดอร์เอง — insert shop_order + order_line ใน transaction เดียว
    (ไม่หักเงิน/ไม่ตัดสต็อก ตามข้อกำหนด)"""
    customer_id = data.get("customer_id") or data.get("user_id")
    address_token = data.get("address_token")
    items = data.get("items") or []
    if not customer_id:
        raise ValueError("กรุณาเลือกลูกค้า")
    if not address_token:
        raise ValueError("กรุณาเลือกที่อยู่จัดส่ง")

    clean = []
    for it in items:
        try:
            pid = int(it.get("product_id"))
            qty = int(it.get("quantity"))
        except (TypeError, ValueError):
            raise ValueError("รายการสินค้าไม่ถูกต้อง")
        if pid and qty > 0:
            clean.append((pid, qty))
    if not clean:
        raise ValueError("กรุณาเพิ่มรายการสินค้าอย่างน้อย 1 รายการ")

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT customer_id FROM user_customer WHERE customer_id = %s", (customer_id,))
        if not cur.fetchone():
            raise ValueError("ไม่พบลูกค้ารหัส " + str(customer_id))

        cur.execute("SELECT address_token FROM address WHERE address_token = %s AND user_id = %s",
                    (address_token, customer_id))
        if not cur.fetchone():
            raise ValueError("ที่อยู่ไม่ถูกต้อง หรือไม่ใช่ของลูกค้าคนนี้")

        ids = [p for p, _ in clean]
        fmt = ", ".join(["%s"] * len(ids))
        cur.execute("SELECT product_id, price FROM product WHERE product_id IN (" + fmt + ")", ids)
        products = {r["product_id"]: r for r in cur.fetchall()}

        total = 0.0
        for pid, qty in clean:
            if pid not in products:
                raise ValueError("ไม่พบสินค้ารหัส " + str(pid))
            total += float(products[pid]["price"]) * qty

        cur.execute(
            """INSERT INTO shop_order (customer_id, employee_id, total_amount, status, address_token)
               VALUES (%s, NULL, %s, 'pending', %s)""",
            (customer_id, total, address_token))
        order_id = cur.lastrowid

        for pid, qty in clean:
            cur.execute(
                "INSERT INTO order_line (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                (order_id, pid, qty, products[pid]["price"]))

        conn.commit()
        return {"new_id": order_id, "affected": len(clean), "total_amount": round(total, 2)}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def delete_order(order_id):
    return run_command("DELETE FROM shop_order WHERE order_id = %s", (order_id,))


# ============================================================
#  REPORT (รายงาน — ใช้ JOIN + GROUP BY + subquery)
# ============================================================
def report_summary():
    """ตัวเลขสรุปบนการ์ด dashboard"""
    users = run_query("SELECT COUNT(*) AS total FROM users WHERE role = 'customer'")[0]["total"]
    products = run_query("SELECT COUNT(*) AS total FROM product")[0]["total"]
    orders = run_query("SELECT COUNT(*) AS total FROM shop_order")[0]["total"]
    sales_data = run_query("SELECT SUM(total_amount) AS total FROM shop_order WHERE status IN ('paid','delivered','succeed','shipped')")[0]["total"]
    total_sales = float(sales_data) if sales_data else 0.0
    reviews = run_query("SELECT COUNT(*) AS total FROM review")[0]["total"]

    return {
        "customers": users,
        "products": products,
        "orders": orders,
        "reviews": reviews,
        "total_sales": total_sales
    }


def report_best_selling():
    """📈 สินค้าขายดี (Best Sellers)"""
    sql = """SELECT p.product_id, p.name, 
                    SUM(ol.quantity) AS total_sold, 
                    SUM(ol.quantity * ol.unit_price) AS total_revenue
             FROM order_line ol
             INNER JOIN product p ON ol.product_id = p.product_id
             GROUP BY p.product_id, p.name
             ORDER BY total_sold DESC
             LIMIT 5"""
    return run_query(sql)


def report_customers_above_avg():
    """🏅 ลูกค้าที่ซื้อมากกว่าค่าเฉลี่ย (Above Average)"""
    sql = """SELECT u.user_id, u.name, u.email, 
                    SUM(ol.quantity * ol.unit_price) AS total_spent
             FROM users u
             INNER JOIN shop_order o ON u.user_id = o.customer_id
             INNER JOIN order_line ol ON o.order_id = ol.order_id
             GROUP BY u.user_id, u.name, u.email
             HAVING total_spent > (
                 SELECT AVG(sub.total) FROM (
                     SELECT SUM(ol2.quantity * ol2.unit_price) AS total
                     FROM shop_order o2
                     INNER JOIN order_line ol2 ON o2.order_id = ol2.order_id
                     GROUP BY o2.customer_id
                 ) AS sub
             )
             ORDER BY total_spent DESC"""
    return run_query(sql)


def report_high_rated():
    """⭐ สินค้าคะแนนรีวิวเฉลี่ย ≥ 4 (HAVING)"""
    sql = """SELECT p.product_id, p.name, 
                    ROUND(AVG(r.rating), 2) AS avg_rating, 
                    COUNT(r.review_id) AS review_count
             FROM review r
             INNER JOIN product p ON r.product_id = p.product_id
             GROUP BY p.product_id, p.name
             HAVING AVG(r.rating) >= 4
             ORDER BY avg_rating DESC"""
    return run_query(sql)