# ============================================================
#  db.py — ชั้นติดต่อฐานข้อมูล  ★★★ นิสิตเขียน SQL ในไฟล์นี้ ★★★
#  มองหาคำว่า  # TODO  ทุกฟังก์ชัน — ใช้ %s เป็น placeholder เสมอ (กัน SQL injection)
# ============================================================
import mysql.connector
import config
from datetime import date


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


def blank_to_none(value):
    """ช่องที่ไม่ได้กรอกในฟอร์มจะส่งมาเป็น "" — แปลงเป็น None (= NULL ใน SQL)
    ใช้กับคอลัมน์ที่ว่างได้ เช่น return_date, paid_date  เพราะ MySQL ไม่รับ '' เป็น DATE"""
    return None if value in ("", None) else value


def _todo(name):
    raise NotImplementedError(f"TODO: ยังไม่ได้เขียนฟังก์ชัน {name} ใน db.py")





# ---------- สินค้า (product) ----------
# stock = จำนวน product_detail ที่ยังไม่ถูกผูกกับ order_line
# TODO: เพิ่ม p.detail ใน SELECT ให้ครบทุกคอลัมน์ของตาราง product
#       (ฟอร์มแก้ไขใน /admin จะอ่านค่าเดิมได้)
_STOCK_SQL = ("(SELECT COUNT(*) FROM product_detail pd "
              "WHERE pd.product_id = p.product_id AND pd.`use` = FALSE   and(pd.order_line_id IS NULL or pd.book_end_at <= NOW()))")

_PRODUCT_SELECT = ("SELECT p.product_id, p.name, p.category, p.price, p.discount, "
                   + _STOCK_SQL + " AS stock FROM product p")


def search_products(filters):
    """ค้นหา สินค้า ตามเงื่อนไข (name, category)"""
    f = filters or {}
    sql = _PRODUCT_SELECT + " WHERE 1=1"
    params = []
    if f.get("name"):
        sql += " AND p.name LIKE %s"
        params.append(f"%{f['name']}%")
    if f.get("category"):
        sql += " AND p.category = %s"
        params.append(f["category"])
    sql += "  ORDER BY p.product_id"
    return run_query(sql, params)


def get_product(product_id):
    """ดึง สินค้า 1 รายการตาม product_id (ใช้ตอนเปิดฟอร์มแก้ไข)"""
    rows = run_query(_PRODUCT_SELECT + " WHERE p.product_id = %s", (int(product_id),))
    if not rows:
        raise ValueError("ไม่พบสินค้า")
    return rows[0]






def delete_product(product_id):
    """ลบ สินค้า ตาม product_id"""
    # TODO: DELETE FROM product WHERE product_id=%s
    _todo("delete_product")

# ---------- ออเดอร์ (shop_order) ของผู้ใช้ ----------
def search_orders_user(filters, user_id):
    """ออเดอร์ของผู้ใช้คนนี้ (JOIN order_line เพื่อนับชิ้น + คิดยอดรวม)"""
    f = filters or {}
    sql = """SELECT o.order_id, o.created_at AS order_date, o.status,
                    COUNT(ol.order_line_id) AS items,
                    IFNULL(SUM(ol.quantity * ol.unit_price), 0) AS total,
                    (SELECT IFNULL(SUM(p.amount_pay), 0) FROM payment p
                      WHERE p.order_id = o.order_id) AS paid
             FROM shop_order o
             LEFT JOIN order_line ol ON ol.order_id = o.order_id
             WHERE o.user_id = %s"""
    params = [int(user_id)]
    sql += " AND o.status <> 'cart'"
    if f.get("status"):
        sql += " AND o.status = %s"
        params.append(f["status"])
    sql += " GROUP BY o.order_id, o.created_at, o.status ORDER BY o.order_id DESC"
    return run_query(sql, params)


def get_order(order_id):
    order = run_query(
        """SELECT ol.order_line_id, ol.product_id, p.name,
                  ol.quantity, ol.unit_price,
                  (ol.quantity * ol.unit_price) AS line_total,
                  pd.username, pd.password
           FROM order_line ol
           JOIN product p ON p.product_id = ol.product_id
           LEFT JOIN product_detail pd ON pd.order_line_id = ol.order_line_id
           WHERE ol.order_id = %s
           ORDER BY ol.order_line_id""",
        (int(order_id),))
    return order








