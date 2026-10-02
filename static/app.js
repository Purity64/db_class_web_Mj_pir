// ============================================================
//  app.js  —  ตรรกะหน้าเว็บ (ทำให้เสร็จแล้ว ★ นิสิตไม่ต้องแก้)
//  ปรับช่องค้นหา/ฟอร์มได้ที่ตัวแปร ENTITIES ด้านล่าง
// ============================================================
const ENTITIES = {
  "customers": {
    "label": "ผู้ใช้",
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
        "label": "สิทธิ",
        "type": "select",
        "options": [
          "",
          "customer",
          "employee"
        ]
      },
      {
        "key": "tier",
        "label": "ระดับ",
        "type": "select",
        "options": [
          "",
          "normal",
          "vip"
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
        "key": "role",
        "label": "สิทธิ",
        "type": "select",
        "options": [
          "customer",
          "employee"
        ]
      },
      {
        "key": "tier",
        "label": "ระดับ",
        "type": "select",
        "options": [
          "normal",
          "vip"
        ]
      },
      {
        "key": "role_id",
        "label": "ตำแหน่งพนักงาน (ถ้าเป็น employee)",
        "type": "select",
        "optionsFrom": "roles"
      }
    ]
  },
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
        "optionsFrom": "categories"
      }
    ],
    "form": [
      {
        "key": "name",
        "label": "ชื่อสินค้า",
        "type": "text"
      },
      {
        "key": "categories",
        "label": "หมวดหมู่ (เลือกได้หลายอย่าง)",
        "type": "select",
        "multiple": true,
        "size": 4,
        "optionsFrom": "categories"
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
  "categories": {
    "label": "หมวดหมู่",
    "api": "/api/categories",
    "idKey": "category_id",
    "search": [
      {
        "key": "name",
        "label": "ชื่อหมวดหมู่",
        "type": "text"
      }
    ],
    "form": [
      {
        "key": "name",
        "label": "ชื่อหมวดหมู่",
        "type": "text"
      }
    ]
  },
  "orders": {
    "label": "ออเดอร์",
    "api": "/api/orders",
    "idKey": "order_id",
    "search": [
      {
        "key": "customer_id",
        "label": "รหัสลูกค้า",
        "type": "number"
      },
      {
        "key": "status",
        "label": "สถานะ",
        "type": "select",
        "options": [
          "",
          "pending",
          "waiting_paid",
          "paid",
          "delivered",
          "cancelled",
          "succeed",
          "shipped"
        ]
      }
    ],
    "form": [
      {
        "key": "customer_id",
        "label": "รหัสลูกค้า",
        "type": "number"
      },
      {
        "key": "address_token",
        "label": "ที่อยู่ลูกค้า",
        "type": "select",
        "optionsFrom": "addresses"
      },
      {
        "key": "order_date",
        "label": "วันที่สั่ง",
        "type": "date"
      },
      {
        "key": "total_amount",
        "label": "ยอดรวม",
        "type": "number"
      },
      {
        "key": "status",
        "label": "สถานะ",
        "type": "select",
        "options": [
          "pending",
          "waiting_paid",
          "paid",
          "delivered",
          "cancelled",
          "succeed",
          "shipped"
        ]
      }
    ]
  },
  "roles": {
    "label": "สิทธิ์",
    "api": "/api/roles",
    "idKey": "role_id",
    "search": [
      {
        "key": "name",
        "label": "ชื่อตำแหน่ง",
        "type": "text"
      }
    ],
    "form": [
      {
        "key": "name",
        "label": "ชื่อตำแหน่ง",
        "type": "text"
      }
    ]
  }
};

let current = Object.keys(ENTITIES)[0];
let editingId = null;
let CATEGORIES = [];
let ADDRESSES = [];
let ROLES = [];
const $ = (s) => document.querySelector(s);
function setStatus(el, msg, cls = "") { el.className = "status " + cls; el.textContent = msg; }
async function api(url, opts) { const res = await fetch(url, opts); return res.json(); }
async function loadCategories() { const r = await api("/api/categories"); CATEGORIES = r.ok ? r.data.map(c => c.name) : []; }
async function loadRoles() { const r = await api("/api/roles"); ROLES = r.ok ? r.data.map(x => ({ value: x.role_id, label: x.name })) : []; }
async function loadAddresses(userId) {
  const r = await api("/api/addresses" + (userId ? "?user_id=" + encodeURIComponent(userId) : ""));
  ADDRESSES = r.ok ? r.data.map(a => ({
    value: a.address_token,
    label: a.full_name + " — " + a.house_address + ", " + a.sub_district + ", " + a.district + ", " + a.province
  })) : [];
}

function fieldOptions(f, prefix) {
  if (f.optionsFrom === "categories") return prefix === "s_" ? ["", ...CATEGORIES] : CATEGORIES.slice();
  if (f.optionsFrom === "addresses") {
    if (prefix === "s_") return [{ value: "", label: "ทั้งหมด" }, ...ADDRESSES];
    return ADDRESSES.length ? ADDRESSES.slice() : [{ value: "", label: "— กรุณากรอกรหัสลูกค้าก่อน —" }];
  }
  if (f.optionsFrom === "roles") {
    if (prefix === "s_") return [{ value: "", label: "ทั้งหมด" }, ...ROLES];
    return ROLES.length ? [{ value: "", label: "— เลือกตำแหน่ง —" }, ...ROLES] : [{ value: "", label: "กำลังโหลด..." }];
  }
  return f.options;
}
function optionsHtml(opts, sel) {
  return opts.map(o => {
    const val = (o && typeof o === "object") ? o.value : o;
    const lab = (o && typeof o === "object") ? o.label : (o || "ทั้งหมด");
    return '<option value="' + val + '"' + (sel.includes(val) ? " selected" : "") + '>' + lab + '</option>';
  }).join("");
}
function fieldHtml(f, prefix, value = "") {
  let input;
  if (f.type === "select") {
    const sel = f.multiple ? (Array.isArray(value) ? value : (value ? [value] : [])) : [value];
    const attr = f.multiple ? ' multiple size="' + (f.size || 4) + '"' : '';
    input = '<select id="' + prefix + f.key + '"' + attr + '>' + optionsHtml(fieldOptions(f, prefix), sel) + '</select>';
  } else { input = '<input id="' + prefix + f.key + '" type="' + f.type + '" value="' + (value ?? "") + '">'; }
  return '<div class="field"><label>' + f.label + '</label>' + input + '</div>';
}
async function buildSearch() {
  const cfg = ENTITIES[current];
  $("#searchTitle").textContent = cfg.label;
  if (current === "products") await loadCategories();
  $("#searchFields").innerHTML = cfg.search.map(f => fieldHtml(f, "s_")).join("");
  $("#btnAdd").style.display = (current === "orders") ? "none" : "";
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
  const cols = Object.keys(rows[0]);
  head.innerHTML = cols.map(c => "<th>" + c + "</th>").join("") + "<th>จัดการ</th>";
  body.innerHTML = rows.map(row => {
    const id = row[ENTITIES[current].idKey];
    return "<tr>" + cols.map(c => "<td>" + (row[c] ?? "—") + "</td>").join("") +
      '<td><button class="btn sm" onclick="editRow(' + id + ')">แก้ไข</button> ' +
      '<button class="btn sm del" onclick="deleteRow(' + id + ')">ลบ</button></td></tr>';
  }).join("");
}
async function openForm(title, data = {}) {
  const cfg = ENTITIES[current];
  if (current === "customers") await loadRoles();
  if (current === "orders") {
    if (data.order_date) data.order_date = String(data.order_date).slice(0, 10);
    await loadAddresses(data.customer_id);
  }
  $("#modalTitle").textContent = title;
  $("#formFields").innerHTML = cfg.form.map(f => fieldHtml(f, "f_", data[f.key])).join("");
  $("#modal").classList.remove("hidden");
  if (current === "orders") bindOrderCustomerChange();
}
function bindOrderCustomerChange() {
  const uid = $("#f_customer_id");
  if (!uid) return;
  uid.addEventListener("change", async () => {
    const keep = $("#f_address_token") ? $("#f_address_token").value : "";
    await loadAddresses(uid.value);
    const selEl = $("#f_address_token");
    if (selEl) selEl.innerHTML = optionsHtml(fieldOptions({ optionsFrom: "addresses" }, "f_"), keep ? [keep] : []);
  });
}
function collectForm() {
  const cfg = ENTITIES[current], d = {};
  cfg.form.forEach(f => {
    const el = $("#f_" + f.key);
    d[f.key] = f.multiple ? Array.from(el.selectedOptions).map(o => o.value) : el.value;
  });
  return d;
}
async function editRow(id) {
  const cfg = ENTITIES[current];
  const r = await api(cfg.api + "/" + id);
  if (!r.ok) { alert((r.todo ? "🚧 " : "⚠️ ") + r.error); return; }
  editingId = id; await openForm("แก้ไขข้อมูล", r.data);
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
$("#btnSearch").onclick = doSearch;
$("#btnClear").onclick = () => buildSearch();
$("#btnAdd").onclick = () => { editingId = null; openForm("เพิ่มข้อมูลใหม่"); };
$("#btnSave").onclick = save;
$("#btnCancel").onclick = () => $("#modal").classList.add("hidden");
buildSearch();
setStatus($("#status"), 'กด "ค้นหา" เพื่อแสดงข้อมูล');

// ---- สลับโหมด พนักงาน / ลูกค้า ----
document.querySelectorAll(".mode-btn").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll(".mode-btn").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  const isEmp = b.dataset.mode === "employee";
  $("#employeeView").classList.toggle("hidden", !isEmp);
  $("#customerView").classList.toggle("hidden", isEmp);
  $("#mainNav").classList.toggle("hidden", !isEmp);
  $("#modal").classList.add("hidden");
}));
