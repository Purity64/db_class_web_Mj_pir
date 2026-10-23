// ============================================================
//  app.js  —  ตรรกะหน้าเว็บ (ทำให้เสร็จแล้ว ★ นิสิตไม่ต้องแก้)
//  ปรับช่องค้นหา/ฟอร์มได้ที่ตัวแปร ENTITIES ด้านล่าง
// ============================================================
// ★ ตัวอย่าง dropdown ที่อ่านข้อมูลจากฐานข้อมูล: ฟอร์ม "ออเดอร์" ช่อง cust_id
//   แสดง name แต่ส่งค่าเป็น cust_id (อ่านรายการจาก /api/customers)
//   ช่อง FK อื่น ๆ ทำแบบเดียวกันได้ — เปลี่ยน "type": "number" เป็น select + optionsFrom
const ENTITIES = {
  "customers": {
    "label": "user",
    "api": "/api/customers",
    "idKey": "user_id",
    "search": [
      {
        "key": "name",
        "label": "ชื่อ",
        "type": "text"
      },
      {
        "key": "email",
        "label": "อีเมล",
        "type": "text"
      },
      {
        "key": "role",
        "label": "role",
        "type": "select",
        "options": [
          "",
          "user",
          "admin"
        ]
      }
    ],
    "form": [
      {
        "key": "name",
        "label": "ชื่อ",
        "type": "text"
      },
      {
        "key": "email",
        "label": "อีเมล",
        "type": "text"
      },
      {
        "key": "password",
        "label": "รหัสผ่าน",
        "type": "text"
      },
      {
        "key": "role",
        "label": "role",
        "type": "select",
        "options": [
          "user",
          "admin"
        ]
      }
    ]
  },
  "products": {
    "label": "สินค้า",
    "api": "/api/products",
    "idKey": "product_id",
    "columns": ["product_id", "name", "detail", "category", "price", "discount", "stock"],
    "search": [
      {
        "key": "name",
        "label": "ชื่อสินค้า",
        "type": "text"
      },
      {
        "key": "category",
        "label": "หมวดหมู่",
        "type": "select",
        "optionsFrom": { "api": "/api/categories", "value": "category", "label": "category" }
      }
    ],
    "form": [
      {
        "key": "name",
        "label": "ชื่อสินค้า",
        "type": "text"
      },
      {
        "key": "detail",
        "label": "รายละเอียด",
        "type": "textarea"
      },
      {
        "key": "category",
        "label": "หมวดหมู่",
        "type": "text"
      },
      {
        "key": "price",
        "label": "ราคา",
        "type": "number"
      },
      {
        "key": "discount",
        "label": "ส่วนลด",
        "type": "number"
      },
      {
        "key": "stock",
        "label": "จำนวนสต็อก (ตอนเพิ่มใหม่)",
        "type": "number",
        "createOnly": true
      }
    ]
  },
  "orders": {
    "label": "ออเดอร์",
    "api": "/api/orders",
    "idKey": "order_id",
    "columns": ["order_id", "order_date", "status", "items", "total", "paid"],
    "search": [
      {
        "key": "status",
        "label": "สถานะ",
        "type": "select",
        "options": [
          { "value": "", "label": "ทั้งหมด" },
          { "value": "waitpay", "label": "รอชำระเงิน" },
          { "value": "success", "label": "สำเร็จ" },
          { "value": "cancel", "label": "ยกเลิก" }
        ]
      }
    ],
    "form": []
  },
  "code": {
    "label": "โค้ดส่วนลด",
    "api": "/api/codes",
    "idKey": "code_id",
    "columns": ["code_id", "code_name", "discount", "discount_method", "max_uses", "status", "end_at"],
    "search": [
      {
        "key": "code_name",
        "label": "ชื่อโค้ด",
        "type": "text"
      },
      {
        "key": "discount_method",
        "label": "วิธีลด",
        "type": "select",
        "options": [
          { "value": "", "label": "ทั้งหมด" },
          { "value": "money", "label": "money (บาท)" },
          { "value": "percent", "label": "percent (%)" }
        ]
      },
      {
        "key": "status",
        "label": "สถานะ",
        "type": "select",
        "options": [
          { "value": "", "label": "ทั้งหมด" },
          { "value": "1", "label": "เปิดใช้" },
          { "value": "0", "label": "ปิด" }
        ]
      }
    ],
    "form": [
      {
        "key": "code_name",
        "label": "ชื่อโค้ด",
        "type": "text"
      },
      {
        "key": "discount",
        "label": "ส่วนลด",
        "type": "number"
      },
      {
        "key": "discount_method",
        "label": "วิธีลด",
        "type": "select",
        "options": [
          { "value": "money", "label": "money (บาท)" },
          { "value": "percent", "label": "percent (%)" }
        ]
      },
      {
        "key": "max_uses",
        "label": "จำกัดการใช้ (0 = ไม่จำกัด)",
        "type": "number"
      },
      {
        "key": "status",
        "label": "สถานะ",
        "type": "select",
        "options": [
          { "value": "1", "label": "เปิดใช้" },
          { "value": "0", "label": "ปิด" }
        ]
      },
      {
        "key": "end_at",
        "label": "หมดอายุ (ว่าง = ไม่หมดอายุ)",
        "type": "datetime-local"
      }
    ]
  },
};