def singin(data):
    d = data or {}
    rows = run_query(
        "SELECT user_id, name, email, role FROM users "
        "WHERE email = %s AND password = %s",
        ((d.get("email") or "").strip(), d.get("password") or ""))
    if not rows:
        raise ValueError("อีเมลหรือรหัสผ่านไม่ถูกต้อง")
    return rows[0]


def signup(data):
    d = data or {}
    name = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip()
    password = d.get("password") or ""
    if not name or not email or not password:
        raise ValueError("กรุณากรอกชื่อ อีเมล และรหัสผ่าน")
    if run_query("SELECT 1 FROM users WHERE email = %s", (email,)):
        raise ValueError("อีเมลนี้ถูกใช้แล้ว")
    out = run_command(
        "INSERT INTO users (name, email, password, role) "
        "VALUES (%s, %s, %s, 'user')",
        (name, email, password))
    return {"user_id": out["new_id"], "name": name, "email": email, "role": "user"}


# home
def list_categories():
    return run_query(
        "SELECT DISTINCT category FROM product "
        "WHERE category IS NOT NULL AND category <> '' ORDER BY category")

  


def Check_myorder(user_id): 
    rows = run_query(
        "SELECT order_id FROM shop_order WHERE user_id = %s AND status = 'cart'", 
        [user_id]
    )
    if rows and len(rows) > 0:
        return rows[0]['order_id']
    return None

def add_to_Order(data, user_id):
    d = data or {}
    pid = int(d.get("product_id"))
    qty = int(d.get("qty", 1))
    print(pid)
    print(qty)
    order_id = Check_myorder(user_id)

    
    if not order_id:
        print("not order")
        #-- ยังไม่มมี order สร้างก่อน
        run_command("INSERT INTO shop_order (user_id , status ) VALUES(%s , 'cart')", [user_id,]) 
        order_id = Check_myorder(user_id)
    
    sql = """
    INSERT INTO order_line (order_id, product_id, unit_price, quantity)
    SELECT %s,product_id , price * (100 - IFNULL(discount,0)) / 100, %s
    FROM product
    WHERE product_id = %s
    """
    
    run_command(sql, [order_id, qty, pid])

    return order_id


def get_cart(user_id):
    """อ่านตะกร้าจาก DB คืน {items, count, total} — ตรงกับ CART_COLS ใน home.js"""
    order_id = Check_myorder(user_id)
    if not order_id:
        return {"items": [], "count": 0, "total": 0}
    items = run_query(
        """SELECT p.product_id,
                  p.name,
                  ol.unit_price AS price,
                  SUM(ol.quantity) AS qty,
                  SUM(ol.unit_price * ol.quantity) AS line_total
           FROM order_line ol
           JOIN product p ON p.product_id = ol.product_id 
           WHERE ol.order_id = %s
           GROUP BY p.product_id, p.name, ol.unit_price
           ORDER BY p.product_id""",
        (order_id,))
    return items



def remove_cart_item(user_id, product_id):
    return run_command(
        """
        DELETE ol
        FROM order_line AS ol
        JOIN shop_order AS so ON ol.order_id = so.order_id
        WHERE so.user_id = %s
          AND so.status = 'cart'
          AND ol.product_id = %s
        """,
        (user_id, product_id)
    )
    


