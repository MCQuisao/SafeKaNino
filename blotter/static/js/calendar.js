// Calendar widget for Mediation
(function () {
  const root = document.getElementById("calendar-root");
  if (!root) return;
  const hearings = window.__HEARINGS__ || {};

  const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  const weekdays = ["Sun","Mon","Tues","Wed","Thu","Fri","Sat"];

  const today = new Date();
  let current = new Date(today.getFullYear(), today.getMonth(), 1);
  // Default-select today, or first date that has hearings
  let selected = ymd(today.getFullYear(), today.getMonth(), today.getDate());
  const keys = Object.keys(hearings);
  if (keys.length && !hearings[selected]) selected = keys[0];

  function ymd(y, m, d) {
    return `${y}-${String(m+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
  }

  function render() {
    const y = current.getFullYear(), m = current.getMonth();
    const first = new Date(y, m, 1);
    const startDay = first.getDay();
    const daysInMonth = new Date(y, m+1, 0).getDate();

    let html = `
      <div class="cal-head">
        <div class="cal-title">${monthNames[m]} ${y}</div>
        <div class="cal-nav">
          <button onclick="window.__cal.prev()">‹</button>
          <button onclick="window.__cal.next()">›</button>
        </div>
      </div>
      <div class="weekdays">${weekdays.map(w => `<div>${w}</div>`).join("")}</div>
      <div class="days">`;
    for (let i = 0; i < startDay; i++) html += `<div class="day muted"></div>`;
    for (let d = 1; d <= daysInMonth; d++) {
      const key = ymd(y, m, d);
      const items = hearings[key] || [];
      const dots = items.map(h => `<span class="dot ${h.status === 'Settled' ? 'settled' : 'scheduled'}"></span>`).join("");
      const sel = key === selected ? "selected" : "";
      html += `<div class="day ${sel}" onclick="window.__cal.select('${key}')"><div>${d}</div><div class="dots">${dots}</div></div>`;
    }
    const filled = startDay + daysInMonth;
    const trailing = (7 - (filled % 7)) % 7;
    for (let i = 1; i <= trailing; i++) html += `<div class="day muted"><div>${i}</div></div>`;
    html += `</div>
      <div class="legend">
        <span><span class="dot settled"></span> Settled</span>
        <span><span class="dot scheduled"></span> Scheduled / In Progress</span>
      </div>`;
    root.innerHTML = html;
    renderHearings();
  }

  function renderHearings() {
    const panel = document.getElementById("hearings-list");
    if (!panel) return;
    const items = hearings[selected] || [];
    const [yy, mm, dd] = selected.split("-");
    document.getElementById("hearings-title").textContent =
      `Hearings for ${monthNames[+mm-1]} ${+dd}, ${yy}`;
    if (!items.length) {
      panel.innerHTML = `<p style="color:var(--text-muted);font-size:14px">No hearings scheduled.</p>`;
      return;
    }
    panel.innerHTML = items.map(h => {
      const meta = `${h.case_id} — ${h.complainant}`;
      const cls = h.status === 'Settled' ? 'settled' : 'scheduled';
      return `
      <div class="hearing-item">
        <div class="hearing-row">
          <div class="hearing-time">${h.time}</div>
          <div class="hearing-body">
            <div>Case ID: <strong>${h.case_id}</strong>
              <span class="hearing-status"><span class="dot ${cls}"></span> ${h.status}</span>
            </div>
            <div>Complainant: ${h.complainant}</div>
            <div>Incident: ${h.incident || ''}</div>
            <div>Mediator: ${h.mediator}</div>
            <div style="margin-top:8px">
              <button class="btn btn-secondary" onclick="openStatus('${h.id}', '${meta.replace(/'/g,"\\'")}')">Update Status</button>
            </div>
          </div>
        </div>
      </div>`;
    }).join("");
  }

  window.__cal = {
    prev() { current = new Date(current.getFullYear(), current.getMonth() - 1, 1); render(); },
    next() { current = new Date(current.getFullYear(), current.getMonth() + 1, 1); render(); },
    select(k) { selected = k; render(); },
  };
  render();
})();