let current = Object.keys(ENTITIES)[0];
let editingId = null;
const $ = (s) => document.querySelector(s);
function setStatus(el, msg, cls = "") { el.className = "status " + cls; el.textContent = msg; }
async function api(url, opts) { const res = await fetch(url, opts); return res.json(); }

function fieldHtml(f, prefix, value = "") {
  if (f.type === "heading") return '<div class="form-section">' + f.label + '</div>';
  let input;
  if (f.type === "select") {
    // options เป็นข้อความ "a" หรือ {value, label} ก็ได้
    input = '<select id="' + prefix + f.key + '">' +
      f.options.map(o => {
        const v = typeof o === "object" ? o.value : o;
        const t = typeof o === "object" ? o.label : (o || "ทั้งหมด");
        return '<option value="' + v + '"' + (String(v) === String(value ?? "") ? " selected" : "") + '>' + t + '</option>';
      }).join("") + '</select>';
  } else if (f.type === "textarea") {
    input = '<textarea id="' + prefix + f.key + '" rows="3" style="width:100%;font:inherit;padding:6px">' + (value ?? "") + '</textarea>';
  } else if (f.type === "datetime-local") {
    const v = value ? String(value).replace(" ", "T").slice(0, 16) : "";
    input = '<input id="' + prefix + f.key + '" type="datetime-local" value="' + v + '">';
  } else { input = '<input id="' + prefix + f.key + '" type="' + f.type + '" value="' + (value ?? "") + '">'; }
  return '<div class="field"><label>' + f.label + '</label>' + input + '</div>';
}
// ช่อง select ที่มี optionsFrom → ดึงตัวเลือกจาก API (เช่น รายชื่อหมวดหมู่จากฐานข้อมูล)
async function loadOptions(fields, forSearch) {
  for (const f of fields.filter(f => f.optionsFrom)) {
    const src = f.optionsFrom, r = await api(src.api);
    f.options = r.ok ? (r.data || []).map(row => ({ value: row[src.value], label: row[src.label] }))
                     : [{ value: "", label: (r.todo ? "🚧 " : "⚠️ ") + r.error }];
    if (forSearch && r.ok) f.options.unshift({ value: "", label: "ทั้งหมด" });
  }
}
// ช่องในฟอร์มที่ใช้อยู่ตอนนี้ (editOnly = แสดงเฉพาะตอนแก้ไข, createOnly = แสดงเฉพาะตอนเพิ่มใหม่)
function formFields() {
  return ENTITIES[current].form.filter(f =>
    (!f.editOnly || editingId !== null) && (!f.createOnly || editingId === null));
}
async function buildSearch() {
  const cfg = ENTITIES[current];
  await loadOptions(cfg.search, true);
  if (cfg !== ENTITIES[current]) return;   // ผู้ใช้เปลี่ยนแท็บระหว่างรอ
  $("#searchTitle").textContent = cfg.label;
  $("#searchFields").innerHTML = cfg.search.map(f => fieldHtml(f, "s_")).join("");
  // ซ่อนปุ่มเพิ่มเมื่อ entity ไม่มีฟอร์ม (เช่น ออเดอร์ — ดูอย่างเดียว)
  if ($("#btnAdd")) $("#btnAdd").style.display = (cfg.form && cfg.form.length) ? "" : "none";
}
async function doSearch() {
  const cfg = ENTITIES[current];
  const params = new URLSearchParams();
  cfg.search.forEach(f => { const v = $("#s_" + f.key).value; if (v) params.append(f.key, v); });
  setStatus($("#status"), "กำลังค้นหา...");
  renderTable(await api(cfg.api + "?" + params.toString()));
}
function renderTable(r) {
  const head = $("#tableHead"), body = $("#tableBody"), st = $("#status");
  head.innerHTML = ""; body.innerHTML = "";
  if (!r.ok) { setStatus(st, (r.todo ? "🚧 " : "⚠️ ") + r.error, r.todo ? "todo" : "err"); return; }
  const rows = r.data || [];
  if (rows.length === 0) { setStatus(st, "ไม่พบข้อมูล"); return; }
  setStatus(st, "พบ " + rows.length + " รายการ");
  const cfg = ENTITIES[current];
  const avail = Object.keys(rows[0]);
  const cols = cfg.columns ? cfg.columns.filter(c => avail.includes(c)) : avail;
  head.innerHTML = cols.map(c => "<th>" + c + "</th>").join("") + "<th>จัดการ</th>";
  body.innerHTML = rows.map(row => {
    const id = row[cfg.idKey];
    let actions;
    if (cfg.idKey === "order_id") {
      // ออเดอร์: ดูอย่างเดียว (ไม่มี route แก้ไข/ลบ)
      actions = '<button class="btn sm" onclick="openOrderDetail(' + id + ')">👁 ดูรายการ</button>';
    } else {
      actions = '<button class="btn sm" onclick="editRow(' + id + ')">แก้ไข</button> ' +
        '<button class="btn sm del" onclick="deleteRow(' + id + ')">ลบ</button>';
      if (cfg.idKey === "product_id" && document.getElementById("stockModal")) {
        actions += ' <button class="btn sm" onclick="openStockModal(' + id + ')">📦 สต็อก</button>';
      }
    }
    return "<tr>" + cols.map(c => "<td>" + (row[c] ?? "—") + "</td>").join("") +
      "<td>" + actions + "</td></tr>";
  }).join("");
}
async function openForm(title, data = {}) {
  await loadOptions(formFields(), false);
  $("#modalTitle").textContent = title;
  $("#formFields").innerHTML = formFields().map(f => fieldHtml(f, "f_", data[f.key])).join("");
  $("#modal").classList.remove("hidden");
}
function collectForm() { const d = {}; formFields().filter(f => f.key).forEach(f => d[f.key] = $("#f_" + f.key).value); return d; }
async function editRow(id) {
  const cfg = ENTITIES[current];
  const r = await api(cfg.api + "/" + id);
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  editingId = id; openForm("แก้ไขข้อมูล", r.data);
}
async function deleteRow(id) {
  if (!confirm("ยืนยันการลบ?")) return;
  const r = await api(ENTITIES[current].api + "/" + id, { method: "DELETE" });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  doSearch();
}
async function save() {
  const cfg = ENTITIES[current], data = collectForm();
  const opts = { method: editingId ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
  const r = await api(editingId ? cfg.api + "/" + editingId : cfg.api, opts);
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  $("#modal").classList.add("hidden"); doSearch();
}
document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
  t.classList.add("active"); current = t.dataset.entity;
  buildSearch(); $("#tableHead").innerHTML = ""; $("#tableBody").innerHTML = "";
  setStatus($("#status"), 'กด "ค้นหา" เพื่อแสดงข้อมูล');
}));
const on = (sel, fn) => { const el = $(sel); if (el) el.onclick = fn; };
on("#btnSearch", doSearch);
on("#btnClear", () => buildSearch());
on("#btnAdd", () => { editingId = null; openForm("เพิ่มข้อมูลใหม่"); });
on("#btnSave", save);
on("#btnCancel", () => $("#modal").classList.add("hidden"));