def check_order_code(user_id, order_id, code_name):
    """เช็คโค้ดส่วนลดของออเดอร์ — คืน {code_id, code_name, discount_method, discount, total, final}
    - โค้ดต้องมีในตาราง code, status = TRUE, และ end_at ยังไม่หมดอายุ (หรือเป็น NULL)
    - คำนวณ: money → final = max(total - discount, 0)
             percent → final = total * (100 - discount) / 100
    - โค้ดผิด / หมดอายุ / ปิดใช้ → raise ValueError("ข้อความอธิบาย")
    """

    # ยอดออเดอร์ + เช็คเป็นเจ้าของ + เช็คสถานะ
    t = run_query(
        """SELECT IFNULL(SUM(ol.quantity * ol.unit_price), 0) AS total,
                  o.user_id, o.status
           FROM shop_order o
           LEFT JOIN order_line ol ON ol.order_id = o.order_id
           WHERE o.order_id = %s
           GROUP BY o.user_id, o.status""",
        [order_id])
    if not t:
        raise ValueError("ไม่พบออเดอร์")
    if int(t[0]["user_id"]) != int(user_id):
        raise ValueError("ไม่ใช่ออเดอร์ของคุณ")
    if t[0]["status"] != "waitpay":
        raise ValueError("ออเดอร์ไม่ได้อยู่ในสถานะรอชำระเงิน")
    total = float(t[0]["total"])

    # ดึงโค้ดที่ยังใช้ได้
    rows = run_query("""
        SELECT c.code_id, c.code_name, c.discount_method, c.discount,
               (SELECT 1 FROM code_line cl
                 WHERE cl.user_id = %s AND cl.code_id = c.code_id) AS used
        FROM code c
        WHERE c.code_name = %s AND c.status = TRUE
          AND (c.end_at IS NULL OR c.end_at > NOW())
        """, [user_id, code_name])
    if not rows:
        raise ValueError("โค้ดไม่ถูกต้อง หมดอายุ หรือถูกปิดใช้งาน")
    c = rows[0]
    if c["used"] == 1:
        raise ValueError("โค้ดนี้ถูกใช้งานแล้ว")

    # คำนวณส่วนลด
    if c["discount_method"] == "percent":
        final = round(total * (100 - float(c["discount"])) / 100, 2)
    else:
        final = max(total - float(c["discount"]), 0)
    final = max(final, 0)

    return {"code_id": c["code_id"], "code_name": c["code_name"],
            "discount_method": c["discount_method"],
            "discount": float(c["discount"]), "total": total, "final": final}


def confirm_cart(order_id):

    sql = """
        SELECT order_line_id, product_id, SUM(quantity) AS quantity 
        FROM order_line 
        WHERE order_id = %s 
        GROUP BY order_line_id, product_id
    """

    rows = run_query(sql, [order_id])

    print(rows)
    for x in rows:
        order_line_id = x['order_line_id']  
        product_id = x['product_id']
        quantity = x['quantity']


        update_sql = """
            UPDATE product_detail pd
            JOIN (
                SELECT product_detail_id,
                    ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY product_detail_id ASC) AS row_num
                FROM product_detail
                WHERE (order_line_id IS NULL or book_end_at < NOW() ) AND `use` = FALSE  AND  product_id = %s 
            ) stock ON pd.product_detail_id = stock.product_detail_id
            SET pd.order_line_id = %s ,
            pd.book_end_at = NOW() + INTERVAL 5 MINUTE
            WHERE stock.row_num <= %s
        """
        run_command(update_sql, [product_id, order_line_id, quantity])
      
    return run_command("UPDATE shop_order SET status = 'waitpay' WHERE order_id    = %s AND  status = 'cart' ", [order_id,])



def pay_order(user_id, order_id, code_name=None):
    uid = int(user_id)

    o = run_query(
        """SELECT user_id, status, (end_at IS NOT NULL AND end_at <= NOW()) AS expired
           FROM shop_order WHERE order_id = %s""",
        (order_id,))
    if not o:
        raise ValueError("ไม่พบออเดอร์")
    if int(o[0]["user_id"]) != uid:
        raise ValueError("ไม่มีสิทธิ์ชำระเงินออเดอร์นี้")
    if o[0]["status"] != "waitpay":
        raise ValueError("ออเดอร์นี้ไม่ได้อยู่ในสถานะรอชำระเงิน")
    if o[0]["expired"]:
        raise ValueError("ออเดอร์หมดอายุแล้ว")

    total_rows = run_query(
        "SELECT IFNULL(SUM(quantity * unit_price), 0) AS total "
        "FROM order_line WHERE order_id = %s",
        (order_id,))
    total = float(total_rows[0]["total"])
    if total < 0:
        raise ValueError("ออเดอร์ไม่มียอดชำระ")
    amount = total
    code_id = None
    if code_name:
        info = check_order_code(uid, order_id, code_name)
        amount = float(info["final"])
        code_id = info.get("code_id")
    run_command(
        "INSERT INTO payment (order_id, amount_pay, code_id) VALUES (%s, %s, %s)",
        (order_id, amount, code_id))
    if code_id:
        run_command(
            "INSERT INTO code_line (code_id, user_id, order_id) VALUES (%s, %s, %s)",
            (code_id, uid, order_id))
    run_command(
        "UPDATE product_detail pd "
        "JOIN order_line ol ON ol.order_line_id = pd.order_line_id "
        "SET pd.`use` = TRUE "
        "WHERE ol.order_id = %s AND pd.`use` = FALSE",
        (order_id,))
    run_command(
        "UPDATE shop_order SET status = 'success' WHERE order_id = %s",
        (order_id,))
    return {"order_id": order_id, "amount_pay": amount, "code_id": code_id}


