/* ============================================================
   WAHABIX MEDICARE SOLUTION — Core JavaScript Engine
   Developed by: WAHABIX (Shah Abdul Wahab) © 2026
   ============================================================ */

'use strict';

/* ── SILENT PRINT ─────────────────────────────────────────────
   Prints a URL (token slips, receipts, etc.) via a hidden iframe
   instead of opening a new tab. Nothing to switch back from or
   close manually — the print dialog appears over the current page
   and the iframe cleans itself up afterwards. */
function wmsSilentPrint(url) {
  const iframe = document.createElement('iframe');
  iframe.style.position = 'fixed';
  iframe.style.top = '-9999px';
  iframe.style.left = '-9999px';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = '0';
  iframe.src = url;
  document.body.appendChild(iframe);

  iframe.onload = function () {
    setTimeout(function () {
      try {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
      } catch (e) {
        // Fallback: some browsers block cross-context printing from a
        // hidden iframe — fall back to a normal new-tab print instead.
        window.open(url, '_blank');
      }
    }, 300);
  };

  // Clean up the iframe a while after printing so it doesn't linger.
  setTimeout(function () {
    if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
  }, 60000);
}

/* ── THEME ─────────────────────────────────────────────────
   Theme is now platform-wide, set only by Super Admin
   (apps.core.models.PlatformSettings) and rendered server-side as
   <html data-theme="...">. There is intentionally no client-side
   override here anymore — no localStorage, no per-user picker. */

/* ── TOAST SYSTEM ─────────────────────────────────────────── */
const WMSToast = {
  container: null,

  init() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      document.body.appendChild(this.container);
    }
  },

  show(message, type = 'success', duration = 3500) {
    const icons = { success:'✅', error:'❌', warning:'⚠️', info:'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || '📢'}</span><span>${message}</span>`;
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      toast.style.transition = 'all .3s';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  success(msg) { this.show(msg, 'success'); },
  error(msg)   { this.show(msg, 'error'); },
  warning(msg) { this.show(msg, 'warning'); },
  info(msg)    { this.show(msg, 'info'); }
};

/* ── CONFIRM DIALOG ───────────────────────────────────────── */
const WMSConfirm = {
  show(message, onConfirm, danger = true) {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position:fixed;inset:0;background:rgba(0,0,0,.6);
      z-index:9000;display:flex;align-items:center;justify-content:center;
      backdrop-filter:blur(4px);animation:fadeIn .2s ease;
    `;
    overlay.innerHTML = `
      <div style="background:var(--bg-card);border:1px solid var(--border);
        border-radius:var(--radius);padding:28px;max-width:380px;width:90%;
        box-shadow:var(--shadow);animation:scaleIn .2s ease;">
        <div style="font-size:32px;text-align:center;margin-bottom:12px;">
          ${danger ? '⚠️' : '❓'}
        </div>
        <div style="font-size:15px;font-weight:700;color:var(--text-h);
          text-align:center;margin-bottom:8px;">Are you sure?</div>
        <div style="font-size:13.5px;color:var(--text-muted);text-align:center;
          margin-bottom:24px;">${message}</div>
        <div style="display:flex;gap:10px;justify-content:center;">
          <button id="wms-confirm-no" style="padding:9px 20px;border-radius:var(--radius-sm);
            border:1px solid var(--border);background:var(--bg-hover);
            color:var(--text-muted);cursor:pointer;font-size:13.5px;font-weight:600;font-family:inherit;">
            Cancel
          </button>
          <button id="wms-confirm-yes" style="padding:9px 20px;border-radius:var(--radius-sm);
            border:none;background:${danger ? 'var(--danger)' : 'var(--accent)'};
            color:${danger ? '#fff' : '#000'};cursor:pointer;font-size:13.5px;font-weight:600;font-family:inherit;">
            Confirm
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    overlay.querySelector('#wms-confirm-yes').onclick = () => { overlay.remove(); onConfirm(); };
    overlay.querySelector('#wms-confirm-no').onclick  = () => overlay.remove();
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  }
};

/* ── SEARCH FILTER ────────────────────────────────────────── */
function wmsTableSearch(inputId, tableId, cols = []) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.addEventListener('input', () => {
    const q = input.value.toLowerCase().trim();
    const rows = document.querySelectorAll(`#${tableId} tbody tr`);
    let visible = 0;
    rows.forEach(row => {
      const cells = cols.length
        ? cols.map(i => row.cells[i]?.textContent || '').join(' ')
        : row.textContent;
      const match = cells.toLowerCase().includes(q);
      row.style.display = match ? '' : 'none';
      if (match) visible++;
    });
    const counter = document.getElementById(`${tableId}-count`);
    if (counter) counter.textContent = `${visible} results`;
  });
}

