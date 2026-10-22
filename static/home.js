// ============================================================
//  app.js  —  ตรรกะหน้าเว็บ (ทำให้เสร็จแล้ว ★ นิสิตไม่ต้องแก้)
//  ปรับช่องค้นหา/ฟอร์มได้ที่ตัวแปร ENTITIES ด้านล่าง
// ============================================================
// ★ ตัวอย่าง dropdown ที่อ่านข้อมูลจากฐานข้อมูล: ฟอร์ม "ออเดอร์" ช่อง cust_id
//   แสดง name แต่ส่งค่าเป็น cust_id (อ่านรายการจาก /api/customers)
//   ช่อง FK อื่น ๆ ทำแบบเดียวกันได้ — เปลี่ยน "type": "number" เป็น select + optionsFrom
const ENTITIES = {  
  "products": {
    "label": "สินค้า",
    "api": "/api/products",
    "idKey": "product_id",
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
        "key": "stock",
        "label": "สต็อก",
        "type": "number"
      }
    ]
  },
  "orders": {
    "label": "ออเดอร์ ของฉัน",
    "api": "/api/orders",
    "idKey": "order_id",
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
    ]
  }
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
    input = '<select id="' + prefix + f.key + '">' +
      f.options.map(o => {
        const v = typeof o === "object" ? o.value : o;
        const t = typeof o === "object" ? o.label : (o || "ทั้งหมด");
        return '<option value="' + v + '"' + (String(v) === String(value ?? "") ? " selected" : "") + '>' + t + '</option>';
      }).join("") + '</select>';
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
// ช่องในฟอร์มที่ใช้อยู่ตอนนี้ (ช่อง editOnly แสดงเฉพาะตอนแก้ไข)
function formFields() { return (ENTITIES[current].form || []).filter(f => !f.editOnly || editingId !== null); }
async function buildSearch() {
  const cfg = ENTITIES[current];
  await loadOptions(cfg.search, true);
  if (cfg !== ENTITIES[current]) return;   // ผู้ใช้เปลี่ยนแท็บระหว่างรอ
  $("#searchTitle").textContent = cfg.label;
  $("#searchFields").innerHTML = cfg.search.map(f => fieldHtml(f, "s_")).join("");
}
async function doSearch() {
  const cfg = ENTITIES[current];
  const params = new URLSearchParams();
  cfg.search.forEach(f => { const v = $("#s_" + f.key).value; if (v) params.append(f.key, v); });
  setStatus($("#status"), "กำลังค้นหา...");
  renderTable(await api(cfg.api + "?" + params.toString()));
}
function renderTable(r) {
  const cfg = ENTITIES[current];
  const head = $("#tableHead"), body = $("#tableBody"), st = $("#status");
  head.innerHTML = ""; body.innerHTML = "";
  if (!r.ok) { setStatus(st, (r.todo ? "🚧 " : "⚠️ ") + r.error, r.todo ? "todo" : "err"); return; }
  const rows = r.data || [];
  if (rows.length === 0) { setStatus(st, "ไม่พบข้อมูล"); return; }
  setStatus(st, "พบ " + rows.length + " รายการ");
  // หน้าสินค้าลูกค้า: แสดงเฉพาะคอลัมน์ที่ต้องการ (กันตารางกว้างเมื่อ backend เพิ่มคอลัมน์ใหม่)
  const PRODUCT_COLS = ["product_id", "name", "category", "price", "discount", "stock"];
  let cols = Object.keys(rows[0]);
  if (cfg.idKey === "product_id") cols = cols.filter(c => PRODUCT_COLS.includes(c));
  if (cfg.idKey === "product_id") {
    head.innerHTML = cols.map(c => "<th>" + c + "</th>").join("") + "<th>สั่งซื้อ</th>";
    body.innerHTML = rows.map(row => {
      const id = row[cfg.idKey];
      return "<tr>" + cols.map(c => "<td>" + (row[c] ?? "—") + "</td>").join("") +
        '<td><button class="btn sm add" onclick="addToCart(' + id + ", " + (row.stock ?? 0) + ')">🛒 ใส่ตะกร้า</button></td></tr>';
    }).join("");
  } else {
    const isOrders = cfg.idKey === "order_id";
    head.innerHTML = cols.map(c => "<th>" + c + "</th>").join("") +
      "<th>" + (isOrders ? "การดำเนินการ" : "รายละเอียด") + "</th>";
    body.innerHTML = rows.map(row => {
      const id = row[cfg.idKey];
      let actions = "";
      if (!isOrders || row.status === "success") {
        actions = '<button class="btn sm" onclick="showOrderDetail(' + id + ')">ดูรายละเอียด</button>';
      }
      if (isOrders && row.status === "success") {
        actions += ' <button class="btn sm add" onclick="openReview(' + id + ')">⭐ รีวิว</button>';
      }
      if (isOrders && row.status === "waitpay") {
        const amt = Number(row.total ?? 0);
        actions += (actions ? " " : "") + '<button class="btn sm primary" onclick="openPayModal(' + id + ", " + amt + ')">💳 จ่ายเงิน (QR)</button>';
        actions += ' <button class="btn sm del" onclick="cancelOrder(' + id + ')">❌ ยกเลิก</button>';
      }
      return "<tr>" + cols.map(c => "<td>" + (row[c] ?? "—") + "</td>").join("") +
        "<td>" + actions + "</td></tr>";
    }).join("");
  }
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
document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", async () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
  t.classList.add("active"); current = t.dataset.entity;
  $("#tableHead").innerHTML = ""; $("#tableBody").innerHTML = "";
  $("#cartFooter").style.display = "none";
  if (current === "cart") {
    $("#searchCard").style.display = "none";
    showCart();
  } else {
    $("#searchCard").style.display = "";
    await buildSearch(); doSearch();
  }
}));
const on = (sel, fn) => { const el = $(sel); if (el) el.onclick = fn; };
on("#btnSearch", doSearch);
on("#btnClear", () => buildSearch());
on("#btnAdd", () => { editingId = null; openForm("เพิ่มข้อมูลใหม่"); });
on("#btnSave", save);
on("#btnCancel", () => $("#modal").classList.add("hidden"));
on("#btnConfirmCart", confirmCart);
on("#btnPaySuccess", paySuccess);
on("#btnPayCancel", payCancel);
on("#btnCheckCode", checkCode);
on("#btnOdClose", () => $("#orderDetailModal").classList.add("hidden"));