def cancel_order(user_id, order_id):
    """ยกเลิกออเดอร์ — ได้เฉพาะสถานะ waitpay (รอยชำระเงิน)"""

    out = run_command(
        "UPDATE shop_order SET status = 'cancel' WHERE order_id = %s AND status = 'waitpay' and user_id = %s",
        (order_id,user_id))
    if not out["affected"]:
        raise ValueError("ยกเลิกไม่สำเร็จ กรุณาลองใหม่")
    return {"order_id": order_id, "status": "cancel"}



def search_customers(filters):
    """ค้นหา ลูกค้า ตามเงื่อนไข (name, email, tier)
    คำใบ้: เริ่มจาก sql = "SELECT * FROM customer WHERE 1=1"
    แล้วต่อเงื่อนไขเฉพาะ filter ที่มีค่า (ข้อความใช้ LIKE %s, อื่น ๆ ใช้ = %s)"""
    # TODO: เขียน SQL ค้นหาแบบยืดหยุ่นตาม filters (ใช้ %s เสมอ)
    sql = """
        SELECT  user_id
                ,name
                ,email
                ,role
        FROM    users
        WHERE   1 = 1
    """
    params = []
    if filters.get("name"):
        sql += " AND name LIKE %s"
        params.append("%" + filters["name"] + "%")
    if filters.get("email"):
        sql += " AND email LIKE %s"
        params.append("%" + filters["email"] + "%")
    if filters.get("role"):
        sql += " AND role = %s"
        params.append(filters["role"])
    return run_query(sql, params)

def get_customer(user_id):
    """ดึง ลูกค้า 1 รายการตาม cust_id (ใช้ตอนเปิดฟอร์มแก้ไข)"""
    # TODO: SELECT * FROM customer WHERE cust_id = %s แล้วคืนแถวเดียว
    rows = run_query("""
                        SELECT user_id, name, email, role
                        FROM users
                        WHERE user_id = %s
                    """, (user_id,))
    return rows[0] if rows else None

def create_customer(data):
    """เพิ่ม user ใหม่จาก /admin — data: name, email, role (+ password ถ้าไม่ส่งใช้ '1234')"""
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    role = data.get("role") if data.get("role") in ("user", "admin") else "user"
    password = data.get("password") or "1234"
    if not name or not email:
        raise ValueError("กรุณากรอกชื่อ และอีเมล")
    if run_query("SELECT 1 FROM users WHERE email = %s", (email,)):
        raise ValueError("อีเมลนี้ถูกใช้แล้ว")
    return run_command(
        "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
        (name, email, password, role)
    )


def update_customer(cust_id, data):
    """แก้ไข user ตาม user_id — data: name, email, role"""
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    role = data.get("role") if data.get("role") in ("user", "admin") else "user"
    if not name or not email:
        raise ValueError("กรุณากรอกชื่อ และอีเมล")
    if run_query("SELECT 1 FROM users WHERE email = %s AND user_id <> %s", (email, cust_id)):
        raise ValueError("อีเมลนี้ถูกใช้แล้ว")
    return run_command(
        """
        UPDATE users
        SET name = %s,
            email = %s,
            role = %s
        WHERE user_id = %s
        """,
        (name, email, role, cust_id)
   )


def delete_customer(cust_id):
    """ลบ ลูกค้า ตาม cust_id"""
    # TODO: DELETE FROM customer WHERE cust_id=%s
    _todo("delete_customer")

# ---------- สินค้า (product) ----------



def create_product(data):
    """เพิ่ม สินค้า ใหม่ — data: name, detail, category, price, stock (form app.js)
    + discount ถ้าส่งมา
    stock = จำนวน product_detail (บัญชีสินค้า) ที่สร้างให้ทันที"""
    # TODO: INSERT INTO product (name, detail, category, price, discount) VALUES (...)
    out = run_command(
        """INSERT INTO product (name, detail, category, price, discount)
           VALUES (%s, %s, %s, %s, %s)""",
        (data["name"], data.get("detail") or "", data.get("category") or "",
         data.get("price", 0), blank_to_none(data.get("discount")))
    )
    pid = out["new_id"]
    try:
        n = int(data.get("stock") or 0)
    except (TypeError, ValueError):
        n = 0
    for i in range(1, max(n, 0) + 1):
        run_command(
            "INSERT INTO product_detail (product_id, username, password) VALUES (%s, %s, %s)",
            (pid, f"acc_{pid}_{i:02d}", f"pass_{pid}_{i:02d}")
        )
    return out