/* ── MOBILE SIDEBAR ───────────────────────────────────────── */
function toggleSidebar() {
  document.querySelector('.wms-sidebar')?.classList.toggle('open');
  document.getElementById('sidebar-backdrop')?.classList.toggle('open');
}
function closeSidebar() {
  document.querySelector('.wms-sidebar')?.classList.remove('open');
  document.getElementById('sidebar-backdrop')?.classList.remove('open');
}

/* ── AUTO-DISMISS ALERTS ──────────────────────────────────── */
function autoDismissAlerts(delay = 4000) {
  document.querySelectorAll('.alert[data-auto-dismiss]').forEach(el => {
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transition = 'opacity .4s';
      setTimeout(() => el.remove(), 400);
    }, delay);
  });
}

/* ── STAT COUNTER ANIMATION ───────────────────────────────── */
function animateCounters() {
  document.querySelectorAll('.stat-num[data-target]').forEach(el => {
    const target = parseInt(el.dataset.target);
    if (isNaN(target)) return;
    let current = 0;
    const step = Math.ceil(target / 40);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current.toLocaleString();
      if (current >= target) clearInterval(timer);
    }, 30);
  });
}

/* ── FORM VALIDATION ──────────────────────────────────────── */
function wmsValidateForm(formId) {
  const form = document.getElementById(formId);
  if (!form) return true;
  let valid = true;
  form.querySelectorAll('[required]').forEach(field => {
    if (!field.value.trim()) {
      field.style.borderColor = 'var(--danger)';
      field.style.boxShadow = '0 0 0 3px rgba(239,68,68,.12)';
      valid = false;
      field.addEventListener('input', () => {
        field.style.borderColor = '';
        field.style.boxShadow = '';
      }, { once: true });
    }
  });
  if (!valid) WMSToast.error('Please fill all required fields.');
  return valid;
}

/* ── INIT ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  WMSToast.init();
  autoDismissAlerts();
  animateCounters();

  // Confirm links
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      const href = el.href || el.dataset.href;
      const msg  = el.dataset.confirm;
      const isDanger = el.dataset.danger !== 'false';
      const form = el.closest('form');
      WMSConfirm.show(msg, () => {
        if (href) {
          window.location.href = href;
        } else if (el.type === 'submit' && form) {
          // Previously this branch didn't exist: a submit <button
          // data-confirm="..."> would preventDefault(), the person would
          // click "Confirm" in the dialog, and then... nothing — the form
          // never actually submitted. This silently broke Lab result
          // saving, payroll generation, and insurance claim actions.
          form.submit();
        } else if (el.type === 'submit') {
          el.form?.submit();
        }
      }, isDanger);
    });
  });

  // Mobile hamburger
  document.getElementById('hamburger')?.addEventListener('click', toggleSidebar);
  document.getElementById('sidebar-backdrop')?.addEventListener('click', closeSidebar);
  if (window.innerWidth <= 768) {
    document.querySelectorAll('.wms-sidebar .nav-link').forEach(link => {
      link.addEventListener('click', closeSidebar);
    });
  }
});

/* CSS for confirm animations */
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeIn  { from{opacity:0} to{opacity:1} }
  @keyframes scaleIn { from{transform:scale(.9);opacity:0} to{transform:scale(1);opacity:1} }
`;
document.head.appendChild(style);
