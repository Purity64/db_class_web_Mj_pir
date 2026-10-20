# ร้านค้าออนไลน์ (Mini Online Shop) — Term Project Template

เทมเพลตนี้ทำส่วนหน้าเว็บ (frontend) และ API ให้แล้ว
งานของนิสิตคือ **ออกแบบฐานข้อมูล และเขียน SQL** ใน `db.py` กับ `schema.sql`

## เริ่มต้น
1. `pip install -r requirements.txt`
2. แก้ `config.py` ใส่ user/password/host ของ MySQL ที่อาจารย์แจกให้
3. ออกแบบและสร้างตารางใน `schema.sql` แล้วรันบน MySQL ของตัวเอง
4. `python app.py` → เปิด http://127.0.0.1:5000

> เปิดมาจะเห็นหน้าเว็บ แต่กดค้นหาจะขึ้น 🚧 TODO จนกว่าจะเขียน SQL ครบ

## งานที่ต้องทำใน db.py (มองหา # TODO)
**CRUD:**
  - search_customers, get/create/update/delete_customer
  - search_products, get/create/update/delete_product
  - search_orders, get/create/update/delete_order

  - check_can_ship — ตรวจสอบก่อนบันทึก (ดูหัวข้อ "ฟีเจอร์" ด้านล่าง)

**รายงาน (JOIN + GROUP BY + subquery):**
  - report_summary — การ์ดสรุป (เขียน SQL แทนค่า None ทีละการ์ด + คิดการ์ดเพิ่มเอง 2 ใบ)
  - report_best_selling — 📈 สินค้าขายดี (Best Sellers)
  - report_customers_above_avg — 🏅 ลูกค้าที่ซื้อมากกว่าค่าเฉลี่ย (Above Average)
  - report_high_rated — ⭐ สินค้าคะแนนรีวิวเฉลี่ย ≥ 4 (HAVING)
  - รายงานเพิ่มเติมที่ออกแบบเอง (ดูหัวข้อ "วิธีเพิ่มรายงานใหม่")

## ฟีเจอร์ที่ต้องทำให้ใช้งานได้
- **ออเดอร์ → ลูกค้า** เป็น dropdown ที่อ่านรายชื่อจากฐานข้อมูล
- **ยอดรวมของออเดอร์ (total)** คำนวณจาก `SUM(qty × unit_price)` ตอน SELECT — ไม่เก็บเป็นคอลัมน์
- **ตรวจก่อนบันทึก** (`check_can_ship`): จัดส่ง (shipped) ได้เฉพาะออเดอร์ที่ชำระเงินแล้ว และห้ามลบออเดอร์ที่ชำระเงินแล้ว

## วิธีเพิ่มรายงานใหม่ (แก้แค่ db.py)
1. เขียนฟังก์ชันใหม่ใน db.py ให้ `return run_query(sql)`
   (ชื่อคอลัมน์ที่ตั้งด้วย `AS '...'` จะเป็นหัวตารางบนเว็บ)
2. เพิ่ม 1 บรรทัดในรายการ `REPORTS` ท้าย db.py
   ```python
   ("my-report", "📋 รายงานของฉัน", report_my_report),
   ```
3. รีเฟรชหน้า /report — กล่องรายงานใหม่จะขึ้นเอง

## กติกา
- ใช้ `%s` เป็น placeholder เสมอ (กัน SQL injection)
- query ที่ join หลายตารางเขียนแบบ explicit INNER JOIN ... ON ...
- ชื่อตาราง/คอลัมน์ใน db.py ต้องตรงกับ schema.sql
- ไม่เก็บค่าที่คำนวณได้เป็นคอลัมน์ (เช่น ยอดรวม จำนวนคงเหลือ) — คำนวณตอน SELECT
- ช่องที่ไม่ได้กรอกในฟอร์มจะส่งมาเป็น `""` — คอลัมน์ที่ว่างได้ (เช่น DATE) ให้ใช้ `blank_to_none(...)`
- แจ้งข้อผิดพลาดให้ผู้ใช้เห็น: `raise ValueError("ข้อความ")` → หน้าเว็บแสดงเป็น alert