def update_product(product_id, data):
    """แก้ไข สินค้า ตาม product_id"""
    # TODO: ขยายให้ UPDATE name, detail, category, price, discount
    #       WHERE product_id = %s   (ตอนนี้แก้ได้แค่ name)
    return run_command(
       """  
        update	product
        set 	name = %s
        where 	product_id = %s
        """,
        (data["name"] , product_id)
   )


# ---------- สต็อก (product_detail) ของสินค้า — /admin จัดการ ----------
def get_product_stock(product_id):
    """ดึงรายการบัญชีสต็อก (product_detail) ของสินค้านี้
    คืน list ของ {product_detail_id, username, password, status}
    status = 'ว่าง' (order_line_id IS NULL) / 'จอง' (มี order_line_id, use=FALSE, book_end_at ยังไม่หมด) / 'ขายแล้ว' (use=TRUE)"""
    
    sql = """
        SELECT 
            product_detail_id, 
            username, 
            password,
            `use`,
            CASE 
                WHEN `use` = TRUE THEN 'ขายแล้ว'
                WHEN order_line_id IS NOT NULL AND `use` = FALSE AND book_end_at > NOW() THEN 'จอง'
                WHEN order_line_id IS NULL THEN 'ว่าง'
                ELSE 'ว่าง'
            END AS status
        FROM product_detail 
        WHERE product_id = %s
    """
    return run_query(sql, [product_id])


def add_product_stock(product_id, qty, username=None, password=None):
    """เพิ่มบัญชีสต็อกใหม่ — ถ้า username/password เป็น None → สร้างอัตโนมัติ qty แถว
    (acc_{pid}_{n} / pass_{pid}_{n} ต่อจากเลขล่าสุด)  ถ้าส่ง username มา → สร้าง 1 แถวด้วยค่านั้น"""
    product_id = int(product_id)
    if username is not None:
        username = str(username).strip()
        password = str(password or "").strip()
        if not username or not password:
            raise ValueError("กรุณากรอก username และ password ให้ครบ")
        return run_command(
            "INSERT INTO product_detail (product_id, username, password) VALUES (%s, %s, %s)",
            (product_id, username, password))

    try:
        qty = int(qty)
    except (TypeError, ValueError):
        raise ValueError("จำนวนสต็อกไม่ถูกต้อง")
    if qty <= 0:
        raise ValueError("จำนวนสต็อกต้องมากกว่า 0")

    # ต่อเลขบัญชีจากรายการเดิม เพื่อไม่ให้ username ที่สร้างอัตโนมัติซ้ำ
    prefix = f"acc_{product_id}_"
    existing = run_query(
        "SELECT username FROM product_detail WHERE product_id = %s AND username LIKE %s",
        (product_id, prefix + "%"))
    next_number = 1
    for row in existing:
        value = row.get("username") or ""
        suffix = value[len(prefix):] if value.startswith(prefix) else ""
        if suffix.isdigit():
            next_number = max(next_number, int(suffix) + 1)

    conn = get_connection()
    cur = conn.cursor()
    try:
        for number in range(next_number, next_number + qty):
            cur.execute(
                "INSERT INTO product_detail (product_id, username, password) VALUES (%s, %s, %s)",
                (product_id, f"{prefix}{number:02d}", f"pass_{product_id}_{number:02d}"))
        conn.commit()
        return {"new_id": cur.lastrowid, "affected": qty}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_product_detail(pd_id, username, password, use):
    """แก้ username/password/use ของบัญชีสต็อก — ได้เฉพาะบัญชีว่าง (order_line_id IS NULL)
    use = 0 (ยังไม่ออกของ) / 1 (ออกของแล้ว)"""
    result = run_command(
        "UPDATE product_detail SET username = %s, password = %s, `use` = %s "
        "WHERE product_detail_id = %s AND order_line_id IS NULL AND `use` = FALSE",
        (username, password, int(use), pd_id))
    if result["affected"] == 0:
        raise ValueError("แก้ไขไม่สำเร็จ (บัญชีถูกจองหรือขายไปแล้ว)")
    return result


