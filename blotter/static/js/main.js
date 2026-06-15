// ===== Theme toggle =====
(function () {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
  window.toggleTheme = function () {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  };
})();

// ===== Smooth page transitions =====
document.addEventListener("click", function (e) {
  const a = e.target.closest("a[data-link]");
  if (!a) return;
  const href = a.getAttribute("href");
  if (!href || href === "#" || href.startsWith("#") || a.target === "_blank") return;
  e.preventDefault();
  const page = document.querySelector(".page");
  if (page) page.classList.add("page-leave");
  setTimeout(() => (window.location.href = href), 180);
});

// ===== Modal =====
window.openModal = function (id) { document.getElementById(id)?.classList.add("open"); };
window.closeModal = function (id) { document.getElementById(id)?.classList.remove("open"); };
document.addEventListener("click", function (e) {
  if (e.target.classList && e.target.classList.contains("modal-backdrop")) {
    e.target.classList.remove("open");
  }
});

// ===== Report detail modal: render ALL fields dynamically =====
function escapeHTML(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

window.viewReport = async function (id) {
  try {
    const res = await fetch(`/admin/report/${id}`);
    if (!res.ok) return;
    const r = await res.json();

    document.getElementById("m-status").textContent = r.status || "Pending";
    document.getElementById("m-type").textContent = r.type_label || "Report";
    document.getElementById("m-meta").textContent = `${r.id} · ${r.date}`;

    const dot = document.getElementById("m-dot");
    dot.className = "status-dot status-" + (r.status || "pending").toLowerCase().replace(/\s+/g, "-");

    const host = document.getElementById("m-sections");
    host.innerHTML = "";
    const fields = r.fields || {};
    Object.keys(fields).forEach(section => {
      const items = fields[section] || {};
      const rows = Object.keys(items).map(k => {
        const v = items[k];
        
        // 1. Set the default plain-text display fallback
        let displayValue = escapeHTML(v) || "—";
        
        // 2. Check if the value is an image path from the server
        if (v && typeof v === 'string' && v.startsWith('/static/uploads/')) {
          displayValue = `
            <a href="${v}" target="_blank" title="Click to view full image">
              <img src="${v}" style="max-width: 100%; max-height: 200px; border-radius: 8px; border: 1px solid var(--border-strong); margin-top: 6px; display: block;" alt="Attachment Preview">
            </a>`;
        }

        return `<div><div class="field-label">${escapeHTML(k)}:</div>
                <div class="field-box">${displayValue}</div></div>`;
      }).join("");
      
      host.insertAdjacentHTML("beforeend",
        `<h4>${escapeHTML(section)}</h4><div class="modal-grid">${rows}</div>`);
    });

    openModal("reportModal");
  } catch (err) { console.error(err); }
};

// ===== Show/hide fields on criminal form =====
window.toggleRespondent = function (val) {
  const y = document.getElementById("respondent-yes");
  const n = document.getElementById("respondent-no");
  if (y) y.style.display = val === "yes" ? "block" : "none";
  if (n) n.style.display = val === "no" ? "block" : "none";
};

// ===== Notification dropdown (admin pages) =====
(function () {
  const btn = document.getElementById("notifBtn");
  const pop = document.getElementById("notifPop");
  const badge = document.getElementById("notifBadge");
  const list = document.getElementById("notifList");
  if (!btn || !pop) return;

  async function loadNotifs() {
    try {
      const res = await fetch("/admin/notifications");
      const data = await res.json();
      if (badge) {
        if (data.unread > 0) { badge.hidden = false; badge.textContent = data.unread; }
        else { badge.hidden = true; }
      }
      list.innerHTML = (data.items || []).map(n => `
        <div class="notif-card">
          <div class="notif-title">${escapeHTML(n.title)}</div>
          <div class="notif-reporter"><strong>${escapeHTML(n.reporter)}</strong></div>
          <div class="notif-incident">${escapeHTML(n.incident_type)}</div>
          <div class="notif-meta">${escapeHTML(n.created)}</div>
        </div>`).join("") || `<div style="font-size:13px;color:var(--text-muted);padding:8px">No notifications.</div>`;
    } catch (e) { /* ignore */ }
  }

  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    pop.hidden = !pop.hidden;
    if (!pop.hidden) {
      await loadNotifs();
      fetch("/admin/notifications/seen", {method:"POST"}).then(() => {
        if (badge) badge.hidden = true;
      });
    }
  });
  document.addEventListener("click", (e) => {
    if (!pop.contains(e.target) && e.target !== btn) pop.hidden = true;
  });

  // Poll every 15s so new reports show up without manual refresh
  setInterval(loadNotifs, 15000);
  loadNotifs();
})();
