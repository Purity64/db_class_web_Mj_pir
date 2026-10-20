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
  // report_summary() คืน dict {ชื่อการ์ด: ตัวเลข} → 1 คีย์ = 1 การ์ด
  const r = await api("/api/reports/summary");
  const box = $("#summary");
  if (!r.ok) { box.innerHTML = '<div style="grid-column:1/-1" class="status ' + (r.todo ? "todo" : "err") + '">' + (r.todo ? "🚧 " : "⚠️ ") + r.error + '</div>'; return; }
  box.innerHTML = Object.entries(r.data || {}).map(([label, num]) =>
    '<div class="metric"><div class="metric-num">' + (num ?? "—") + '</div><div class="metric-label">' + label + '</div></div>').join("");
}
async function loadAll() {
  loadSummary();
  // สร้างกล่องรายงานตามรายการ REPORTS ใน db.py
  const list = await api("/api/reports");
  for (const rep of (list.data || [])) {
    const id = "rep_" + rep.key.replace(/\W/g, "_");
    const sec = document.createElement("section");
    sec.className = "card";
    sec.innerHTML = '<h3>' + rep.title + '</h3><div id="' + id + '_status" class="status"></div>' +
      '<div class="table-wrap"><table id="' + id + '_table"><thead></thead><tbody></tbody></table></div>';
    $("#reports").appendChild(sec);
    fillTable("#" + id + "_table", "#" + id + "_status", await api("/api/reports/" + rep.key));
  }
}
loadAll();