def delete_product_detail(pd_id):
    """ลบบัญชีสต็อก — ได้เฉพาะบัญชีว่าง (order_line_id IS NULL AND use = FALSE)"""
    result = run_command(
        "DELETE FROM product_detail WHERE product_detail_id = %s "
        "AND order_line_id IS NULL AND `use` = FALSE",
        (pd_id,))
    if result["affected"] == 0:
        raise ValueError("ลบไม่ได้ (บัญชีถูกจองหรือขายไปแล้ว)")
    return result


# ---------- โค้ดส่วนลด (code) — /admin จัดการ ----------
def search_codes(filters):
    """ค้นหาโค้ดส่วนลด — filters: code_name (LIKE), discount_method, status (''=ทั้งหมด, '1'=เปิด, '0'=ปิด)
    คืน list ของ {code_id, code_name, discount, discount_method, max_uses, status, end_at}"""
    # TODO: SELECT code_id, code_name, discount, discount_method, max_uses, status, end_at
    #       FROM code
    #       + filters["code_name"]     → AND code_name LIKE %s ('%...%')
    #       + filters["discount_method"] → AND discount_method = %s
    #       + filters["status"] ('1'/'0') → AND status = %s (แปลงเป็น boolean)
    #       ORDER BY code_id DESC
    sql = """
        select 	code_id
		        ,code_name 
		        ,discount 
		        ,discount_method 
		        ,max_uses 
		        ,status
		        ,end_at
        from 	code 
        WHERE   1 = 1
        ORDER BY code_id DESC
    """
    params = []
    if filters.get("code_name"):
        sql += " AND code_name LIKE %s"
        params.append("%" + filters["code_name"] + "%")
    if filters.get("discount_method"):
        sql += " AND discount_method = %s"
        params.append("%" + filters["discount_method"] + "%")
    if filters.get("status"):
        sql += " AND status = %s"
        params.append(filters["status"])
    return run_query(sql, params)

def get_code(code_id):
    """ดึงโค้ดเดียว — ไม่พบ → raise ValueError("ไม่พบโค้ดนี้")"""
    # TODO: SELECT code_id, code_name, discount, discount_method, max_uses, status, end_at
    #       FROM code WHERE code_id = %s
    rows = run_query("""
                        SELECT code_id , code_name , discount , discount_method , max_uses , status , end_at
                        FROM code
                        WHERE code_id = %s
                    """, (code_id,))
    return rows[0] if rows else None


def create_code(data):
    """เพิ่มโค้ดใหม่ — data: code_name, discount, discount_method, max_uses, status, end_at
    status ส่งเป็น "1"/"0" (แปลงเป็น boolean), end_at ว่าง → NULL"""
    
    code_name = (data.get("code_name") or "").strip()
    discount_raw = data.get("discount")
    discount_method = data.get("discount_method") if data.get("discount_method") in ("money", "percent") else "money"
    max_uses = data.get("max_uses")
    status_raw = data.get("status")
    status = True if status_raw in ('1',1,True) else False
    end_at = data.get("end_at")
    if not end_at or end_at == "":
        end_at = None

    if not code_name:
        raise ValueError("กรอกชื่อโค้ด")
    
    try:
        discount = float(discount_raw)
    except (ValueError, TypeError):
        raise ValueError("กรอกตัวเลขให้ถูกต้อง")
    if run_query("SELECT 1 FROM code WHERE code_name = %s", (code_name,)):
        raise ValueError("โค้ดชือนี้ถูกใช้ไปแล้ว")
    return run_command(
        "INSERT INTO code (code_name, discount, discount_method, max_uses, status, end_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (code_name, discount, discount_method, max_uses, status, end_at)
    )

def update_code(code_id, data):
    """แก้โค้ด — ฟิลด์เดียวกับ create_code"""
    # TODO: UPDATE code SET code_name=%s, discount=%s, discount_method=%s,
    #              max_uses=%s, status=%s, end_at=%s
    #       WHERE code_id = %s   (code_name ซ้ำกับโค้ดอื่น → raise ValueError)
    code_name = (data.get("code_name") or "").strip()
    discount_raw = data.get("discount")
    discount_method = data.get("discount_method") if data.get("discount_method") in ("money", "percent") else "money"
    max_uses = data.get("max_uses")
    status_raw = data.get("status")
    status = True if status_raw in ('1',1,True) else False
    end_at = data.get("end_at")
    if not end_at or end_at == "":
            end_at = None
    
    if not code_name:
            raise ValueError("กรอกชื่อโค้ด")
        
    try:
            discount = float(discount_raw)
    except (ValueError, TypeError):
            raise ValueError("กรอกตัวเลขให้ถูกต้อง")
    if run_query("SELECT 1 FROM code WHERE code_name = %s", (code_name,)):
            raise ValueError("โค้ดชือนี้ถูกใช้ไปแล้ว")

    return run_command(
        """
        UPDATE code
        SET code_name = %s,
            discount = %s,
            discount_method = %s,
            max_uses = %s,
            status = %s,
            end_at = %s
        WHERE code_id = %s
        """,
        (code_name, discount, discount_method, max_uses, status, end_at, code_id)
   )