// ===== รีวิวสินค้าหลังชำระเงินเสร็จ =====
const rvEsc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let reviewOrderId = null;
async function openReview(orderId) {
  reviewOrderId = orderId;
  const st = $("#rvStatus");
  $("#rvTitle").textContent = "⭐ รีวิวออเดอร์ #" + orderId;
  $("#rvBody").innerHTML = "";
  $("#reviewModal").classList.remove("hidden");
  setStatus(st, "กำลังโหลด...");
  const d = await api("/api/orders/" + orderId);
  if (!d.ok) { setStatus(st, (d.todo ? "🚧 " : "⚠️ ") + d.error, d.todo ? "todo" : "err"); return; }
  // merge สินค้าเดิมซื้อหลายชิ้น → 1 แถว (review = user × product)
  const byP = new Map();
  (d.data || []).forEach(it => {
    if (it.product_id && !byP.has(it.product_id)) byP.set(it.product_id, it.name);
  });
  if (byP.size === 0) { setStatus(st, "ไม่มีรายการสินค้า"); return; }
  const rv = await api("/api/reviews?order_id=" + orderId);
  const mine = {};
  if (rv.ok) (rv.data || []).forEach(r => mine[r.product_id] = r);
  setStatus(st, "");
  $("#rvBody").innerHTML = [...byP.entries()].map(([pid, name]) => {
    const m = mine[pid] || {};
    const rate = Number(m.rating) || 5;
    const opts = [1, 2, 3, 4, 5].map(n =>
      '<option value="' + n + '"' + (n === rate ? " selected" : "") + ">" + n + " ★</option>").join("");
    return '<tr data-pid="' + pid + '"><td>' + rvEsc(name) + "</td>" +
      '<td><select class="rvRate">' + opts + "</select></td>" +
      '<td><input class="rvComment" type="text" style="width:100%;padding:6px" value="' +
      rvEsc(m.comment) + '" placeholder="ความคิดเห็น (ถ้ามี)"></td></tr>';
  }).join("");
}
async function saveReview() {
  const items = [...document.querySelectorAll("#rvBody tr[data-pid]")].map(tr => ({
    product_id: Number(tr.dataset.pid),
    rating: Number(tr.querySelector(".rvRate").value),
    comment: tr.querySelector(".rvComment").value.trim()
  }));
  if (!items.length) { alert("ไม่มีรายการให้รีวิว"); return; }
  if (items.some(x => x.rating < 1 || x.rating > 5)) { alert("ดาวต้องอยู่ระหว่าง 1-5"); return; }
  const r = await api("/api/reviews", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_id: reviewOrderId, items })
  });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  $("#reviewModal").classList.add("hidden");
  alert("บันทึกรีวิวแล้ว ⭐");
}
on("#btnReviewSave", saveReview);
on("#btnReviewClose", () => $("#reviewModal").classList.add("hidden"));
(async () => {
  await buildSearch();
  if (document.querySelector(".tab.active")) doSearch();
  else setStatus($("#status"), 'กด "ค้นหา" เพื่อแสดงข้อมูล');
})();
setStatus($("#status"), 'กด "ค้นหา" เพื่อแสดงข้อมูล');

