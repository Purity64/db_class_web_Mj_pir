# ============================================================
#  db.py — ชั้นติดต่อฐานข้อมูล  ★★★ นิสิตเขียน SQL ในไฟล์นี้ ★★★
#  มองหาคำว่า  # TODO  ทุกฟังก์ชัน — ใช้ %s เป็น placeholder เสมอ (กัน SQL injection)
# ============================================================
import mysql.connector
import config
import uuid

ORDER_STATUSES = ("pending", "waiting_paid", "paid", "delivered", "cancelled", "succeed", "shipped")
PAYMENT_STATUSES = ("pending", "verified")
TERMINAL_STATUSES = ("succeed", "cancelled")
PAYMENT_METHODS = ("cash", "bank", "point")
USER_ROLES = ("customer", "employee")
TIERS = ("normal", "vip")

# =============== ชั้นช่วยเชื่อมต่อ / transaction ===============
def get_connection():
    return mysql.connector.connect(
        host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD,
        database=config.DB_NAME, port=config.DB_PORT)


def _fetch(cur, sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


def _exec(cur, sql, params=None):
    cur.execute(sql, params or ())
    return {"new_id": cur.lastrowid, "affected": cur.rowcount}


def run_query(sql, params=None):
    """รัน SELECT คืนผลเป็น list ของ dict"""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        out = _fetch(cur, sql, params)
        cur.close()
        return out
    finally:
        conn.close()


def run_command(sql, params=None):
    """รัน INSERT / UPDATE / DELETE แล้ว commit"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        out = _exec(cur, sql, params)
        conn.commit()
        cur.close()
        return out
    finally:
        conn.close()


class transaction:
    """งานที่ต้องเขียนหลายคำสั่ง — สำเร็จทั้งหมดหรือย้อนกลับทั้งหมด

    ใช้แบบ:  with transaction() as tx:  tx.query(...) / tx.command(...)
    """
    def __init__(self):
        self.conn = get_connection()
        self.cur = self.conn.cursor(dictionary=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.cur.close()
            self.conn.close()
        return False

    def query(self, sql, params=None):
        return _fetch(self.cur, sql, params)

    def command(self, sql, params=None):
        return _exec(self.cur, sql, params)


# =============== ตัวช่วยตรวจข้อมูล ===============
def _text(data, key, label, required=False):
    value = data.get(key)
    value = "" if value is None else str(value).strip()
    if required and not value:
        raise ValueError("กรุณากรอก" + label)
    return value


def _to_float(value, label):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(label + "ต้องเป็นตัวเลข")


def _to_int(value, label):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise ValueError(label + "ต้องเป็นจำนวนเต็ม")


def _to_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _choice(value, allowed, label):
    if value not in allowed:
        raise ValueError(label + "ไม่ถูกต้อง: " + str(value))
    return value


def _set_clause(pairs):
    """[(column, value), ...] -> (SET ..., params)  ใส่เฉพาะคอลัมน์ที่ส่งมาเท่านั้น
    ค่า None แปลว่า "ล้างค่าให้เป็น NULL" (ใช้กับคอลัมน์ที่ยอมให้ว่างได้)"""
    sets, params = [], []
    for column, value in pairs:
        sets.append("`" + column + "` = %s")
        params.append(value)
    if not sets:
        return None, ()
    return ", ".join(sets), tuple(params)


def _one(tx, sql, params=None):
    rows = tx.query(sql, params)
    return rows[0] if rows else None


# ---------- ลูกค้า (customer) ----------
def search_customers(filters):
    filters = filters or {}
    sql = """SELECT ur.user_id, ur.name, ur.email, ur.role, ur.created_at,
                    uc.tier, uc.money, uc.referrals, r.name AS position
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
    if filters.get("position"):
        sql += " AND r.name = %s"
        param.append(filters["position"])

    if filters.get("name"):
        sql += " AND ur.name LIKE %s"
        param.append(f"%{filters['name']}%")

    if filters.get("email"):
        sql += " AND ur.email LIKE %s"
        param.append(f"%{filters['email']}%")

    sql += " ORDER BY ur.user_id"
    return run_query(sql, param)


def get_customer(user_id):
    sql = """SELECT ur.user_id, ur.name, ur.email, ur.role, ur.created_at,
                    uc.tier, uc.money, uc.referrals,
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


def _check_email(tx, email, exclude_id=None):
    if not email:
        return
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("อีเมลไม่ถูกต้อง")
    sql = "SELECT user_id FROM users WHERE email = %s"
    param = [email]
    if exclude_id:
        sql += " AND user_id <> %s"
        param.append(exclude_id)
    if tx.query(sql, tuple(param)):
        raise ValueError("อีเมลนี้ถูกใช้แล้ว")


def _require_role(tx, role_id):
    role_id = _to_int(role_id, "รหัสตำแหน่ง")
    if not _one(tx, "SELECT role_id FROM `role` WHERE role_id = %s", (role_id,)):
        raise ValueError("ไม่พบตำแหน่งพนักงานรหัส " + str(role_id))
    return role_id


def _resolve_categories(tx, categories):
    """คืนรายชื่อหมวดหมู่ที่มีจริง พร้อม error ถ้าเจอชื่อที่ไม่มีในระบบ"""
    if isinstance(categories, str):
        categories = categories.split(",")
    names = [str(c).strip() for c in (categories or []) if str(c).strip()]
    if not names:
        return []
    found = []
    for name in names:
        row = _one(tx, "SELECT category_token FROM category WHERE `name` = %s", (name,))
        if not row:
            raise ValueError("ไม่พบหมวดหมู่: " + name)
        found.append((name, row["category_token"]))
    return found


def create_customer(data):
    data = data or {}
    name = _text(data, "name", "ชื่อ", required=True)
    email = _text(data, "email", "อีเมล", required=True)
    role = _choice(data.get("role") or "customer", USER_ROLES, "สิทธิ")
    password = _text(data, "password", "รหัสผ่าน") or "123456"
    token = "usr_tok_" + uuid.uuid4().hex[:12]

    if role == "employee" and not data.get("role_id"):
        raise ValueError("กรุณาเลือกตำแหน่งพนักงาน")

    with transaction() as tx:
        _check_email(tx, email)
        res = tx.command(
            "INSERT INTO users (name, email, password, role, user_token) VALUES (%s, %s, %s, %s, %s)",
            (name, email, password, role, token))
        new_user_id = res["new_id"]

        # user_customer เก็บเฉพาะลูกค้า
        if role == "customer":
            tier = _choice(data.get("tier") or "normal", TIERS, "ระดับลูกค้า")
            money = _to_float(data.get("money") or 0.0, "ยอดเงิน")
            if money < 0:
                raise ValueError("ยอดเงินต้องไม่ติดลบ")
            referrals = None
            if data.get("referrals"):
                referrals = _to_int(data["referrals"], "รหัสผู้แนะนำ")
                if not _one(tx, "SELECT customer_id FROM user_customer WHERE customer_id = %s", (referrals,)):
                    raise ValueError("ไม่พบผู้แนะนำรหัส " + str(referrals))
                if referrals == new_user_id:
                    raise ValueError("ผู้แนะนำต้องไม่ใช่ตัวเอง")
            tx.command(
                "INSERT INTO user_customer (customer_id, referrals, tier, money) VALUES (%s, %s, %s, %s)",
                (new_user_id, referrals, tier, money))
        else:
            role_id = _require_role(tx, data["role_id"])
            rl = tx.command("INSERT INTO role_line (role_id) VALUES (%s)", (role_id,))
            tx.command(
                "INSERT INTO user_employee (employee_id, role_line_id) VALUES (%s, %s)",
                (new_user_id, rl["new_id"]))

        res["affected"] = 2
        return res


def update_customer(user_id, data):
    data = data or {}
    with transaction() as tx:
        current = _one(tx, "SELECT role FROM users WHERE user_id = %s", (user_id,))
        if not current:
            raise ValueError("ไม่พบผู้ใช้รหัส " + str(user_id))

        old_role = current["role"]
        new_role = _choice(data.get("role") or old_role, USER_ROLES, "สิทธิ")
        name = _text(data, "name", "ชื่อ")
        email = _text(data, "email", "อีเมล")

        pairs = []
        if name:
            pairs.append(("name", name))
        if email:
            pairs.append(("email", email))
        if new_role != old_role:
            pairs.append(("role", new_role))
        sets, params = _set_clause(pairs)
        affected = 0
        if sets:
            _check_email(tx, email, exclude_id=user_id)
            tx.command("UPDATE users SET " + sets + " WHERE user_id = %s", params + (user_id,))
            affected = 1

        if old_role == "customer" and new_role == "employee":
            role_id = _require_role(tx, data.get("role_id"))
            tx.command("DELETE FROM user_customer WHERE customer_id = %s", (user_id,))
            rl = tx.command("INSERT INTO role_line (role_id) VALUES (%s)", (role_id,))
            tx.command(
                "INSERT INTO user_employee (employee_id, role_line_id) VALUES (%s, %s)",
                (user_id, rl["new_id"]))
        elif old_role == "employee" and new_role == "customer":
            emp = _one(tx, "SELECT role_line_id FROM user_employee WHERE employee_id = %s", (user_id,))
            if emp:
                tx.command("DELETE FROM user_employee WHERE employee_id = %s", (user_id,))
                tx.command("DELETE FROM role_line WHERE role_line_id = %s", (emp["role_line_id"],))
            tier = _choice(data.get("tier") or "normal", TIERS, "ระดับลูกค้า")
            tx.command("INSERT INTO user_customer (customer_id, tier) VALUES (%s, %s)", (user_id, tier))
        elif new_role == "employee":
            if data.get("role_id"):
                role_id = _require_role(tx, data["role_id"])
                tx.command(
                    """UPDATE role_line rl
                       INNER JOIN user_employee ue ON ue.role_line_id = rl.role_line_id
                       SET rl.role_id = %s
                       WHERE ue.employee_id = %s""",
                    (role_id, user_id))
        elif new_role == "customer":
            cust_pairs = []
            if data.get("tier"):
                cust_pairs.append(("tier", _choice(data["tier"], TIERS, "ระดับลูกค้า")))
            if data.get("money") is not None:
                money = _to_float(data["money"], "ยอดเงิน")
                if money < 0:
                    raise ValueError("ยอดเงินต้องไม่ติดลบ")
                cust_pairs.append(("money", money))
            if data.get("referrals") is not None:
                referrals = data["referrals"]
                if str(referrals).strip() in ("", "0", "None"):
                    cust_pairs.append(("referrals", None))
                else:
                    ref = _to_int(referrals, "รหัสผู้แนะนำ")
                    if ref == user_id:
                        raise ValueError("ผู้แนะนำต้องไม่ใช่ตัวเอง")
                    if not _one(tx, "SELECT customer_id FROM user_customer WHERE customer_id = %s", (ref,)):
                        raise ValueError("ไม่พบผู้แนะนำรหัส " + str(ref))
                    cust_pairs.append(("referrals", ref))
            c_sets, c_params = _set_clause(cust_pairs)
            if c_sets:
                tx.command("UPDATE user_customer SET " + c_sets + " WHERE customer_id = %s",
                           c_params + (user_id,))

        return {"new_id": 0, "affected": affected}


def delete_customer(user_id):
    with transaction() as tx:
        if not _one(tx, "SELECT user_id FROM users WHERE user_id = %s", (user_id,)):
            raise ValueError("ไม่พบผู้ใช้รหัส " + str(user_id))

        used = _one(tx, "SELECT COUNT(*) AS c FROM shop_order WHERE customer_id = %s", (user_id,))["c"]
        if used:
            raise ValueError("ลบไม่ได้: ลูกค้าคนนี้มีออเดอร์ %d รายการ" % used)
        owns = _one(tx, "SELECT COUNT(*) AS c FROM product WHERE employee_id = %s", (user_id,))["c"]
        if owns:
            raise ValueError("ลบไม่ได้: พนักงานคนนี้ดูแลสินค้า %d ชิ้น" % owns)

        # user_customer / user_employee / address ถูกลบด้วย ON DELETE CASCADE
        return tx.command("DELETE FROM users WHERE user_id = %s", (user_id,))


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
    name = _text(data or {}, "name", "ชื่อตำแหน่ง", required=True)
    with transaction() as tx:
        if _one(tx, "SELECT role_id FROM `role` WHERE `name` = %s", (name,)):
            raise ValueError("มีตำแหน่งชื่อนี้อยู่แล้ว")
        return tx.command("INSERT INTO `role` (name) VALUES (%s)", (name,))


def update_role(role_id, data):
    name = _text(data or {}, "name", "ชื่อตำแหน่ง", required=True)
    with transaction() as tx:
        if not _one(tx, "SELECT role_id FROM `role` WHERE role_id = %s", (role_id,)):
            raise ValueError("ไม่พบตำแหน่งรหัส " + str(role_id))
        if _one(tx, "SELECT role_id FROM `role` WHERE `name` = %s AND role_id <> %s", (name, role_id)):
            raise ValueError("มีตำแหน่งชื่อนี้อยู่แล้ว")
        return tx.command("UPDATE `role` SET name = %s WHERE role_id = %s", (name, role_id))


def delete_role(role_id):
    with transaction() as tx:
        if not _one(tx, "SELECT role_id FROM `role` WHERE role_id = %s", (role_id,)):
            raise ValueError("ไม่พบตำแหน่งรหัส " + str(role_id))
        used = _one(tx, "SELECT COUNT(*) AS c FROM role_line WHERE role_id = %s", (role_id,))["c"]
        if used:
            raise ValueError("ลบไม่ได้: มีพนักงาน %d คนใช้ตำแหน่งนี้อยู่" % used)
        return tx.command("DELETE FROM `role` WHERE role_id = %s", (role_id,))


# ---------- หมวดหมู่ (category) ----------
def list_categories(filters=None):
    filters = filters or {}
    sql = "SELECT category_id, name, category_token, created_at FROM category WHERE 1=1"
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
    name = _text(data or {}, "name", "ชื่อหมวดหมู่", required=True)
    token = "cat_tok_" + uuid.uuid4().hex[:12]
    with transaction() as tx:
        if _one(tx, "SELECT category_id FROM category WHERE `name` = %s", (name,)):
            raise ValueError("มีหมวดหมู่ชื่อนี้อยู่แล้ว")
        return tx.command(
            "INSERT INTO category (name, category_token) VALUES (%s, %s)",
            (name, token))


def update_category(category_id, data):
    name = _text(data or {}, "name", "ชื่อหมวดหมู่", required=True)
    with transaction() as tx:
        if not _one(tx, "SELECT category_id FROM category WHERE category_id = %s", (category_id,)):
            raise ValueError("ไม่พบหมวดหมู่รหัส " + str(category_id))
        if _one(tx, "SELECT category_id FROM category WHERE `name` = %s AND category_id <> %s",
                (name, category_id)):
            raise ValueError("มีหมวดหมู่ชื่อนี้อยู่แล้ว")
        return tx.command(
            "UPDATE category SET `name` = %s WHERE category_id = %s",
            (name, category_id))


def delete_category(category_id):
    with transaction() as tx:
        cat = _one(tx, "SELECT category_id, category_token FROM category WHERE category_id = %s",
                   (category_id,))
        if not cat:
            raise ValueError("ไม่พบหมวดหมู่รหัส " + str(category_id))
        # ลบใน category_line ก่อน แล้วค่อยลบหมวดหมู่
        tx.command("DELETE FROM category_line WHERE category_token = %s", (cat["category_token"],))
        return tx.command("DELETE FROM category WHERE category_id = %s", (category_id,))


# ---------- สินค้า (product) ----------
def search_products(filters):
    filters = filters or {}
    sql = """SELECT p.product_id, p.name, p.detail, p.price, p.total AS stock,
                    p.isOpen, p.product_token, p.employee_id, p.created_at,
                    GROUP_CONCAT(DISTINCT c.`name` ORDER BY c.`name` SEPARATOR ', ') AS categories
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
    if filters.get("is_open") is not None and filters.get("is_open") != "":
        sql += " AND p.isOpen = %s"
        param.append(1 if _to_bool(filters["is_open"]) else 0)
    if filters.get("employee_id"):
        sql += " AND p.employee_id = %s"
        param.append(_to_int(filters["employee_id"], "รหัสพนักงาน"))
    if filters.get("min_price"):
        sql += " AND p.price >= %s"
        param.append(_to_float(filters["min_price"], "ราคาต่ำสุด"))
    if filters.get("max_price"):
        sql += " AND p.price <= %s"
        param.append(_to_float(filters["max_price"], "ราคาสูงสุด"))
    if filters.get("low_stock"):
        sql += " AND p.total <= %s"
        param.append(_to_int(filters["low_stock"], "จำนวนสต็อก"))

    sql += """ GROUP BY p.product_id, p.name, p.detail, p.price, p.total,
                      p.isOpen, p.product_token, p.employee_id, p.created_at
              ORDER BY p.product_id"""
    return run_query(sql, param)


def get_product(product_id):
    rows = run_query("SELECT *, total AS stock FROM product WHERE product_id = %s", (product_id,))
    if not rows:
        return None
    product = rows[0]
    product["categories"] = get_product_categories(product_id)
    return product


def _product_fields(tx, data):
    pairs = []
    if "name" in data:
        name = _text(data, "name", "ชื่อสินค้า", required=True)
        pairs.append(("name", name))
    if "detail" in data:
        pairs.append(("detail", _text(data, "detail", "รายละเอียดสินค้า")))
    if "price" in data:
        price = _to_float(data["price"], "ราคา")
        if price < 0:
            raise ValueError("ราคาต้องไม่ติดลบ")
        pairs.append(("price", price))
    if "stock" in data:
        stock = _to_int(data["stock"], "สต็อก")
        if stock < 0:
            raise ValueError("สต็อกต้องไม่ติดลบ")
        pairs.append(("total", stock))
    if "isOpen" in data:
        pairs.append(("isOpen", 1 if _to_bool(data["isOpen"]) else 0))
    if "employee_id" in data:
        emp_id = _to_int(data["employee_id"], "รหัสพนักงาน")
        if not _one(tx, "SELECT employee_id FROM user_employee WHERE employee_id = %s", (emp_id,)):
            raise ValueError("ไม่พบพนักงานรหัส " + str(emp_id))
        pairs.append(("employee_id", emp_id))
    return pairs


def create_product(data):
    data = data or {}
    product_token = "prd_tok_" + uuid.uuid4().hex[:12]
    with transaction() as tx:
        name = _text(data, "name", "ชื่อสินค้า", required=True)
        detail = _text(data, "detail", "รายละเอียดสินค้า")
        price = _to_float(data.get("price") or 0, "ราคา")
        stock = _to_int(data.get("stock") or 0, "สต็อก")
        if price < 0 or stock < 0:
            raise ValueError("ราคาและสต็อกต้องไม่ติดลบ")
        is_open = 1 if _to_bool(data.get("isOpen", True)) else 0
        emp_id = _to_int(data.get("employee_id") or data.get("user_id") or 1, "รหัสพนักงาน")
        if not _one(tx, "SELECT employee_id FROM user_employee WHERE employee_id = %s", (emp_id,)):
            raise ValueError("ไม่พบพนักงานรหัส " + str(emp_id))
        pairs = [("name", name), ("detail", detail), ("price", price),
                 ("total", stock), ("isOpen", is_open), ("employee_id", emp_id)]

        sets, params = _set_clause(pairs)
        res = tx.command(
            "INSERT INTO product SET " + sets + ", product_token = %s", params + (product_token,))

        cats = _resolve_categories(tx, data.get("categories"))
        for name_, cat_token in cats:
            tx.command(
                "INSERT INTO category_line (category_token, product_token) VALUES (%s, %s)",
                (cat_token, product_token))
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


def _set_product_categories(tx, product_token, categories):
    tx.command("DELETE FROM category_line WHERE product_token = %s", (product_token,))
    for name, cat_token in _resolve_categories(tx, categories):
        tx.command(
            "INSERT INTO category_line (category_token, product_token) VALUES (%s, %s)",
            (cat_token, product_token))


def set_product_categories(product_id, categories):
    with transaction() as tx:
        row = _one(tx, "SELECT product_token FROM product WHERE product_id = %s", (product_id,))
        if not row:
            raise ValueError("ไม่พบสินค้ารหัส " + str(product_id))
        _set_product_categories(tx, row["product_token"], categories)
        return {"new_id": 0, "affected": 1}


def update_product(product_id, data):
    data = data or {}
    with transaction() as tx:
        row = _one(tx, "SELECT product_token FROM product WHERE product_id = %s", (product_id,))
        if not row:
            raise ValueError("ไม่พบสินค้ารหัส " + str(product_id))

        pairs = _product_fields(tx, data)
        sets, params = _set_clause(pairs)
        res = {"new_id": 0, "affected": 0}
        if sets:
            res = tx.command("UPDATE product SET " + sets + " WHERE product_id = %s",
                             params + (product_id,))
        if "categories" in data:
            _set_product_categories(tx, row["product_token"], data.get("categories"))
        return res


def delete_product(product_id):
    with transaction() as tx:
        row = _one(tx, "SELECT product_token FROM product WHERE product_id = %s", (product_id,))
        if not row:
            raise ValueError("ไม่พบสินค้ารหัส " + str(product_id))
        sold = _one(tx, "SELECT COUNT(*) AS c FROM order_line WHERE product_id = %s", (product_id,))["c"]
        if sold:
            raise ValueError("ลบไม่ได้: สินค้านี้ถูกสั่งซื้อแล้ว %d รายการ" % sold)
        tx.command("DELETE FROM category_line WHERE product_token = %s", (row["product_token"],))
        return tx.command("DELETE FROM product WHERE product_id = %s", (product_id,))


# ---------- ที่อยู่ (address) ----------
def list_addresses(filters=None):
    filters = filters or {}
    sql = """SELECT address_id, address_token, user_id, full_name, phone, house_address,
                    moo, soi, road, sub_district, district, province, postal_code, note, created_at
             FROM address WHERE 1=1"""
    param = []
    if filters.get("user_id"):
        sql += " AND user_id = %s"
        param.append(_to_int(filters["user_id"], "รหัสผู้ใช้"))
    if filters.get("province"):
        sql += " AND province = %s"
        param.append(filters["province"])
    if filters.get("q"):
        sql += " AND (full_name LIKE %s OR house_address LIKE %s OR district LIKE %s)"
        like = "%" + filters["q"] + "%"
        param.extend([like, like, like])
    sql += " ORDER BY address_id"
    return run_query(sql, param)


def get_address(address_id):
    rows = run_query("SELECT * FROM address WHERE address_id = %s", (address_id,))
    if rows:
        return rows[0]
    return None


ADDRESS_REQUIRED = (("full_name", "ชื่อผู้รับ"), ("phone", "เบอร์โทร"), ("house_address", "บ้านเลขที่"),
                    ("sub_district", "ตำบล/แขวง"), ("district", "อำเภอ/เขต"),
                    ("province", "จังหวัด"), ("postal_code", "รหัสไปรษณีย์"))


def _address_pairs(data, partial):
    pairs = []
    for key, label in ADDRESS_REQUIRED:
        if partial and key not in data:
            continue
        value = _text(data, key, label, required=not partial)
        if partial and not value:
            continue
        if key == "postal_code":
            value = _to_int(value, label)
            if not 0 < value < 100000:
                raise ValueError("รหัสไปรษณีย์ไม่ถูกต้อง")
        pairs.append((key, value))
    for key in ("moo", "soi", "road"):
        if partial and key not in data:
            continue
        pairs.append((key, _text(data, key, "ที่อยู่") or "-"))
    if not partial or "note" in data:
        pairs.append(("note", _text(data, "note", "หมายเหตุ") or None))
    return pairs


def create_address(data):
    data = data or {}
    if not data.get("user_id"):
        raise ValueError("กรุณาเลือกลูกค้าก่อน")
    user_id = _to_int(data["user_id"], "รหัสผู้ใช้")
    if not run_query("SELECT user_id FROM users WHERE user_id = %s", (user_id,)):
        raise ValueError("ไม่พบผู้ใช้รหัส " + str(user_id))

    token = "addr_tok_" + uuid.uuid4().hex[:12]
    pairs = [("user_id", user_id)] + _address_pairs(data, partial=False)
    sets, params = _set_clause(pairs)
    return run_command(
        "INSERT INTO address SET " + sets + ", address_token = %s", params + (token,))


def update_address(address_id, data):
    data = data or {}
    pairs = _address_pairs(data, partial=True)
    sets, params = _set_clause(pairs)
    if not sets:
        return {"new_id": 0, "affected": 0}
    with transaction() as tx:
        if not _one(tx, "SELECT address_id FROM address WHERE address_id = %s", (address_id,)):
            raise ValueError("ไม่พบที่อยู่รหัส " + str(address_id))
        return tx.command("UPDATE address SET " + sets + " WHERE address_id = %s",
                          params + (address_id,))


def delete_address(address_id):
    with transaction() as tx:
        row = _one(tx, "SELECT address_token FROM address WHERE address_id = %s", (address_id,))
        if not row:
            raise ValueError("ไม่พบที่อยู่รหัส " + str(address_id))
        used = _one(tx, "SELECT COUNT(*) AS c FROM shop_order WHERE address_token = %s",
                    (row["address_token"],))["c"]
        if used:
            raise ValueError("ลบไม่ได้: ที่อยู่นี้ถูกใช้ในออเดอร์ %d รายการ" % used)
        return tx.command("DELETE FROM address WHERE address_id = %s", (address_id,))


# ---------- ออเดอร์ (shop_order) ----------
ORDER_SORTS = {
    "order_id": "o.order_id", "order_date": "o.order_date",
    "total_amount": "o.total_amount", "status": "o.status",
}


def search_orders(filters):
    filters = filters or {}
    sql = """SELECT o.order_id, o.customer_id, u.name AS user_name, o.employee_id,
                    o.order_date, o.total_amount, o.status, o.address_token,
                    COALESCE(pay.paid_amount, 0) AS paid_amount,
                    ROUND(o.total_amount - COALESCE(pay.paid_amount, 0), 2) AS unpaid_amount
             FROM shop_order o
             INNER JOIN users u ON o.customer_id = u.user_id
LEFT JOIN (SELECT order_id, SUM(amount) AS paid_amount
                       FROM payment WHERE order_id IS NOT NULL AND status = 'verified'
                       GROUP BY order_id) pay
                    ON pay.order_id = o.order_id
             WHERE 1=1"""
    param = []
    if filters.get("customer_id") or filters.get("user_id"):
        sql += " AND o.customer_id = %s"
        param.append(filters.get("customer_id") or filters.get("user_id"))
    if filters.get("employee_id"):
        sql += " AND o.employee_id = %s"
        param.append(filters["employee_id"])
    if filters.get("status"):
        sql += " AND o.status = %s"
        param.append(filters["status"])
    if filters.get("date_from"):
        sql += " AND o.order_date >= %s"
        param.append(str(filters["date_from"]) + " 00:00:00")
    if filters.get("date_to"):
        sql += " AND o.order_date <= %s"
        param.append(str(filters["date_to"]) + " 23:59:59")
    if filters.get("min_amount"):
        sql += " AND o.total_amount >= %s"
        param.append(_to_float(filters["min_amount"], "ยอดรวมต่ำสุด"))
    if filters.get("max_amount"):
        sql += " AND o.total_amount <= %s"
        param.append(_to_float(filters["max_amount"], "ยอดรวมสูงสุด"))
    if filters.get("q"):
        sql += " AND (u.name LIKE %s OR o.address_token LIKE %s)"
        like = "%" + filters["q"] + "%"
        param.extend([like, like])

    sort = ORDER_SORTS.get(filters.get("sort") or "order_id", "o.order_id")
    sql += " ORDER BY " + sort + " DESC"
    return run_query(sql, param)


def get_order_items(order_id):
    sql = """SELECT ol.order_line_id, ol.product_id, p.name AS product_name,
                    ol.quantity, ol.unit_price,
                    ROUND(ol.quantity * ol.unit_price, 2) AS line_total
             FROM order_line ol
             INNER JOIN product p ON ol.product_id = p.product_id
             WHERE ol.order_id = %s
             ORDER BY ol.order_line_id"""
    return run_query(sql, (order_id,))


def get_order(order_id):
    rows = run_query("SELECT * FROM shop_order WHERE order_id = %s", (order_id,))
    if not rows:
        return None
    order = rows[0]
    order["items"] = get_order_items(order_id)
    order["payments"] = get_order_payments(order_id)
    return order


def _clean_items(tx, items):
    clean = []
    for it in items or []:
        try:
            pid = _to_int(it.get("product_id"), "รหัสสินค้า")
            qty = _to_int(it.get("quantity"), "จำนวน")
        except AttributeError:
            raise ValueError("รายการสินค้าไม่ถูกต้อง")
        if pid and qty > 0:
            clean.append((pid, qty))
    if not clean:
        raise ValueError("กรุณาเพิ่มรายการสินค้าอย่างน้อย 1 รายการ")

    ids = [p for p, _ in clean]
    fmt = ", ".join(["%s"] * len(ids))
    rows = tx.query("SELECT product_id, `name`, price FROM product WHERE product_id IN (" + fmt + ")", ids)
    products = {r["product_id"]: r for r in rows}
    missing = [str(p) for p in ids if p not in products]
    if missing:
        raise ValueError("ไม่พบสินค้ารหัส " + ", ".join(missing))
    return clean, products


def _sum_items(clean, products):
    return round(sum(float(products[pid]["price"]) * qty for pid, qty in clean), 2)


def _replace_items(tx, order_id, clean, products):
    tx.command("DELETE FROM order_line WHERE order_id = %s", (order_id,))
    total = 0.0
    for pid, qty in clean:
        tx.command(
            "INSERT INTO order_line (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
            (order_id, pid, qty, products[pid]["price"]))
        total += float(products[pid]["price"]) * qty
    return round(total, 2)


def set_order_items(order_id, items):
    with transaction() as tx:
        if not _one(tx, "SELECT order_id FROM shop_order WHERE order_id = %s", (order_id,)):
            raise ValueError("ไม่พบออเดอร์รหัส " + str(order_id))
        clean, products = _clean_items(tx, items)
        total = _replace_items(tx, order_id, clean, products)
        tx.command("UPDATE shop_order SET total_amount = %s WHERE order_id = %s", (total, order_id))
        return {"new_id": 0, "affected": len(clean), "total_amount": total}


def create_order(data):
    """พนักงานเปิดออเดอร์เอง — ถ้าส่ง items มาจะคำนวณยอดรวมจากราคาสินค้าให้อัตโนมัติ"""
    data = data or {}
    customer_id = data.get("customer_id") or data.get("user_id")
    address_token = _text(data, "address_token", "ที่อยู่ลูกค้า", required=True)
    if not customer_id:
        raise ValueError("กรุณาเลือกลูกค้า")
    status = _choice(data.get("status") or "pending", ORDER_STATUSES, "สถานะ")

    with transaction() as tx:
        if not _one(tx, "SELECT customer_id FROM user_customer WHERE customer_id = %s", (customer_id,)):
            raise ValueError("ไม่พบลูกค้ารหัส " + str(customer_id))
        if not _one(tx, "SELECT address_token FROM address WHERE address_token = %s AND user_id = %s",
                    (address_token, customer_id)):
            raise ValueError("ที่อยู่ไม่ถูกต้อง หรือไม่ใช่ของลูกค้าคนนี้")

        items = data.get("items")
        if items:
            clean, products = _clean_items(tx, items)
            total = _sum_items(clean, products)
        else:
            clean, products = [], {}
            total = round(_to_float(data.get("total_amount") or 0.0, "ยอดรวม"), 2)
        if total < 0:
            raise ValueError("ยอดรวมต้องไม่ติดลบ")

        cols = ["customer_id", "address_token", "total_amount", "status"]
        vals = [_to_int(customer_id, "รหัสลูกค้า"), address_token, total, status]
        if data.get("employee_id"):
            cols.append("employee_id")
            vals.append(_to_int(data["employee_id"], "รหัสพนักงาน"))
        if data.get("order_date"):
            cols.append("order_date")
            vals.append(data["order_date"])

        sql = "INSERT INTO shop_order (" + ", ".join("`" + c + "`" for c in cols) + ") VALUES (" + \
              ", ".join(["%s"] * len(cols)) + ")"
        res = tx.command(sql, tuple(vals))
        order_id = res["new_id"]

        for pid, qty in clean:
            tx.command(
                "INSERT INTO order_line (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                (order_id, pid, qty, products[pid]["price"]))
        res["total_amount"] = total
        return res


def update_order(order_id, data):
    """แก้ไขออเดอร์ — ส่งมาเฉพาะฟิลด์ที่ต้องการเปลี่ยน ฟิลด์อื่นยังอยู่เดิม"""
    data = data or {}
    with transaction() as tx:
        current = _one(tx, "SELECT * FROM shop_order WHERE order_id = %s", (order_id,))
        if not current:
            raise ValueError("ไม่พบออเดอร์รหัส " + str(order_id))

        pairs = []
        if "status" in data and data["status"]:
            status = _choice(data["status"], ORDER_STATUSES, "สถานะ")
            if current["status"] in TERMINAL_STATUSES and status != current["status"]:
                raise ValueError("ออเดอร์สถานะ '%s' เป็นสถานะสุดท้ายแล้ว เปลี่ยนไม่ได้" % current["status"])
            pairs.append(("status", status))
        if "address_token" in data:
            token = _text(data, "address_token", "ที่อยู่ลูกค้า", required=True)
            if token != current["address_token"] and not _one(
                    tx, "SELECT address_token FROM address WHERE address_token = %s AND user_id = %s",
                    (token, current["customer_id"])):
                raise ValueError("ที่อยู่ไม่ถูกต้อง หรือไม่ใช่ของลูกค้าคนนี้")
            pairs.append(("address_token", token))
        if "total_amount" in data and data["total_amount"] not in (None, ""):
            total = _to_float(data["total_amount"], "ยอดรวม")
            if total < 0:
                raise ValueError("ยอดรวมต้องไม่ติดลบ")
            pairs.append(("total_amount", total))
        if "order_date" in data and data["order_date"]:
            pairs.append(("order_date", data["order_date"]))
        if "employee_id" in data:
            emp = data["employee_id"]
            if emp in (None, "", "0"):
                pairs.append(("employee_id", None))
            else:
                emp_id = _to_int(emp, "รหัสพนักงาน")
                if not _one(tx, "SELECT employee_id FROM user_employee WHERE employee_id = %s", (emp_id,)):
                    raise ValueError("ไม่พบพนักงานรหัส " + str(emp_id))
                pairs.append(("employee_id", emp_id))

        res = {"new_id": 0, "affected": 0}
        sets, params = _set_clause(pairs)
        if sets:
            res = tx.command("UPDATE shop_order SET " + sets + " WHERE order_id = %s",
                             params + (order_id,))
        if "items" in data:
            clean, products = _clean_items(tx, data.get("items"))
            total = _replace_items(tx, order_id, clean, products)
            res = tx.command("UPDATE shop_order SET total_amount = %s WHERE order_id = %s",
                             (total, order_id))
            res["total_amount"] = total
        return res


def create_customer_order(data):
    """ลูกค้าสร้างออเดอร์เอง — insert shop_order + order_line ใน transaction เดียว
    (ไม่หักเงิน/ไม่ตัดสต็อก ตามข้อกำหนด)"""
    data = data or {}
    customer_id = data.get("customer_id") or data.get("user_id")
    address_token = _text(data, "address_token", "ที่อยู่จัดส่ง", required=True)
    if not customer_id:
        raise ValueError("กรุณาเลือกลูกค้า")

    with transaction() as tx:
        if not _one(tx, "SELECT customer_id FROM user_customer WHERE customer_id = %s", (customer_id,)):
            raise ValueError("ไม่พบลูกค้ารหัส " + str(customer_id))
        if not _one(tx, "SELECT address_token FROM address WHERE address_token = %s AND user_id = %s",
                    (address_token, customer_id)):
            raise ValueError("ที่อยู่ไม่ถูกต้อง หรือไม่ใช่ของลูกค้าคนนี้")

        clean, products = _clean_items(tx, data.get("items"))
        total = _sum_items(clean, products)

        res = tx.command(
            """INSERT INTO shop_order (customer_id, employee_id, total_amount, status, address_token)
               VALUES (%s, NULL, %s, 'pending', %s)""",
            (customer_id, total, address_token))
        order_id = res["new_id"]
        for pid, qty in clean:
            tx.command(
                "INSERT INTO order_line (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                (order_id, pid, qty, products[pid]["price"]))

        return {"new_id": order_id, "affected": len(clean), "total_amount": total}


def delete_order(order_id):
    with transaction() as tx:
        order = _one(tx, "SELECT order_id, customer_id FROM shop_order WHERE order_id = %s", (order_id,))
        if not order:
            raise ValueError("ไม่พบออเดอร์รหัส " + str(order_id))
        rows = tx.query("SELECT method, amount FROM payment WHERE order_id = %s", (order_id,))
        refund = round(sum(float(r["amount"] or 0) for r in rows if r["method"] == "point"), 2)
        tx.command("DELETE FROM order_line WHERE order_id = %s", (order_id,))
        tx.command("DELETE FROM payment WHERE order_id = %s", (order_id,))
        if refund:
            _wallet_change(tx, order["customer_id"], refund)
        return tx.command("DELETE FROM shop_order WHERE order_id = %s", (order_id,))


# ---------- การชำระเงิน (payment) ----------
# กติกา: จ่ายผ่าน 'point' = หักยอดเงินสะสมของลูกค้าทันทีถือว่าชำระสำเร็จ
#        จ่ายผ่าน 'cash'/'bank' = ลูกค้าแจ้งชำระ แต่ต้องรอพนักงานยืนยันก่อนถึงนับว่าชำระแล้ว
def get_order_payments(order_id):
    sql = """SELECT payment_id, order_id, method, amount, status, paid_date
             FROM payment WHERE order_id = %s ORDER BY paid_date, payment_id"""
    return run_query(sql, (order_id,))


def search_payments(filters=None):
    filters = filters or {}
    sql = """SELECT pay.payment_id, pay.order_id, pay.method, pay.amount, pay.status, pay.paid_date,
                    o.total_amount AS order_total, o.status AS order_status
             FROM payment pay
             LEFT JOIN shop_order o ON o.order_id = pay.order_id
             WHERE 1=1"""
    param = []
    if filters.get("order_id"):
        sql += " AND pay.order_id = %s"
        param.append(_to_int(filters["order_id"], "รหัสออเดอร์"))
    if filters.get("customer_id"):
        sql += " AND o.customer_id = %s"
        param.append(_to_int(filters["customer_id"], "รหัสลูกค้า"))
    if filters.get("method"):
        sql += " AND pay.method = %s"
        param.append(_choice(filters["method"], PAYMENT_METHODS, "วิธีชำระเงิน"))
    if filters.get("status"):
        sql += " AND pay.status = %s"
        param.append(_choice(filters["status"], PAYMENT_STATUSES, "สถานะการชำระเงิน"))
    if filters.get("min_amount"):
        sql += " AND pay.amount >= %s"
        param.append(_to_float(filters["min_amount"], "ยอดขั้นต่ำ"))
    if filters.get("date_from"):
        sql += " AND pay.paid_date >= %s"
        param.append(str(filters["date_from"]) + " 00:00:00")
    if filters.get("date_to"):
        sql += " AND pay.paid_date <= %s"
        param.append(str(filters["date_to"]) + " 23:59:59")
    sql += " ORDER BY pay.status ASC, pay.paid_date DESC, pay.payment_id DESC"
    return run_query(sql, param)


def get_payment(payment_id):
    rows = run_query("SELECT * FROM payment WHERE payment_id = %s", (payment_id,))
    if rows:
        return rows[0]
    return None


def _order_info(tx, order_id):
    return _one(tx, "SELECT order_id, customer_id, total_amount, status FROM shop_order WHERE order_id = %s",
                (order_id,))


def _sum_payment(tx, order_id, status, exclude_payment_id=None):
    """ยอดรวมของรายการชำระเงินที่มีสถานะตามที่ระบุ"""
    sql = "SELECT COALESCE(SUM(amount), 0) AS paid FROM payment WHERE order_id = %s AND status = %s"
    param = [order_id, status]
    if exclude_payment_id:
        sql += " AND payment_id <> %s"
        param.append(exclude_payment_id)
    row = _one(tx, sql, tuple(param))
    return round(float(row["paid"] or 0), 2) if row else 0.0


def _verified_total(tx, order_id, exclude_payment_id=None):
    """ยอดที่ชำระสำเร็จแล้ว (นับเฉพาะที่พนักงานยืนยันหรือจ่ายด้วยคะแนน)"""
    return _sum_payment(tx, order_id, "verified", exclude_payment_id)


def _pending_total(tx, order_id, exclude_payment_id=None):
    return _sum_payment(tx, order_id, "pending", exclude_payment_id)


def _claimable(tx, order_id, method, exclude_payment_id=None):
    """ยอดที่ยังจอง/จ่ายได้อีก"""
    total = float(_order_info(tx, order_id)["total_amount"])
    blocked = _verified_total(tx, order_id, exclude_payment_id)
    if method != "point":
        blocked += _pending_total(tx, order_id, exclude_payment_id)
    return round(total - blocked, 2)


def _wallet_change(tx, customer_id, delta):
    """เปลี่ยนยอดเงินสะสมของลูกค้า — delta ติดลบ = หักออก, ติดบวก = คืนเงิน"""
    if not customer_id or not delta:
        return
    if delta < 0:
        res = tx.command("UPDATE user_customer SET money = money - %s WHERE customer_id = %s AND money >= %s",
                         (-round(delta, 2), customer_id, -round(delta, 2)))
        if not res["affected"]:
            raise ValueError("ยอดเงินสะสมไม่พอ (ต้องการ %.2f บาท)\nกรุณาชำระผ่านเงินสดหรือโอนธนาคารแทน" % -delta)
    else:
        tx.command("UPDATE user_customer SET money = money + %s WHERE customer_id = %s",
                   (round(delta, 2), customer_id))


def _sync_order_paid(tx, order_id):
    """อัปเดตสถานะออเดอร์เป็น 'ชำระแล้ว' เมื่อยืนยันครบยอด และคืนเป็น 'รอชำระเงิน' เมื่อยกเลิกรายการ"""
    info = _order_info(tx, order_id) if order_id else None
    if not info:
        return
    paid = _verified_total(tx, order_id)
    if paid + 0.005 >= round(float(info["total_amount"]), 2):
        if info["status"] in ("pending", "waiting_paid"):
            tx.command("UPDATE shop_order SET status = 'paid' WHERE order_id = %s", (order_id,))
    elif info["status"] == "paid":
        tx.command("UPDATE shop_order SET status = 'waiting_paid' WHERE order_id = %s", (order_id,))


def create_payment(data):
    data = data or {}
    method = _choice(_text(data, "method", "วิธีชำระเงิน", required=True),
                     PAYMENT_METHODS, "วิธีชำระเงิน")
    if data.get("amount") in (None, ""):
        raise ValueError("กรุณากรอกยอดเงิน")
    amount = round(_to_float(data["amount"], "ยอดเงิน"), 2)
    if amount <= 0:
        raise ValueError("ยอดเงินต้องมากกว่า 0")
    # จ่ายด้วยคะแนนสะสมถือว่าสำเร็จทันที
    # ส่วนเงินสด/โอน = ลูกค้าแจ้งชำระแล้ว ต้องรอพนักงานยืนยัน
    status = "verified" if method == "point" else "pending"

    with transaction() as tx:
        order_id = data.get("order_id")
        order = None
        if order_id in (None, "", "0"):
            order_id = None
        else:
            order_id = _to_int(order_id, "รหัสออเดอร์")
            order = _order_info(tx, order_id)
            if not order:
                raise ValueError("ไม่พบออเดอร์ " + str(order_id))
            if order["status"] == "cancelled":
                raise ValueError("ออเดอร์นี้ถูกยกเลิกแล้ว ไม่สามารถชำระเงินได้")
            remain = _claimable(tx, order_id, method)
            if amount > remain + 0.005:
                raise ValueError("ชำระเกินยอดที่ต้องชำระ (คงเหลือ %.2f บาท)" % remain)
        paid_date = data.get("paid_date") or None

        cols = ["method", "amount", "status"]
        vals = [method, amount, status]
        if order_id:
            cols.append("order_id")
            vals.append(order_id)
        if paid_date:
            cols.append("paid_date")
            vals.append(paid_date)
        sql = "INSERT INTO payment (" + ", ".join("`" + c + "`" for c in cols) + ") VALUES (" + \
              ", ".join(["%s"] * len(cols)) + ")"
        res = tx.command(sql, tuple(vals))

        if order:
            if method == "point":
                _wallet_change(tx, order["customer_id"], -amount)
            _sync_order_paid(tx, order_id)
        return res


def verify_payment(payment_id):
    """พนักงานยืนยันว่าได้รับเงินสด/โอนจริง"""
    with transaction() as tx:
        row = _one(tx, "SELECT payment_id, order_id, method, amount, status FROM payment WHERE payment_id = %s",
                   (payment_id,))
        if not row:
            raise ValueError("ไม่พบรายการชำระเงินรหัส " + str(payment_id))
        if row["status"] == "verified":
            raise ValueError("รายการชำระเงินนี้ผ่านการยืนยันแล้ว")
        if row["method"] == "point":
            raise ValueError("รายการจ่ายด้วยคะแนนสะสมถือว่าสำเร็จอยู่แล้ว")
        if not row["order_id"]:
            raise ValueError("รายการนี้ไม่ได้ผูกกับออเดอร์ กรุณาแก้ไขออเดอร์ก่อนยืนยัน")
        order = _order_info(tx, row["order_id"])
        if not order:
            raise ValueError("ไม่พบออเดอร์ " + str(row["order_id"]))
        if order["status"] == "cancelled":
            raise ValueError("ออเดอร์นี้ถูกยกเลิกแล้ว")
        remain = _claimable(tx, row["order_id"], row["method"], payment_id)
        if float(row["amount"]) > remain + 0.005:
            raise ValueError("ยอดนี้เกินกว่าที่ออเดอร์รับได้ (คงเหลือ %.2f บาท)" % remain)

        res = tx.command("UPDATE payment SET status = 'verified' WHERE payment_id = %s", (payment_id,))
        _sync_order_paid(tx, row["order_id"])
        return res


def update_payment(payment_id, data):
    data = data or {}

    with transaction() as tx:
        old = _one(tx, "SELECT payment_id, order_id, method, amount, status FROM payment WHERE payment_id = %s",
                   (payment_id,))
        if not old:
            raise ValueError("ไม่พบรายการชำระเงินรหัส " + str(payment_id))
        if old["status"] == "verified" and old["method"] != "point":
            raise ValueError("รายการนี้ผ่านการยืนยันของพนักงานแล้ว หากต้องการแก้ไขกรุณาติดต่อพนักงาน")

        old_amount = round(float(old["amount"] or 0), 2)
        old_order_id = old["order_id"]
        old_method = old["method"]

        method = old_method
        if "method" in data and data["method"]:
            method = _choice(data["method"], PAYMENT_METHODS, "วิธีชำระเงิน")
        new_amount = old_amount
        if "amount" in data and data["amount"] not in (None, ""):
            new_amount = round(_to_float(data["amount"], "ยอดเงิน"), 2)
            if new_amount <= 0:
                raise ValueError("ยอดเงินต้องมากกว่า 0")
        new_order_id = old_order_id
        if "order_id" in data:
            if data["order_id"] in (None, "", "0"):
                new_order_id = None
            else:
                new_order_id = _to_int(data["order_id"], "รหัสออเดอร์")
        new_status = old["status"]
        if method != old_method:
            new_status = "verified" if method == "point" else "pending"

        # คืนยอดเดิมก่อน (เฉพาะที่จ่ายด้วยคะแนนสะสม) แล้วค่อยหักค่าใหม่
        if old_order_id and old_method == "point":
            old_info = _order_info(tx, old_order_id)
            if old_info:
                _wallet_change(tx, old_info["customer_id"], old_amount)
        new_info = None
        if new_order_id:
            new_info = _order_info(tx, new_order_id)
            if not new_info:
                raise ValueError("ไม่พบออเดอร์ " + str(new_order_id))
            if new_info["status"] == "cancelled":
                raise ValueError("ออเดอร์นี้ถูกยกเลิกแล้ว ไม่สามารถชำระเงินได้")
            remain = _claimable(tx, new_order_id, method, payment_id)
            if new_amount > remain + 0.005:
                raise ValueError("ชำระเกินยอดที่ต้องชำระ (คงเหลือ %.2f บาท)" % remain)

        pairs = []
        if method != old_method:
            pairs.append(("method", method))
        if new_amount != old_amount:
            pairs.append(("amount", new_amount))
        if new_status != old["status"]:
            pairs.append(("status", new_status))
        if new_order_id != old_order_id:
            pairs.append(("order_id", new_order_id))
        if "paid_date" in data:
            pairs.append(("paid_date", data["paid_date"] or None))

        sets, params = _set_clause(pairs)
        res = {"new_id": 0, "affected": 0}
        if sets:
            res = tx.command("UPDATE payment SET " + sets + " WHERE payment_id = %s", params + (payment_id,))

        if new_info and method == "point":
            _wallet_change(tx, new_info["customer_id"], -new_amount)
        if new_order_id:
            _sync_order_paid(tx, new_order_id)
        if old_order_id and old_order_id != new_order_id:
            _sync_order_paid(tx, old_order_id)
        return res


def delete_payment(payment_id):
    with transaction() as tx:
        row = _one(tx, "SELECT payment_id, order_id, method, amount, status FROM payment WHERE payment_id = %s",
                   (payment_id,))
        if not row:
            raise ValueError("ไม่พบรายการชำระเงินรหัส " + str(payment_id))
        if row["status"] == "verified" and row["method"] != "point":
            raise ValueError("รายการนี้ผ่านการยืนยันของพนักงานแล้ว หากต้องการยกเลิกกรุณาติดต่อพนักงาน")

        res = tx.command("DELETE FROM payment WHERE payment_id = %s", (payment_id,))
        if row["order_id"]:
            info = _order_info(tx, row["order_id"])
            if info and row["method"] == "point":
                _wallet_change(tx, info["customer_id"], round(float(row["amount"] or 0), 2))
            _sync_order_paid(tx, row["order_id"])
        return res



# ---------- รีวิว (review) ----------
def search_reviews(filters=None):
    filters = filters or {}
    sql = """SELECT r.review_id, r.user_id, u.name AS user_name, r.product_id,
                    p.name AS product_name, r.rating, r.comment, r.review_date
             FROM review r
             INNER JOIN users u ON r.user_id = u.user_id
             INNER JOIN product p ON r.product_id = p.product_id
             WHERE 1=1"""
    param = []
    if filters.get("user_id"):
        sql += " AND r.user_id = %s"
        param.append(_to_int(filters["user_id"], "รหัสผู้ใช้"))
    if filters.get("product_id"):
        sql += " AND r.product_id = %s"
        param.append(_to_int(filters["product_id"], "รหัสสินค้า"))
    if filters.get("min_rating"):
        sql += " AND r.rating >= %s"
        param.append(_to_int(filters["min_rating"], "คะแนนขั้นต่ำ"))
    if filters.get("max_rating"):
        sql += " AND r.rating <= %s"
        param.append(_to_int(filters["max_rating"], "คะแนนสูงสุด"))
    if filters.get("q"):
        sql += " AND r.comment LIKE %s"
        param.append("%" + filters["q"] + "%")
    sql += " ORDER BY r.review_id DESC"
    return run_query(sql, param)


def get_review(review_id):
    sql = """SELECT r.*, u.name AS user_name, p.name AS product_name
             FROM review r
             INNER JOIN users u ON r.user_id = u.user_id
             INNER JOIN product p ON r.product_id = p.product_id
             WHERE r.review_id = %s"""
    rows = run_query(sql, (review_id,))
    if rows:
        return rows[0]
    return None


def get_product_reviews(product_id):
    sql = """SELECT r.review_id, r.rating, r.comment, r.review_date, u.name AS user_name
             FROM review r
             INNER JOIN users u ON r.user_id = u.user_id
             WHERE r.product_id = %s
             ORDER BY r.review_id DESC"""
    return run_query(sql, (product_id,))


def _rating(data, required=False):
    if "rating" not in data:
        if required:
            raise ValueError("กรุณาให้คะแนน 1-5")
        return None
    rating = _to_int(data["rating"], "คะแนน")
    if not 1 <= rating <= 5:
        raise ValueError("คะแนนต้องอยู่ระหว่าง 1-5")
    return rating


def create_review(data):
    data = data or {}
    user_id = _to_int(data.get("user_id"), "รหัสผู้ใช้")
    product_id = _to_int(data.get("product_id"), "รหัสสินค้า")
    rating = _rating(data, required=True)
    comment = _text(data, "comment", "ความคิดเห็น") or None

    with transaction() as tx:
        if not _one(tx, "SELECT customer_id FROM user_customer WHERE customer_id = %s", (user_id,)):
            raise ValueError("รีวิวได้เฉพาะลูกค้าเท่านั้น")
        if not _one(tx, "SELECT product_id FROM product WHERE product_id = %s", (product_id,)):
            raise ValueError("ไม่พบสินค้ารหัส " + str(product_id))
        if _one(tx, "SELECT review_id FROM review WHERE user_id = %s AND product_id = %s",
                (user_id, product_id)):
            raise ValueError("คุณรีวิวสินค้านี้แล้ว")
        return tx.command(
            "INSERT INTO review (user_id, product_id, rating, comment) VALUES (%s, %s, %s, %s)",
            (user_id, product_id, rating, comment))


def update_review(review_id, data):
    data = data or {}
    pairs = []
    if "rating" in data:
        pairs.append(("rating", _rating(data, required=True)))
    if "comment" in data:
        pairs.append(("comment", _text(data, "comment", "ความคิดเห็น") or None))
    sets, params = _set_clause(pairs)
    if not sets:
        return {"new_id": 0, "affected": 0}
    with transaction() as tx:
        if not _one(tx, "SELECT review_id FROM review WHERE review_id = %s", (review_id,)):
            raise ValueError("ไม่พบรีวิวรหัส " + str(review_id))
        return tx.command("UPDATE review SET " + sets + " WHERE review_id = %s",
                          params + (review_id,))


def delete_review(review_id):
    with transaction() as tx:
        if not _one(tx, "SELECT review_id FROM review WHERE review_id = %s", (review_id,)):
            raise ValueError("ไม่พบรีวิวรหัส " + str(review_id))
        return tx.command("DELETE FROM review WHERE review_id = %s", (review_id,))


# ============================================================
#  REPORT (รายงาน — ใช้ JOIN + GROUP BY + subquery)
# ============================================================
def report_summary():
    """ตัวเลขสรุปบนการ์ด dashboard"""
    users = run_query("SELECT COUNT(*) AS total FROM users WHERE role = 'customer'")[0]["total"]
    products = run_query("SELECT COUNT(*) AS total FROM product")[0]["total"]
    orders = run_query("SELECT COUNT(*) AS total FROM shop_order")[0]["total"]
    paid_orders = run_query(
        "SELECT COUNT(*) AS total FROM shop_order WHERE status IN ('paid','delivered','succeed','shipped')"
    )[0]["total"]
    cancelled = run_query("SELECT COUNT(*) AS total FROM shop_order WHERE status = 'cancelled'")[0]["total"]
    sales_data = run_query(
        "SELECT SUM(total_amount) AS total FROM shop_order WHERE status IN ('paid','delivered','succeed','shipped')"
    )[0]["total"]
    total_sales = float(sales_data) if sales_data else 0.0
    avg_data = run_query(
        "SELECT AVG(total_amount) AS avg_amount FROM shop_order WHERE status IN ('paid','delivered','succeed','shipped')"
    )[0]["avg_amount"]
    reviews = run_query("SELECT COUNT(*) AS total FROM review")[0]["total"]
    low_stock = run_query("SELECT COUNT(*) AS total FROM product WHERE total <= 10")[0]["total"]

    return {
        "customers": users,
        "products": products,
        "orders": orders,
        "paid_orders": paid_orders,
        "cancelled_orders": cancelled,
        "reviews": reviews,
        "low_stock": low_stock,
        "avg_order_value": round(float(avg_data), 2) if avg_data else 0.0,
        "total_sales": total_sales
    }


def report_best_selling(limit=5):
    """📈 สินค้าขายดี (Best Sellers) — นับเฉพาะออเดอร์ที่ยังไม่ถูกยกเลิก"""
    sql = """SELECT p.product_id, p.name,
                    SUM(ol.quantity) AS total_sold,
                    SUM(ol.quantity * ol.unit_price) AS total_revenue
             FROM order_line ol
             INNER JOIN product p ON ol.product_id = p.product_id
             INNER JOIN shop_order o ON o.order_id = ol.order_id
             WHERE o.status <> 'cancelled'
             GROUP BY p.product_id, p.name
             ORDER BY total_sold DESC
             LIMIT %s"""
    return run_query(sql, (int(limit),))


def report_customers_above_avg():
    """🏅 ลูกค้าที่ซื้อมากกว่าค่าเฉลี่ย (Above Average)"""
    sql = """SELECT u.user_id, u.name, u.email,
                    SUM(ol.quantity * ol.unit_price) AS total_spent
             FROM users u
             INNER JOIN shop_order o ON u.user_id = o.customer_id
             INNER JOIN order_line ol ON o.order_id = ol.order_id
             WHERE o.status <> 'cancelled'
             GROUP BY u.user_id, u.name, u.email
             HAVING total_spent > (
                 SELECT AVG(sub.total) FROM (
                     SELECT SUM(ol2.quantity * ol2.unit_price) AS total
                     FROM shop_order o2
                     INNER JOIN order_line ol2 ON o2.order_id = ol2.order_id
                     WHERE o2.status <> 'cancelled'
                     GROUP BY o2.customer_id
                 ) AS sub
             )
             ORDER BY total_spent DESC"""
    return run_query(sql)


def report_high_rated(min_rating=4):
    """⭐ สินค้าคะแนนรีวิวเฉลี่ย ≥ 4 (HAVING)"""
    sql = """SELECT p.product_id, p.name,
                    ROUND(AVG(r.rating), 2) AS avg_rating,
                    COUNT(r.review_id) AS review_count
             FROM review r
             INNER JOIN product p ON r.product_id = p.product_id
             GROUP BY p.product_id, p.name
             HAVING AVG(r.rating) >= %s
             ORDER BY avg_rating DESC"""
    return run_query(sql, (int(min_rating),))


def report_sales_by_month(months=6):
    """ยอดขายรายเดือน (ใช้ GROUP BY + MONTH/YEAR) — ไม่นับออเดอร์ที่ยกเลิก"""
    sql = """SELECT DATE_FORMAT(o.order_date, '%%Y-%%m') AS month,
                    COUNT(o.order_id) AS order_count,
                    SUM(o.total_amount) AS total_sales
             FROM shop_order o
             WHERE o.status <> 'cancelled'
               AND o.order_date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
             GROUP BY month
             ORDER BY month DESC"""
    return run_query(sql, (int(months),))