def delete_code(code_id):
    """ลบโค้ด — ห้ามลบโค้ดที่เคยถูกใช้ (มีใน code_line หรือ payment)"""
    
    used_in_code_line = run_query(
        "SELECT 1 FROM code_line WHERE code_id = %s LIMIT 1", 
        (code_id,)
    )
    used_in_payment = run_query(
        "SELECT 1 FROM payment WHERE code_id = %s LIMIT 1", 
        (code_id,)
    )
    if used_in_code_line or used_in_payment:
        raise ValueError("โค้ดถูกใช้แล้ว — ปิดการใช้งาน (status=0) แทนการลบ")
        
    return run_command(
        "DELETE FROM code WHERE code_id = %s",
        (code_id,)
    )


# ---------- รีวิว (review) — หน้า /home แท็บออเดอร์ หลังจ่ายเงิน ----------
def get_my_reviews(user_id, order_id):
    """รีวิวของฉันสำหรับสินค้าในออเดอร์นี้ — คืน list ของ {product_id, rating, comment}
    (ใช้เติมค่าเดิมในฟอร์มรีวิวถ้าเคยรีวิวไว้แล้ว)"""
    # TODO: SELECT DISTINCT r.product_id, r.rating, r.comment
    #       FROM review r
    #       WHERE r.user_id = %s
    #         AND r.product_id IN (SELECT product_id FROM order_line WHERE order_id = %s)
    sql = """
            select 	DISTINCT r.product_id, r.rating, r.comment
            from 	review r 
            where 	r.user_id = %s
            AND r.product_id IN (SELECT product_id FROM order_line WHERE order_id = %s)
        """
    return run_query(sql, [user_id],[order_id])


def save_reviews(user_id, order_id, items):
    """บันทึกรีวิวทั้งชุดของออเดอร์ — items = [{product_id, rating, comment}, ...]
    1 คน ต่อ 1 สินค้า = 1 รีวิว (มีเดิม → UPDATE, ไม่มี → INSERT)"""
    for it in items:
        pid = int(it.get("product_id"))
        rating = int(it.get("rating") or 0)
        comment = (it.get("comment") or "").strip()
        if rating < 1 or rating > 5:
            raise ValueError("ดาวต้องอยู่ระหว่าง 1-5")

        # 3) upsert — มีเดิมแล้ว (user_id + product_id) → UPDATE, ไม่มี → INSERT
        #    (ยังไม่มี composite PK → ห้ามใช้ ON DUPLICATE KEY)
        old = run_query(
            "SELECT review_id FROM review WHERE user_id = %s AND product_id = %s",
            (user_id, pid))
        if old:
            run_command(
                "UPDATE review SET rating = %s, comment = %s "
                "WHERE user_id = %s AND product_id = %s",
                (rating, comment, user_id, pid))
        else:
            run_command(
                "INSERT INTO review (user_id, product_id, rating, comment) "
                "VALUES (%s, %s, %s, %s)",
                (user_id, pid, rating, comment))
    return {"saved": len(items)}


def get_product_reviews(product_id):
    """รีวิวทั้งหมดของสินค้า — คืน list ของ {user_id, name, rating, comment, create_at}
    (หน้า /home และ /admin กด "ดูรีวิว" ที่ตารางสินค้า)"""
    # TODO: SELECT r.user_id, u.name, r.rating, r.comment, r.create_at
    #       FROM review r
    #       LEFT JOIN users u ON u.user_id = r.user_id
    #       WHERE r.product_id = %s
    #       ORDER BY r.create_at DESC
    sql = """
            SELECT r.user_id, u.name, r.rating, r.comment, r.create_at
            FROM review r       
            LEFT JOIN users u ON u.user_id = r.user_id
            WHERE r.product_id = %s
            ORDER BY r.create_at DESC
        """
    return run_query(sql, [product_id])