async function addToCart(productId, stock = 0) {
  if (stock <= 0) { alert("สินค้าหมด"); return; }
  const qty = parseInt(prompt("จำนวน (ชิ้น)", "1"), 10);
  if (!qty || qty < 1) return;
  if (qty > stock) { alert("สินค้าคงเหลือ " + stock + " ชิ้น"); return; }
  const r = await api("/api/cart/items", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, qty })
  });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  alert("เพิ่มลงตะกร้าแล้ว " + qty + " ชิ้น");
  if (current === "cart") showCart();
}

// ★ ตารางตะกร้า: แต่ละคอลัมน์ map กับฟิลด์จาก /api/cart (db.get_cart)
//   ถ้า backend เปลี่ยนชื่อฟิลด์ในอนาคต → แก้เฉพาะ field ด้านล่าง ไม่ต้องแตะโค้ดส่วนอื่น
const CART_COLS = [
  { label: "สินค้า", field: ["name", "product_name"], fallback: "—" },
  { label: "ราคา",   field: ["price", "unit_price"],  fallback: 0 },
  { label: "จำนวน", field: ["qty", "quantity"],       fallback: 1, input: true },
  { label: "รวม",    field: ["line_total"],           fallback: null },
];
const CART_KEYS = { del: ["product_id", "order_line_id"] };  // คีย์สำหรับปุ่มลบ/แก้จำนวน

function pickField(row, names, fallback) {
  for (const n of names) {
    if (row[n] !== undefined && row[n] !== null) return row[n];
  }
  return fallback;
}