// ===== ดูรายการสินค้าในออเดอร์ (/admin) =====
async function openOrderDetail(orderId) {
  const st = $("#odStatus"), body = $("#odBody");
  if (!st || !body) return;
  $("#odTitle").textContent = "ออเดอร์ #" + orderId;
  body.innerHTML = "";
  $("#orderDetailModal").classList.remove("hidden");
  setStatus(st, "กำลังโหลด...");
  const r = await api("/api/orders/" + orderId);
  if (!r.ok) { setStatus(st, (r.todo ? "🚧 " : "⚠️ ") + r.error, r.todo ? "todo" : "err"); return; }
  const items = r.data || [];
  if (!items.length) { setStatus(st, "ไม่มีรายการ"); return; }
  setStatus(st, "");
  body.innerHTML = items.map(it =>
    "<tr><td>" + (it.name ?? "—") + "</td><td>" + (it.quantity ?? "—") + "</td><td>" +
    (it.unit_price ?? "—") + "</td><td>" + (it.line_total ?? "—") + "</td><td>" +
    (it.username || "—") + "</td><td>" + (it.password || "—") + "</td></tr>").join("");
}
on("#btnOdClose", () => $("#orderDetailModal").classList.add("hidden"));
buildSearch();
setStatus($("#status"), 'กด "ค้นหา" เพื่อแสดงข้อมูล');

