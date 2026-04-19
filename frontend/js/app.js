/* ── API Base ── */
const API = 'http://localhost:5000/api';

function getToken() { return localStorage.getItem('token'); }
function getUser()  { return JSON.parse(localStorage.getItem('user') || 'null'); }
function setAuth(token, user) {
  localStorage.setItem('token', token);
  localStorage.setItem('user', JSON.stringify(user));
}
function clearAuth() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}
function isLoggedIn() { return !!getToken(); }

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = 'Bearer ' + token;

  const res = await fetch(API + path, { ...options, headers });
  if (res.status === 401) {
    clearAuth();
    window.location.href = '/login';
    return;
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.message || 'HTTP ' + res.status);
  return data;
}

/* ── Toast ── */
function showToast(msg, type = 'info', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.innerHTML = '<span style="font-weight:700;font-size:15px">' + (icons[type] || '•') + '</span>' + msg;
  container.appendChild(t);
  setTimeout(() => {
    t.style.animation = 'slideIn .2s ease reverse';
    setTimeout(() => t.remove(), 200);
  }, duration);
}

/* ── Sidebar & Layout ── */
function renderLayout(activePage) {
  if (!isLoggedIn()) { window.location.href = '/login'; return; }
  const user = getUser();
  const role = user?.role || 'student';

  const allNav = [
    { id: 'dashboard',  icon: '⬛', label: 'Dashboard',       roles: ['admin','teacher','student'] },
    { id: 'students',   icon: '👥', label: 'My Profile',      roles: ['student'] },
    { id: 'students',   icon: '👥', label: 'Students',        roles: ['admin','teacher'] },
    { id: 'subjects',   icon: '📚', label: 'Subjects',        roles: ['admin','teacher'] },
    { id: 'attendance', icon: '📷', label: 'Take Attendance', roles: ['admin','teacher'] },
    { id: 'sessions',   icon: '📋', label: 'Sessions',        roles: ['admin','teacher'] },
    { id: 'reports',    icon: '📊', label: 'Reports',         roles: ['admin','teacher','student'] },
    { id: 'enroll',     icon: '🔍', label: 'Face Enroll',     roles: ['admin','teacher','student'] },
  ];
  const nav = allNav.filter(n => n.roles.includes(role));

  const navHTML = nav.map(n =>
    '<button class="nav-link ' + (n.id === activePage ? 'active' : '') + '" onclick="window.location.href=\'/' + n.id + '\'">'
    + '<span class="icon">' + n.icon + '</span>' + n.label
    + '</button>'
  ).join('');

  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.innerHTML =
      '<div class="sidebar-logo">'
      + '<div class="logo-icon">👁</div>'
      + '<div class="logo-text">FaceAttend</div>'
      + '</div>'
      + '<nav class="sidebar-nav">' + navHTML + '</nav>'
      + '<div class="sidebar-user">'
      + '<div class="user-card">'
      + '<div class="user-avatar">' + (user?.full_name || 'U')[0].toUpperCase() + '</div>'
      + '<div class="user-info">'
      + '<div class="user-name">' + (user?.full_name || 'User') + '</div>'
      + '<div class="user-role">' + (user?.role || '') + '</div>'
      + '</div></div>'
      + '<button class="btn btn-secondary btn-sm btn-logout w-full mt-4" onclick="logout()">Sign out</button>'
      + '</div>';
  }
}

function logout() {
  clearAuth();
  window.location.href = '/login';
}

/* ── Modal helpers ── */
function openModal(id)  { document.getElementById(id).style.display = 'flex'; }
function closeModal(id) { document.getElementById(id).style.display = 'none'; }

/* ── Format helpers ── */
function statusBadge(status) {
  const map = { present: 'badge-present', absent: 'badge-absent', late: 'badge-late' };
  return '<span class="badge ' + (map[status] || 'badge-absent') + '">' + status + '</span>';
}

/* ── Bar Chart (Canvas) ── */
function drawBarChart(canvasId, labels, values, color) {
  color = color || '#4f46e5';
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const pad = { top: 20, right: 20, bottom: 40, left: 40 };
  const max = Math.max(...values, 1);

  ctx.clearRect(0, 0, W, H);

  ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (H - pad.top - pad.bottom) * (1 - i / 4);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    ctx.fillStyle = '#94a3b8'; ctx.font = '11px Inter,sans-serif'; ctx.textAlign = 'right';
    ctx.fillText(Math.round(max * i / 4), pad.left - 6, y + 4);
  }

  const barW = (W - pad.left - pad.right) / labels.length * 0.6;
  const gap  = (W - pad.left - pad.right) / labels.length;

  labels.forEach((label, i) => {
    const x    = pad.left + gap * i + gap * 0.2;
    const barH = (values[i] / max) * (H - pad.top - pad.bottom);
    const y    = H - pad.bottom - barH;

    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(x, y, barW, barH, [4, 4, 0, 0]);
    ctx.fill();

    ctx.fillStyle = '#64748b'; ctx.font = '11px Inter,sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(label, x + barW / 2, H - pad.bottom + 16);
    ctx.fillStyle = '#1e293b'; ctx.font = 'bold 11px Inter,sans-serif';
    if (barH > 20) ctx.fillText(Math.round(values[i]), x + barW / 2, y - 6);
  });
}

/* ── Donut Chart (Canvas) ── */
function drawDonutChart(canvasId, slices) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx   = canvas.getContext('2d');
  const cx    = canvas.width / 2, cy = canvas.height / 2;
  const R     = Math.min(cx, cy) - 20, r = R * 0.55;
  const total = slices.reduce((s, sl) => s + sl.value, 0) || 1;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  let angle = -Math.PI / 2;

  slices.forEach(sl => {
    const sweep = (sl.value / total) * 2 * Math.PI;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, R, angle, angle + sweep);
    ctx.closePath();
    ctx.fillStyle = sl.color;
    ctx.fill();
    angle += sweep;
  });

  ctx.beginPath(); ctx.arc(cx, cy, r, 0, 2 * Math.PI);
  ctx.fillStyle = '#fff'; ctx.fill();

  ctx.fillStyle = '#1e293b'; ctx.font = 'bold 22px Inter,sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(slices[0]?.value || 0, cx, cy + 2);
  ctx.fillStyle = '#64748b'; ctx.font = '11px Inter,sans-serif';
  ctx.fillText(slices[0]?.label || '', cx, cy + 18);
}
