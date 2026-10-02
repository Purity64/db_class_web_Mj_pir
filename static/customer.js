// ============================================================
//  customer.js — โหมดลูกค้า: ที่อยู่ + สร้างออเดอร์ + ประวัติสั่งซื้อ
// ============================================================
(function () {
  const $ = (s) => document.querySelector(s);
  const api = async (url, opts) => (await fetch(url, opts)).json();
  const STATUS_TH = {
    pending: "รอตรวจสอบ",
    waiting_paid: "รอชำระเงิน",
    paid: "ชำระแล้ว",
    delivered: "ส่งถึงแล้ว",
    shipped: "จัดส่งแล้ว",
    succeed: "สำเร็จ",
    cancelled: "ยกเลิก"
  };
  const ADDR_FIELDS = [
    ["full_name", "ชื่อผู้รับ", "text"],
    ["phone", "เบอร์โทร", "text"],
    ["house_address", "บ้านเลขที่", "text"],
    ["moo", "หมู่", "text"],
    ["soi", "ซอย", "text"],
    ["road", "ถนน", "text"],
    ["sub_district", "ตำบล/แขวง", "text"],
    ["district", "อำเภอ/เขต", "text"],
    ["province", "จังหวัด", "text"],
    ["postal_code", "รหัสไปรษณีย์", "number"],
    ["note", "หมายเหตุ", "text"]
  ];

  let CUSTOMER_ID = null;
  let ADDRESSES = [];
  let PRODUCTS = [];

  function setStatus(el, msg, cls = "") { el.className = "status " + cls; el.textContent = msg; }

  async function loadCustomers() {
    const r = await api("/api/customers?role=customer");
    if (!r.ok) { setStatus($("#cpOrderStatus"), r.error, "err"); return; }
    $("#cpCustomer").innerHTML = '<option value="">— เลือกลูกค้า —</option>' +
      r.data.map(c => '<option value="' + c.user_id + '">' + c.user_id + " — " + c.name + "</option>").join("");
  }

  async function loadWallet(id) {
    const r = await api("/api/customers/" + id);
    if (!r.ok) { $("#cpMoney").textContent = "—"; $("#cpTier").textContent = "—"; return; }
    $("#cpMoney").textContent = Number(r.data.money || 0).toFixed(2);
    const tier = r.data.tier || "normal";
    const el = $("#cpTier");
    el.textContent = tier.toUpperCase();
    el.className = "badge " + (tier === "vip" ? "succeed" : "pending");
  }

  async function loadAddr(id) {
    const r = await api("/api/addresses?user_id=" + encodeURIComponent(id));
    ADDRESSES = r.ok ? r.data : [];
    $("#cpAddrTable tbody").innerHTML = ADDRESSES.map(a =>
      "<tr><td>" + a.full_name + "</td><td>" + a.house_address + "</td><td>" + a.sub_district +
      "</td><td>" + a.district + "</td><td>" + a.province + "</td><td>" + (a.phone ?? "—") + "</td></tr>"
    ).join("");
    setStatus($("#cpAddrStatus"), ADDRESSES.length ? "พบ " + ADDRESSES.length + " ที่อยู่" : "ยังไม่มีที่อยู่");
  }

  async function loadOrders(id) {
    const r = await api("/api/orders?customer_id=" + encodeURIComponent(id));
    if (!r.ok) { $("#cpOrderTable tbody").innerHTML = ""; setStatus($("#cpOrderStatus"), r.error, "err"); return; }
    $("#cpOrderTable tbody").innerHTML = r.data.map(o =>
      "<tr><td>" + o.order_id + "</td><td>" + String(o.order_date || "").slice(0, 10) + "</td><td>" +
      Number(o.total_amount).toFixed(2) + "</td><td><span class='badge " + o.status + "'>" +
      (STATUS_TH[o.status] || o.status) + "</span></td><td>" + o.address_token + "</td></tr>"
    ).join("");
    setStatus($("#cpOrderStatus"), r.data.length ? "พบ " + r.data.length + " ออเดอร์" : "ยังไม่มีออเดอร์");
  }

  async function refresh() {
    CUSTOMER_ID = $("#cpCustomer").value || null;
    if (!CUSTOMER_ID) { return; }
    await Promise.all([loadWallet(CUSTOMER_ID), loadAddr(CUSTOMER_ID), loadOrders(CUSTOMER_ID)]);
  }

  // ---------- เพิ่มที่อยู่ ----------
  function openAddrModal() {
    if (!CUSTOMER_ID) { alert("กรุณาเลือกลูกค้าก่อน"); return; }
    $("#addrFields").innerHTML = ADDR_FIELDS.map(([k, l, t]) =>
      '<div class="field"><label>' + l + '</label><input id="af_' + k + '" type="' + t + '"></div>'
    ).join("");
    $("#addrModal").classList.remove("hidden");
  }

  async function saveAddress() {
    const d = { user_id: CUSTOMER_ID };
    ADDR_FIELDS.forEach(([k]) => { d[k] = $("#af_" + k).value; });
    const r = await api("/api/addresses", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(d)
    });
    if (!r.ok) { alert(r.error); return; }
    $("#addrModal").classList.add("hidden");
    await loadAddr(CUSTOMER_ID);
  }

  // ---------- สร้างออเดอร์ ----------
  async function loadProducts() {
    if (PRODUCTS.length) return;
    const r = await api("/api/products");
    PRODUCTS = r.ok ? r.data.filter(p => p.isOpen === 1 || p.isOpen === true) : [];
  }

  function addItemRow() {
    const row = document.createElement("div");
    row.className = "item-row";
    row.innerHTML =
      '<select class="omProduct">' +
      PRODUCTS.map(p => '<option value="' + p.product_id + '" data-price="' + p.price + '">' +
        p.product_id + " — " + p.name + " (" + Number(p.price).toFixed(2) + ")</option>").join("") +
      '</select><input class="omQty" type="number" min="1" value="1">' +
      '<button class="btn sm del omRemove" type="button">ลบ</button>';
    $("#omItems").appendChild(row);
    row.querySelector(".omProduct").addEventListener("change", calcTotal);
    row.querySelector(".omQty").addEventListener("input", calcTotal);
    row.querySelector(".omRemove").addEventListener("click", () => { row.remove(); calcTotal(); });
    calcTotal();
  }

  function calcTotal() {
    let total = 0;
    document.querySelectorAll("#omItems .item-row").forEach(row => {
      const opt = row.querySelector(".omProduct").selectedOptions[0];
      const qty = parseInt(row.querySelector(".omQty").value || "0", 10);
      if (opt && qty > 0) total += Number(opt.dataset.price) * qty;
    });
    $("#omTotal").textContent = total.toFixed(2);
  }

  async function openOrderModal() {
    if (!CUSTOMER_ID) { alert("กรุณาเลือกลูกค้าก่อน"); return; }
    if (!ADDRESSES.length) { alert("ลูกค้ายังไม่มีที่อยู่ กรุณาเพิ่มที่อยู่ก่อน"); return; }
    await loadProducts();
    $("#omAddress").innerHTML = ADDRESSES.map(a =>
      '<option value="' + a.address_token + '">' + a.full_name + " — " + a.house_address + ", " +
      a.sub_district + ", " + a.district + ", " + a.province + "</option>").join("");
    $("#omItems").innerHTML = "";
    addItemRow();
    $("#orderModal").classList.remove("hidden");
  }

  async function saveOrder() {
    const items = [];
    document.querySelectorAll("#omItems .item-row").forEach(row => {
      const pid = row.querySelector(".omProduct").value;
      const qty = parseInt(row.querySelector(".omQty").value || "0", 10);
      if (pid && qty > 0) items.push({ product_id: pid, quantity: qty });
    });
    if (!items.length) { alert("กรุณาเพิ่มรายการสินค้าอย่างน้อย 1 รายการ"); return; }
    const r = await api("/api/orders/customer", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id: CUSTOMER_ID, address_token: $("#omAddress").value, items })
    });
    if (!r.ok) { alert(r.error); return; }
    $("#orderModal").classList.add("hidden");
    await loadOrders(CUSTOMER_ID);
  }

  // ---------- bind ----------
  $("#cpCustomer").addEventListener("change", refresh);
  $("#cpBtnAddAddress").addEventListener("click", openAddrModal);
  $("#btnAddrSave").addEventListener("click", saveAddress);
  $("#btnAddrCancel").addEventListener("click", () => $("#addrModal").classList.add("hidden"));
  $("#cpBtnNewOrder").addEventListener("click", openOrderModal);
  $("#omAddItem").addEventListener("click", addItemRow);
  $("#btnOrderSave").addEventListener("click", saveOrder);
  $("#btnOrderCancel").addEventListener("click", () => $("#orderModal").classList.add("hidden"));

  loadCustomers();
})();
