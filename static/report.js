// ============================================================
//  report.js  —  ตรรกะหน้ารายงาน (ทำให้เสร็จแล้ว ★)
// ============================================================
const $ = (s) => document.querySelector(s);
async function api(url) { return (await fetch(url)).json(); }
function fillTable(tableSel, statusSel, r) {
  const t = $(tableSel), st = $(statusSel);
  const thead = t.querySelector("thead"), tbody = t.querySelector("tbody");
  thead.innerHTML = ""; tbody.innerHTML = "";
  if (!r.ok) { st.className = "status " + (r.todo ? "todo" : "err"); st.textContent = (r.todo ? "🚧 " : "⚠️ ") + r.error; return; }
  const rows = r.data || [];
  if (!rows.length) { st.className = "status"; st.textContent = "ไม่มีข้อมูล"; return; }
  st.textContent = "";
  const cols = Object.keys(rows[0]);
  thead.innerHTML = "<tr>" + cols.map(c => "<th>" + c + "</th>").join("") + "</tr>";
  tbody.innerHTML = rows.map(row => "<tr>" + cols.map(c => "<td>" + (row[c] ?? "—") + "</td>").join("") + "</tr>").join("");
}
async function loadSummary() {
  const r = await api("/api/reports/summary");
  if (!r.ok) return;
  const d = r.data || {};
  if (d.customers !== undefined) $("#m_cus").textContent = d.customers;
  if (d.products !== undefined) $("#m_prd").textContent = d.products;
  if (d.orders !== undefined) $("#m_ord").textContent = d.orders;
  if (d.reviews !== undefined) $("#m_rev").textContent = d.reviews;
}
async function loadAll() {
  loadSummary();
  fillTable("#bestTable", "#bestStatus", await api("/api/reports/best-selling"));
  fillTable("#topcusTable", "#topcusStatus", await api("/api/reports/top-customers"));
  fillTable("#ratedTable", "#ratedStatus", await api("/api/reports/high-rated"));
}
loadAll();
