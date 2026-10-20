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
_STOCK_SQL = ("(SELECT COUNT(*) FROM product_detail pd "
              "WHERE pd.product_id = p.product_id AND pd.use = FALSE   and(pd.order_line_id IS NULL or pd.book_end_at <= NOW()))")

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






REPORTS = []


def report_summary():
    return {}

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
    SELECT %s, product_id, price, %s
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
    _todo("remove_cart_item")


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
                WHERE order_line_id IS NULL AND product_id = %s
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
    if total <= 0:
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
        "SET pd.use = TRUE "
        "WHERE ol.order_id = %s AND pd.use = FALSE",
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