# ============================================================
#  REPORT (รายงาน — ใช้ JOIN + GROUP BY + subquery)
# ============================================================
def report_summary():
    """ตัวเลขสรุปบนการ์ด dashboard — คืน dict เช่น {"customers": 10, ...}
    คำใบ้: ใช้ COUNT(*) หลายครั้ง"""
    # TODO: นับจำนวนรวมต่าง ๆ เพื่อแสดงบนการ์ด
    rows = run_query(
        """
        SELECT
            (SELECT COUNT(*)
             FROM users
             WHERE role = 'user') AS customers,

            (SELECT COUNT(*)
             FROM product) AS products,

            (SELECT COUNT(*)
             FROM shop_order) AS orders,

            (SELECT COALESCE(SUM(amount_pay), 0)
             FROM payment
             WHERE create_at >= DATE_FORMAT(CURRENT_DATE(), '%Y-%m-01')
               AND create_at < DATE_FORMAT(CURRENT_DATE() + INTERVAL 1 MONTH, '%Y-%m-01')) AS payment_month,

            (SELECT avg(rating)
             FROM review) AS  avg_review

        """
    )
    print(rows)
    return rows[0]
def report_best_selling():
    """📈 สินค้าขายดี (Best Sellers)
    คำใบ้: JOIN order_line→product, GROUP BY product, SUM(qty), ORDER BY DESC, LIMIT 5"""
    # TODO: เขียน SQL รายงานนี้ (เขียน JOIN แบบ explicit INNER JOIN ... ON ...)
    return run_query(
        """
        SELECT
                p.product_id,
                p.name,
                SUM(ol.quantity) AS total_sold
        FROM order_line AS ol
        INNER JOIN product AS p
                ON ol.product_id = p.product_id
        GROUP BY p.product_id, p.name
        ORDER BY total_sold DESC
        LIMIT 5
        """
    )

def report_customers_above_avg():
    """🏅 ลูกค้าที่ซื้อมากกว่าค่าเฉลี่ย (Above Average)
    คำใบ้: JOIN shop_order→order_line, GROUP BY customer, HAVING SUM(qty*unit_price) > (subquery AVG)"""
    # TODO: เขียน SQL รายงานนี้ (เขียน JOIN แบบ explicit INNER JOIN ... ON ...)
    return run_query(
        """
    SELECT
    	u.user_id,
    	u.name,
    	SUM(ol.unit_price * ol.quantity) AS total_spent
    FROM users AS u
    INNER JOIN 	shop_order AS so
    	on	u.user_id = so.user_id  
    INNER JOIN order_line AS ol
    	on	so.order_id = ol.order_id
    GROUP BY u.user_id, u.name
    HAVING SUM(ol.unit_price * ol.quantity) >
    (
        SELECT AVG(customer_total)
            FROM (
            SELECT SUM(ol.unit_price * ol.quantity) AS customer_total
            FROM users AS u
            INNER JOIN shop_order AS so
                ON u.user_id = so.user_id
            INNER JOIN order_line AS ol
                ON so.order_id = ol.order_id
            GROUP BY u.user_id
            ) AS customer_totals
    )
            """
    )

def report_high_rated():
    """⭐ สินค้าคะแนนรีวิวเฉลี่ย ≥ 4 (HAVING)
    คำใบ้: JOIN review→product, GROUP BY product, HAVING AVG(rating) >= 4"""
    # TODO: เขียน SQL รายงานนี้ (เขียน JOIN แบบ explicit INNER JOIN ... ON ...)
    return run_query(
        """
        SELECT
            p.product_id,
            p.name,
            AVG(r.rating) AS average_rating
        FROM product AS p
        INNER JOIN review AS r
            ON r.product_id = p.product_id
        GROUP BY p.product_id, p.name
        HAVING AVG(r.rating) >= %s
        """,
        (4,)
    )


# ============================================================
#  ลงทะเบียนรายงาน — หน้า /report อ่านจาก db.REPORTS
#  รูปแบบ: (key ใช้ใน URL, title แสดงบนการ์ด, ฟังก์ชัน)
# ============================================================
REPORTS = [
    ("best-selling", "📈 สินค้าขายดี (Top 5)", report_best_selling),
    ("above-average", "🏅 ลูกค้าที่ซื้อมากกว่าค่าเฉลี่ย", report_customers_above_avg),
    ("high-rated", "⭐ สินค้าคะแนนรีวิวเฉลี่ย ≥ 4", report_high_rated),
]