async function showCart() {
  const head = $("#tableHead"), body = $("#tableBody"), st = $("#status"), foot = $("#cartFooter");
  head.innerHTML = ""; body.innerHTML = ""; foot.style.display = "none";
  const r = await api("/api/cart");
  if (!r.ok) { setStatus(st, (r.todo ? "🚧 " : "⚠️ ") + r.error, r.todo ? "todo" : "err"); return; }
  const d = r.data || {};
  // รองรับหลายรูปทรงข้อมูล (backend เปลี่ยนได้ในอนาคตโดยไม่พัง):
  //   {items:[...], total, count}  |  [ {...}, ... ]  |  { แถวเดียว }
  let items = [];
  if (Array.isArray(d)) items = d;
  else if (Array.isArray(d.items)) items = d.items;
  else if (typeof d === "object" && d !== null && Object.keys(d).length) items = [d];
  if (items.length === 0) { setStatus(st, "ตะกร้าว่าง"); return; }

  const rows = items.map(it => {
    const price = Number(pickField(it, CART_COLS[1].field, 0));
    const qty = Number(pickField(it, CART_COLS[2].field, 1));
    let lineTotal = pickField(it, CART_COLS[3].field, null);
    if (lineTotal === null) lineTotal = price * qty;   // คำนวณเองถ้า backend ไม่ส่งมา
    return {
      name: pickField(it, CART_COLS[0].field, it.product_id ?? "—"),
      price: price, qty: qty, lineTotal: Number(lineTotal),
      key: pickField(it, CART_KEYS.del, null)
    };
  });

  head.innerHTML = CART_COLS.map(c => "<th>" + c.label + "</th>").join("") + "<th>ลบ</th>";
  body.innerHTML = rows.map(x => {
    const qtyCell = (CART_COLS[2].input && x.key !== null)
      ? ""+ x.qty
      : x.qty;
    
    const delBtn = (x.key !== null)
      ? '<button class="btn sm del" onclick="removeCartItem(' + x.key + ')">ลบ</button>'
      : "—";
    return "<tr><td>" + x.name + "</td><td>" + x.price + "</td><td>" + qtyCell +
           "</td><td>" + x.lineTotal + "</td><td>" + delBtn + "</td></tr>";
  }).join("");

  const total = (d.total !== undefined) ? d.total : rows.reduce((s, x) => s + x.lineTotal, 0);
  const count = (d.count !== undefined) ? d.count : rows.reduce((s, x) => s + x.qty, 0);
  $("#cartTotal").textContent = total;
  foot.style.display = "";
  setStatus(st, "สินค้าในตะกร้า " + count + " ชิ้น");
}

async function updateCartQty(productId, qty) {
  const r = await api("/api/cart/items/" + productId, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ qty: Number(qty) })
  });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); }
  showCart();
}

async function removeCartItem(productId) {
  if (!confirm("เอาสินค้านี้ออกจากตะกร้า?")) return;
  const r = await api("/api/cart/items/" + productId, { method: "DELETE" });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); }
  showCart();
}

var pendingPayOrderId = null;
var pendingPayAmount = 0;
var pendingPayCode = null;

function drawFakeQr(canvas, seed) {
  const n = 25, size = canvas.width / n;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  let h = 2166136261;
  for (const ch of String(seed)) h = ((h ^ ch.charCodeAt(0)) * 16777619) >>> 0;
  ctx.fillStyle = "#111";
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      h = (Math.imul(h, 1103515245) + 12345) >>> 0;
      if ((h >> 9) & 1) ctx.fillRect(x * size, y * size, size, size);
    }
  }
  [[0, 0], [n - 7, 0], [0, n - 7]].forEach(([fx, fy]) => {
    ctx.fillStyle = "#111"; ctx.fillRect(fx * size, fy * size, 7 * size, 7 * size);
    ctx.fillStyle = "#fff"; ctx.fillRect((fx + 1) * size, (fy + 1) * size, 5 * size, 5 * size);
    ctx.fillStyle = "#111"; ctx.fillRect((fx + 2) * size, (fy + 2) * size, 3 * size, 3 * size);
  });
}

async function confirmCart() {
  const r = await api("/api/cart/confirm");
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  const d = r.data || {};
  if (!d.affected) { alert("ตะกร้าว่าง"); return; }
  document.querySelector('.tab[data-entity="orders"]').click();
}