// ===== จัดการสต็อก (product_detail) ของสินค้า =====
let stockProductId = null;
let stockRows = [];
let editingStockId = null;
async function openStockModal(pid) {
  stockProductId = pid;
  const t = $("#stockTitle"); if (!t) return;
  t.textContent = "📦 สต็อกสินค้า #" + pid;
  if ($("#stockUser")) $("#stockUser").value = "";
  if ($("#stockPass")) $("#stockPass").value = "";
  $("#stockModal").classList.remove("hidden");
  await loadStock();
}
async function loadStock() {
  const st = $("#stockStatus"), body = $("#stockBody");
  if (!st || stockProductId === null) return;
  setStatus(st, "กำลังโหลด...");
  const r = await api("/api/products/" + stockProductId + "/stock");
  if (!r.ok) { setStatus(st, (r.todo ? "🚧 " : "⚠️ ") + r.error, r.todo ? "todo" : "err"); body.innerHTML = ""; stockRows = []; return; }
  stockRows = r.data || [];
  setStatus(st, "ทั้งหมด " + stockRows.length + " บัญชี");
  body.innerHTML = stockRows.map(s =>
    "<tr><td>" + s.product_detail_id + "</td><td>" + (s.username ?? "—") + "</td><td>" +
    (s.password ?? "—") + "</td><td>" + (s.use ?? "—") + "</td><td>" + (s.status ?? "—") + "</td><td>" +
    '<button class="btn sm" onclick="editStockRow(' + s.product_detail_id + ')">แก้ไข</button> ' +
    '<button class="btn sm del" onclick="deleteStockRow(' + s.product_detail_id + ')">ลบ</button>' +
    "</td></tr>").join("");
}
async function addStock() {
  const u = ($("#stockUser").value || "").trim(), p = ($("#stockPass").value || "").trim();
  if (!u || !p) { alert("กรอก username และ password ให้ครบ"); return; }
  const r = await api("/api/products/" + stockProductId + "/stock", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ qty: 1, username: u, password: p })
  });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  loadStock();
}
function editStockRow(pdId) {
  const s = stockRows.find(x => x.product_detail_id === pdId);
  if (!s) return;
  editingStockId = pdId;
  $("#seUser").value = s.username ?? "";
  $("#sePass").value = s.password ?? "";
  const useVal = (s.use !== undefined && s.use !== null && s.use !== "") ? Number(s.use)
                 : (s.status === "ขายแล้ว" ? 1 : 0);
  $("#seUse").value = useVal ? "1" : "0";
  $("#stockEditModal").classList.remove("hidden");
}
async function saveStockEdit() {
  const u = ($("#seUser").value || "").trim(), p = ($("#sePass").value || "").trim();
  if (!u || !p) { alert("กรอก username และ password ให้ครบ"); return; }
  const r = await api("/api/product-details/" + editingStockId, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: p, use: parseInt($("#seUse").value, 10) })
  });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  $("#stockEditModal").classList.add("hidden");
  loadStock();
}
async function deleteStockRow(pdId) {
  if (!confirm("ยืนยันลบบัญชี #" + pdId + " ?")) return;
  const r = await api("/api/product-details/" + pdId, { method: "DELETE" });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  loadStock();
}
on("#btnAddStock", addStock);
on("#btnStockClose", () => $("#stockModal").classList.add("hidden"));
on("#btnStockEditSave", saveStockEdit);
on("#btnStockEditCancel", () => $("#stockEditModal").classList.add("hidden"));
