/* ═══════════════════════════════════════════════════════════
   SHIV SHANKAR DOOR — Dashboard JavaScript
   ═══════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Sidebar toggle (mobile) ───────────────────────────────
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');

  if (toggle && sidebar) {
    toggle.addEventListener('click', () => {
      const isOpen = sidebar.classList.contains('open');
      sidebar.classList.toggle('open', !isOpen);
      overlay.style.display = isOpen ? 'none' : 'block';
    });
  }

  window.closeSidebar = function () {
    sidebar && sidebar.classList.remove('open');
    overlay && (overlay.style.display = 'none');
  };

  // ── Auto-dismiss alerts ───────────────────────────────────
  document.querySelectorAll('.dash-alert').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transform = 'translateX(20px)';
      alert.style.transition = 'opacity 0.3s, transform 0.3s';
      setTimeout(() => alert.remove(), 350);
    }, 5000);
  });

  // ── Confirm delete modal exposed functions ────────────────
  window.confirmDelete = function (id, name) {
    const modal = document.getElementById('deleteModal');
    const nameEl = document.getElementById('deleteProductName');
    const form = document.getElementById('deleteForm');
    if (!modal || !nameEl || !form) return;
    nameEl.textContent = '"' + name + '"';
    form.action = '/dashboard/products/delete/' + id + '/';
    modal.classList.add('open');
  };

  window.closeDeleteModal = function () {
    const modal = document.getElementById('deleteModal');
    if (modal) modal.classList.remove('open');
  };

  // Close modal on Escape key
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      window.closeDeleteModal && window.closeDeleteModal();
      window.closeSidebar && window.closeSidebar();
    }
  });

  // ── Price inputs: format display ─────────────────────────
  document.querySelectorAll('input[name="price_min"], input[name="price_max"]').forEach(input => {
    input.addEventListener('blur', () => {
      const v = parseInt(input.value.replace(/,/g, ''));
      if (!isNaN(v)) {
        // Keep the raw number value for form submit but show formatted hint
        const hint = input.closest('.form-group')?.querySelector('.form-hint');
        if (hint && v > 0) {
          hint.textContent = '₹' + v.toLocaleString('en-IN');
        }
      }
    });
  });

  // ── Search: submit on Enter ───────────────────────────────
  document.querySelectorAll('.filter-search').forEach(input => {
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        input.closest('form')?.submit();
      }
    });
  });

  // ── Product tile hover effects ────────────────────────────
  document.querySelectorAll('.product-tile').forEach(tile => {
    tile.addEventListener('mouseenter', () => {
      tile.querySelector('img')?.style && (tile.querySelector('img').style.transform = 'scale(1.04)');
    });
    tile.addEventListener('mouseleave', () => {
      tile.querySelector('img')?.style && (tile.querySelector('img').style.transform = 'scale(1)');
    });
  });

  // ── Stat card count-up animation ─────────────────────────
  document.querySelectorAll('.stat-card__value').forEach(el => {
    const target = parseInt(el.textContent);
    if (isNaN(target) || target === 0) return;
    let current = 0;
    const step = Math.max(1, Math.floor(target / 30));
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 30);
  });

});