function openPayModal(orderId, amount) {
  pendingPayOrderId = orderId;
  pendingPayAmount = Number(amount) || 0;
  pendingPayCode = null;
  const canvas = $("#qrCanvas");
  if (canvas) drawFakeQr(canvas, orderId);
  $("#payAmount").textContent = pendingPayAmount;
  $("#payRef").textContent = "ออเดอร์ #" + orderId;
  if ($("#payCode")) $("#payCode").value = "";
  if ($("#payDiscount")) $("#payDiscount").textContent = "";
  $("#payModal").classList.remove("hidden");
}

async function checkCode() {
  if (pendingPayOrderId == null) return;
  const code = ($("#payCode").value || "").trim();
  const discEl = $("#payDiscount");
  if (!code) {
    pendingPayCode = null;
    $("#payAmount").textContent = pendingPayAmount;
    discEl.textContent = "";
    return;
  }
  const r = await api("/api/orders/" + pendingPayOrderId + "/check-code", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code_name: code })
  });
  if (!r.ok) {
    pendingPayCode = null;
    $("#payAmount").textContent = pendingPayAmount;
    discEl.textContent = "";
    alert((r.todo ? "🚧 " : "⚠️ ") + r.error);
    return;
  }
  const d = r.data || {};
  pendingPayCode = code;
  $("#payAmount").textContent = d.final;
  discEl.textContent = "โค้ด " + d.code_name + " ลด " + d.discount +
    (d.discount_method === "percent" ? "%" : " บาท") + " → เหลือ " + d.final + " บาท";
}

async function paySuccess() {
  if (pendingPayOrderId == null) return;
  const orderId = pendingPayOrderId;
  const r = await api("/api/orders/" + orderId + "/pay", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pendingPayCode ? { code_name: pendingPayCode } : {})
  });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  const paid = r.data && r.data.amount_pay;
  pendingPayOrderId = null;
  pendingPayAmount = 0;
  pendingPayCode = null;
  $("#payModal").classList.add("hidden");
  alert("ชำระเงินสำเร็จ เลขที่ออเดอร์ #" + (r.data.order_id ?? orderId) +
    (paid !== undefined ? " ยอด " + paid + " บาท" : ""));
  if (current === "orders") doSearch();
  else document.querySelector('.tab[data-entity="orders"]').click();
}

function payCancel() {
  pendingPayOrderId = null;
  pendingPayAmount = 0;
  pendingPayCode = null;
  $("#payModal").classList.add("hidden");
  setStatus($("#status"), "ยกเลิกการชำระเงิน — ออเดอร์ยังรอชำระอยู่");
}

async function cancelOrder(orderId) {
  if (!confirm("ยกเลิกออเดอร์ #" + orderId + " ?")) return;
  const r = await api("/api/orders/" + orderId + "/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}"
  });
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  alert("ยกเลิกออเดอร์ #" + orderId + " แล้ว");
  if (current === "orders") doSearch();
}

async function showOrderDetail(orderId) {
  const r = await api("/api/orders/" + orderId);
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  const items = r.data || [];
  $("#odBody").innerHTML = items.length ? items.map(it =>
    "<tr><td>" + it.name + "</td><td>" + it.quantity + "</td><td>" + it.unit_price + "</td>" +
    "<td>" + it.line_total + "</td><td>" + (it.username || "—") + "</td><td>" + (it.password || "—") + "</td></tr>"
  ).join("") : '<tr><td colspan="6">ไม่มีรายการ</td></tr>';
  $("#orderDetailModal").classList.remove("hidden");
}

(async () => {
  const me = await api("/api/me");  
  if (!me.ok || !me.data) { location.href = "/"; return; }
  const info = document.getElementById("userInfo");
  if (info) info.textContent = `user ${me.data.user_id} (${me.data.role})`;
})();
document.getElementById("logoutLink")?.addEventListener("click", async (e) => {
  e.preventDefault();
  await api("/api/logout", { method: "POST" });
  location.href = "/";
});
