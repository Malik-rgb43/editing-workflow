/* מחסן העבודות - library + review room. Vanilla JS, no network beyond this local server. */
(function () {
'use strict';
const TOKEN = document.querySelector('meta[name="wh-token"]').content;
const $ = (s, el) => (el || document).querySelector(s);
const app = $('#app');

/* ---------------------------------------------------------------- helpers */
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'html') el.innerHTML = v;
    else if (k === 'text') el.textContent = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'value') el.value = v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat(9)) {
    if (kid == null || kid === false) continue;
    el.appendChild(typeof kid === 'string' || typeof kid === 'number' ? document.createTextNode(String(kid)) : kid);
  }
  return el;
}
const I = {
  play: '<svg viewBox="0 0 24 24"><path d="M7 4.5l13 7.5-13 7.5z"/></svg>',
  pause: '<svg viewBox="0 0 24 24"><path d="M7 4h3.5v16H7zM13.5 4H17v16h-3.5z" fill="currentColor" stroke="none"/></svg>',
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
  dots: '<svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="12" cy="19" r="1.4"/></svg>',
  down: '<svg viewBox="0 0 24 24"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>',
  broom: '<svg viewBox="0 0 24 24"><path d="M14 4l6 6M12.5 5.5l6 6-4.5 4.5-6-6zM8 10l-4.5 8.5L12 14"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>',
  edit: '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/></svg>',
  open: '<svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  pen: '<svg viewBox="0 0 24 24"><path d="M4 20c4-1 6-4 9-9l3-3 2 2-3 3c-5 3-8 5-9 9z"/></svg>',
  circle: '<svg viewBox="0 0 24 24"><ellipse cx="12" cy="12" rx="9" ry="7"/></svg>',
  arrow: '<svg viewBox="0 0 24 24"><path d="M5 19L19 5M10 5h9v9"/></svg>',
  undo: '<svg viewBox="0 0 24 24"><path d="M9 14L4 9l5-5M4 9h10a6 6 0 010 12h-3"/></svg>',
  range: '<svg viewBox="0 0 24 24"><path d="M4 6v12M20 6v12M8 12h8M8 12l3-3M8 12l3 3"/></svg>',
  pin: '<svg viewBox="0 0 24 24"><path d="M12 21s7-6.5 7-12a7 7 0 10-14 0c0 5.5 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>',
  draw: '<svg viewBox="0 0 24 24"><path d="M3 21l3.5-1L19 7.5 16.5 5 4 17.5zM14 7.5l2.5 2.5"/></svg>',
  cmp: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="8" height="14" rx="2"/><rect x="13" y="5" width="8" height="14" rx="2"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  send: '<svg viewBox="0 0 24 24"><path d="M21 3L10 14M21 3l-7 18-4-7-7-4z"/></svg>',
  loop: '<svg viewBox="0 0 24 24"><path d="M17 2l3 3-3 3M4 11V9a4 4 0 014-4h12M7 22l-3-3 3-3M20 13v2a4 4 0 01-4 4H4"/></svg>',
  vol: '<svg viewBox="0 0 24 24"><path d="M4 9h4l5-4v14l-5-4H4zM16.5 8.5a5 5 0 010 7M19 6a8.5 8.5 0 010 12"/></svg>',
  mute: '<svg viewBox="0 0 24 24"><path d="M4 9h4l5-4v14l-5-4H4zM17 9l5 6M22 9l-5 6"/></svg>',
  full: '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>',
};
const icon = (n) => h('span', { html: I[n], style: 'display:contents' });
function fmtT(t, cs = true) {
  if (t == null || !isFinite(t)) return '--:--';
  const c = Math.round(t * 100), m = Math.floor(c / 6000), s = Math.floor((c % 6000) / 100), r = c % 100;
  return `${m}:${String(s).padStart(2, '0')}` + (cs ? `.${String(r).padStart(2, '0')}` : '');
}
function bytes(n) {
  if (!n) return '⁦0 MB⁩';
  const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return '⁦' + (i >= 3 ? n.toFixed(1) : Math.round(n)) + ' ' + u[i] + '⁩';
}
function rel(iso) {
  if (!iso) return '';
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 60) return 'עכשיו';
  if (d < 3600) return `לפני ${Math.round(d / 60)} דק׳`;
  if (d < 86400) return `לפני ${Math.round(d / 3600)} שע׳`;
  const days = Math.round(d / 86400);
  if (days === 1) return 'אתמול';
  if (days < 30) return `לפני ${days} ימים`;
  const mo = Math.round(days / 30);
  return mo === 1 ? 'לפני חודש' : `לפני ${mo} חודשים`;
}
const dateStr = (iso) => iso ? new Date(iso).toLocaleDateString('he-IL', { day: 'numeric', month: 'short', year: 'numeric' }) : '';
function hue(s) { let x = 0; for (const c of s) x = (x * 31 + c.charCodeAt(0)) >>> 0; return x % 360; }
const enc = encodeURIComponent;
async function api(path, body) {
  const opt = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Token': TOKEN }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  let d = {};
  try { d = await r.json(); } catch (e) { /* empty body */ }
  if (r.status === 403 && body !== undefined) { toast('המחסן הופעל מחדש. מרענן…'); setTimeout(() => location.reload(), 1200); }
  if (!r.ok) { const err = new Error(d.error || `שגיאה ${r.status}`); err.data = d; err.status = r.status; throw err; }
  return d;
}
function toast(msg, kind) {
  const t = h('div', { class: 'toast ' + (kind || '') }, msg);
  $('#toasts').appendChild(t);
  setTimeout(() => { t.style.transition = 'opacity .3s'; t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 2600);
}
function confetti() {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const box = h('div', { class: 'confetti' });
  const cols = ['#7c6cff', '#34d399', '#fbbf24', '#ff6b6b', '#a597ff', '#7dd3fc'];
  for (let i = 0; i < 90; i++) {
    box.appendChild(h('i', { style: `left:${Math.random() * 100}%;background:${cols[i % cols.length]};--dx:${(Math.random() - .5) * 240}px;--rot:${Math.random() * 900}deg;animation-delay:${Math.random() * .35}s;animation-duration:${1.3 + Math.random()}s` }));
  }
  document.body.appendChild(box);
  setTimeout(() => box.remove(), 2800);
}
function modal(build) {
  const wrap = $('#modal');
  wrap.innerHTML = '';
  const close = () => { wrap.hidden = true; wrap.innerHTML = ''; document.removeEventListener('keydown', esc, true); };
  const esc = (e) => { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
  const box = h('div', { class: 'modal', role: 'dialog', 'aria-modal': 'true' });
  build(box, close);
  wrap.appendChild(box);
  wrap.hidden = false;
  wrap.onclick = (e) => { if (e.target === wrap) close(); };
  document.addEventListener('keydown', esc, true);
  const f = box.querySelector('input,textarea,button.primary,button.good,button.danger');
  if (f) setTimeout(() => f.focus(), 30);
  return close;
}
let menuEl = null;
function closeMenu() { if (menuEl) { menuEl.remove(); menuEl = null; } }
function menu(anchor, items) {
  closeMenu();
  const m = h('div', { class: 'menu', role: 'menu' });
  for (const it of items) {
    if (it === '-') { m.appendChild(h('hr')); continue; }
    m.appendChild(h('button', { class: it.danger ? 'danger' : '', role: 'menuitem', onclick: (e) => { e.stopPropagation(); closeMenu(); it.fn(); } },
      it.icon ? icon(it.icon) : null, it.label, it.hint ? h('span', { class: 'hint' }, it.hint) : null));
  }
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  const w = m.offsetWidth, hh = m.offsetHeight;
  m.style.top = Math.min(r.bottom + 6, innerHeight - hh - 8) + 'px';
  m.style.left = Math.max(8, Math.min(r.left, innerWidth - w - 8)) + 'px';
  menuEl = m;
}
document.addEventListener('click', closeMenu);
const isTyping = (el) => el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);

/* ---------------------------------------------------------------- router */
let cleanup = null;
let LIB = null;
function route() {
  if (cleanup) { cleanup(); cleanup = null; }
  closeMenu();
  const parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
  if (parts[0] === 'p' && parts[1]) return review(parts[1], parts[2]);
  return library(parts[0] === 'c' ? parts[1] : null);
}
window.addEventListener('hashchange', route);

function crumbs(list) {
  const c = $('#crumbs');
  c.innerHTML = '';
  list.forEach((x, i) => {
    if (i) c.appendChild(h('span', { class: 'sep' }, '/'));
    c.appendChild(x.href ? h('a', { href: x.href }, x.label) : h('span', { class: 'cur' }, x.label));
  });
}
function diskPill(disk) {
  const d = $('#disk');
  d.onclick = (e) => { e.stopPropagation(); menu(d, [{ label: 'נקה מטמון של פרימייר', icon: 'broom', fn: premiereFlow }, { label: 'חפש עותקים כפולים ב-incoming', icon: 'search', fn: duplicatesFlow }]); };
  d.innerHTML = '';
  d.append(disk.free ? h('b', {}, `${bytes(disk.free)} פנויים`) : h('b', {}, bytes(disk.bytes) + ' בדיסק'));
  if (disk.reclaim > 1 << 20) d.append(' · ', h('span', { class: 'free' }, `אפשר לפנות ${bytes(disk.reclaim)}`));
}

/* ---------------------------------------------------------------- library */
const STATUSES = ['גלם חדש', 'בעבודה', 'ממתין לבדיקה', 'בתיקונים', 'אושר', 'נמסר'];
const stIdx = (s) => Math.max(0, STATUSES.indexOf(s));
let libView = (() => { try { return localStorage.getItem('wh.view') || 'grid'; } catch (e) { return 'grid'; } })();

async function library(client) {
  crumbs(client ? [{ label: 'כל הלקוחות', href: '#/' }, { label: client }] : [{ label: 'כל הלקוחות' }]);
  app.innerHTML = '';
  app.appendChild(h('div', { class: 'empty', style: 'flex:1' }, 'טוען את המחסן…'));
  let data;
  try { data = await api('/api/library'); app.innerHTML = ''; } catch (e) { app.innerHTML = ''; app.appendChild(h('div', { class: 'empty' }, 'לא הצלחתי לטעון: ' + e.message)); return; }
  LIB = data;
  diskPill(data.disk);
  const projs = data.projects;
  const clients = {};
  for (const p of projs) (clients[p.client] = clients[p.client] || []).push(p);
  const LIBD = data.library || { items: [], clients: [] };
  const libItems = LIBD.items;
  const libClient = {};
  LIBD.clients.forEach((c) => { libClient[c.name] = c; });
  let libAll = false;
  let q = '', stFilter = null;

  const folder = (name, label, n, on) => h('a', { class: 'folder' + (on ? ' on' : ''), href: name ? '#/c/' + enc(name) : '#/' },
    h('span', { class: 'ico', style: name ? `background:hsl(${hue(name)} 55% 42%)` : 'background:var(--accent)' }, name ? name.slice(0, 2).toUpperCase() : '★'),
    label, h('span', { class: 'n' }, n));
  const side = h('aside', { class: 'side' }, h('h4', {}, 'תיקיות'),
    folder(null, 'כל העבודות', projs.length + libItems.length, !client),
    [...new Set([...Object.keys(clients), ...LIBD.clients.map((c) => c.name)])].sort((a, b) => a.localeCompare(b, 'he'))
      .map((c) => folder(c, c, (clients[c] || []).length + libItems.filter((i) => i.client === c).length, c === client)));

  const list = client ? (clients[client] || []) : projs;
  const libList = client ? libItems.filter((i) => i.client === client) : libItems;
  const total = list.reduce((a, p) => a + p.bytes, 0), reclaim = list.reduce((a, p) => a + p.reclaim, 0);
  const body = h('div');
  const filt = h('div', { class: 'filters' });
  function drawFilters() {
    filt.innerHTML = '';
    filt.appendChild(h('button', { class: stFilter == null ? 'on' : '', onclick: () => { stFilter = null; drawFilters(); draw(); } }, `הכל · ${list.length}`));
    STATUSES.forEach((s) => {
      const n = list.filter((p) => p.status === s).length;
      if (n) filt.appendChild(h('button', { class: stFilter === s ? 'on' : '', onclick: () => { stFilter = s; drawFilters(); draw(); } }, `${s} · ${n}`));
    });
  }
  const viewSeg = h('div', { class: 'seg' },
    h('button', { class: libView === 'grid' ? 'on' : '', onclick: () => setView('grid') }, 'רשת'),
    h('button', { class: libView === 'board' ? 'on' : '', onclick: () => setView('board') }, 'לפי שלב'));
  function setView(v) { libView = v; try { localStorage.setItem('wh.view', v); } catch (e) { /* private mode */ } [...viewSeg.children].forEach((b, i) => b.classList.toggle('on', (i === 0) === (v === 'grid'))); draw(); }
  const search = h('label', { class: 'search' }, icon('search'), h('input', { class: 'inp', placeholder: 'חיפוש סרטון…', oninput: (e) => { q = e.target.value.trim().toLowerCase(); draw(); } }));
  const head = h('div', { class: 'lib-head' },
    h('div', {}, h('h1', {}, client || 'כל העבודות'),
      h('div', { class: 'sub' }, `${list.length} בעבודה · ${libList.length} מוכנים בתיקיות` + (client && libClient[client] ? ` · ${bytes(libClient[client].bytes)}` : ` · ${bytes(total)}`) + (data.disk.free ? ` · פנוי בדיסק ${bytes(data.disk.free)}` : ''), reclaim > 1 << 20 ? h('span', { style: 'color:var(--like)' }, ` · אפשר לפנות ${bytes(reclaim)}`) : null)),
    h('div', { class: 'grow' }), search, viewSeg,
    h('button', { class: 'btn primary', onclick: () => importWizard(null, client) }, '📥 קליטת חומר'),
    client ? h('button', { class: 'btn ghost', title: 'אפשרויות לקוח', onclick: (e) => { e.stopPropagation(); menu(e.currentTarget, [
      libClient[client] ? { label: 'פתח את התיקייה במחשב', icon: 'open', fn: () => reveal(libClient[client].path) } : null,
      { label: 'צמצם את כל העבודות המאושרות', icon: 'broom', fn: () => bulkCompact(list) },
      libClient[client] ? { label: 'הסתר את התיקייה מהמחסן', icon: 'edit', fn: () => hideFolder(client) } : null,
      list.length ? '-' : null, list.length ? { label: `מחק את פרויקטי העבודה של ${client}…`, icon: 'trash', danger: true, fn: () => deleteClient(client, list) } : null].filter(Boolean)); } }, icon('dots')) : null);

  function card(p, small) {
    const v = p.latest;
    const img = v ? h('img', { src: `/thumb/${enc(p.slug)}/${v.id}.jpg`, alt: '', loading: 'lazy', onerror: (e) => { e.target.replaceWith(h('div', { class: 'ph' }, 'אין תמונה')); } })
      : p.raw_sample ? h('img', { src: '/clipthumb?path=' + enc(p.raw_sample), alt: '', loading: 'lazy', style: 'filter:saturate(.7)' }) : h('div', { class: 'ph' }, 'עוד אין סרטון');
    return h('article', { class: 'card' },
      h('a', { class: 'thumb', href: `#/p/${enc(p.slug)}`, style: small ? '' : (v && v.w && v.h && v.w > v.h ? 'aspect-ratio:16/10' : '') }, img,
        h('div', { class: 'play' }, h('span', { html: I.play })),
        h('div', { class: 'badge-tl' }, v ? h('span', { class: 'pill' }, v.id) : null, p.open_notes ? h('span', { class: 'pill fix', title: 'הערות שמחכות ל-Claude' }, `${p.open_notes} פתוחות`) : null),
        !v && p.raw_bytes ? h('div', { class: 'badge-br' }, h('span', { class: 'pill' }, '🎞 גלם · ' + bytes(p.raw_bytes))) : null,
        v && v.duration ? h('div', { class: 'badge-br' }, h('span', { class: 'pill mono' }, fmtT(v.duration, false))) : null),
      h('button', { class: 'kebab', 'aria-label': 'אפשרויות', html: I.dots, onclick: (e) => { e.stopPropagation(); e.preventDefault(); cardMenu(e.currentTarget, p); } }),
      h('div', { class: 'card-body' },
        h('a', { class: 'card-title', href: `#/p/${enc(p.slug)}`, title: p.title }, p.title),
        h('div', { class: 'card-meta' }, h('span', { class: 'chip st-' + stIdx(p.status) }, h('span', { class: 'dot' }), p.status),
          !client ? h('span', {}, p.client) : null, h('span', {}, '· ' + rel(p.updated_utc))),
        h('div', { class: 'card-foot' }, h('span', { class: 'size' }, bytes(p.bytes),
          p.reclaim > 1 << 20 ? h('span', { class: 'free' }, ` · ${bytes(p.reclaim)} לפינוי`) : p.compacted_utc ? ' · מצומצם ✓' : '', p.raw_deleted_utc ? ' · גלם נמחק' : ''),
          p.pending_notes ? h('span', { class: 'chip', style: 'color:var(--note)' }, `${p.pending_notes} טיוטות הערה`) : null)));
  }
  function libCard(i) {
    return h('article', { class: 'card' },
      h('a', { class: 'thumb', href: `#/p/${enc(i.id)}` }, h('img', { src: '/clipthumb?path=' + enc(i.path), alt: '', loading: 'lazy', onerror: (e) => { e.target.replaceWith(h('div', { class: 'ph' }, '🎬')); } }),
        h('div', { class: 'play' }, h('span', { html: I.play }))),
      h('button', { class: 'kebab', 'aria-label': 'אפשרויות', html: I.dots, onclick: (e) => { e.stopPropagation(); e.preventDefault(); menu(e.currentTarget, [
        { label: 'פתח לצפייה והערות', icon: 'open', fn: () => { location.hash = `#/p/${enc(i.id)}`; } },
        { label: 'הורד', icon: 'down', fn: () => { location.href = `/download/${enc(i.id)}/V1`; } },
        { label: 'הצג בתיקייה', icon: 'open', fn: () => reveal(i.path) },
        '-', { label: 'מחק לסל המיחזור…', icon: 'trash', danger: true, fn: () => deleteLibFile(i) }]); } }),
      h('div', { class: 'card-body' },
        h('a', { class: 'card-title', href: `#/p/${enc(i.id)}`, title: i.rel }, i.title),
        h('div', { class: 'card-meta' }, h('span', { class: 'chip st-5' }, h('span', { class: 'dot' }), i.folder || 'מוכנים'), !client ? h('span', {}, i.client) : null, h('span', {}, '· ' + rel(i.mtime))),
        h('div', { class: 'card-foot' }, h('span', { class: 'size' }, bytes(i.bytes)))));
  }
  function draw() {
    body.innerHTML = '';
    let items = list.filter((p) => (!q || (p.title + ' ' + p.client + ' ' + p.slug).toLowerCase().includes(q)));
    items.sort((a, b) => (b.updated_utc || '').localeCompare(a.updated_utc || ''));
    if (!projs.length && !libItems.length) {
      body.appendChild(h('div', { class: 'empty' }, h('div', { class: 'big' }, '🎬'), h('div', {}, 'המחסן ריק. התחל בקליטת חומר מכרטיס.'), h('button', { class: 'btn primary lg', style: 'margin-top:14px', onclick: () => importWizard() }, '📥 קליטת חומר'), h('div', { class: 'mono', style: 'margin-top:8px;font-size:12px' }, data.root)));
      return;
    }
    if (libView === 'board') {
      const b = h('div', { class: 'board' });
      STATUSES.forEach((s) => {
        const col = items.filter((p) => p.status === s);
        const extra = s === 'נמסר' ? libList.filter((i) => !q || (i.title + ' ' + i.client).toLowerCase().includes(q)).sort((a, b) => b.mtime.localeCompare(a.mtime)) : [];
        b.appendChild(h('section', { class: 'col' }, h('div', { class: 'col-h' }, h('span', { class: 'chip st-' + stIdx(s) }, h('span', { class: 'dot' }), s), h('span', { class: 'n' }, col.length + extra.length)),
          col.map((p) => card(p, true)), extra.slice(0, 8).map((i) => libCard(i)),
          extra.length > 8 ? h('button', { class: 'btn sm ghost', onclick: () => setView('grid') }, `עוד ${extra.length - 8} בתצוגת רשת`) : ''));
      });
      body.appendChild(b);
      filt.hidden = true;
      return;
    }
    filt.hidden = !list.length;
    items = items.filter((p) => !stFilter || p.status === stFilter);
    let lib = stFilter ? [] : libList.filter((i) => !q || (i.title + ' ' + i.client + ' ' + i.folder).toLowerCase().includes(q));
    lib = lib.sort((a, b) => b.mtime.localeCompare(a.mtime));
    if (!items.length && !lib.length) { body.appendChild(h('div', { class: 'empty' }, 'אין כאן כלום שמתאים לחיפוש')); return; }
    if (items.length) body.append(h('h3', { class: 'sec-h' }, '🎬 בעבודה עם Claude'), h('div', { class: 'grid' }, items.map((p) => card(p))));
    if (lib.length) {
      const cap = client || q || libAll ? lib.length : 24;
      body.append(h('h3', { class: 'sec-h' }, '📁 מוכנים בתיקיות שלך', h('span', {}, ` · ${lib.length}`)),
        h('div', { class: 'grid' }, lib.slice(0, cap).map((i) => libCard(i))),
        lib.length > cap ? h('div', { style: 'text-align:center;margin-top:16px' }, h('button', { class: 'btn', onclick: () => { libAll = true; draw(); } }, `הצג את כל ${lib.length}`)) : '');
    }
  }
  drawFilters(); draw();
  app.appendChild(h('div', { class: 'lib' }, side, h('section', { class: 'lib-main' }, head, filt, body)));
}

async function reveal(path) { try { await api('/api/reveal', { path }); toast('נפתח בסייר הקבצים'); } catch (e) { toast(e.message, 'bad'); } }
async function hideFolder(name) { try { await api('/api/library-hide', { name }); toast(`"${name}" הוסתר. אפשר להחזיר ב-config.json`); location.hash = '#/'; route(); } catch (e) { toast(e.message, 'bad'); } }
function deleteLibFile(i) {
  typedConfirm(`למחוק את "${i.title}"?`, `הקובץ ${i.rel} (${bytes(i.bytes)}) עובר לסל המיחזור של Windows. משם אפשר לשחזר.`, i.title, 'מחק לסל המיחזור',
    async () => { await api(`/api/project/${enc(i.id)}/delete`, { confirm: i.id }); toast('הועבר לסל המיחזור 🗑'); route(); });
}
async function premiereFlow() {
  toast('בודק את המטמון של פרימייר…');
  let c;
  try { c = await api('/api/premiere-cache', {}); } catch (e) { return toast(e.message, 'bad'); }
  if (!c.bytes) return toast('אין מטמון פרימייר לניקוי ✓', 'good');
  modal((box, close) => {
    box.append(h('h3', {}, 'ניקוי מטמון של פרימייר'),
      h('p', {}, 'אלה קבצי Preview (Audio / Video Previews) שפרימייר מייצר בעצמו ויבנה מחדש כשצריך. את הפרויקטים, את ה-Auto-Save ואת החומרים לא נוגעים.'),
      h('div', { class: 'total' }, bytes(c.bytes)), h('div', { style: 'color:var(--muted);font-size:12.5px' }, `${c.folders.length} תיקיות מטמון`),
      h('table', {}, c.folders.slice(0, 10).map((f) => h('tr', {}, h('td', { style: 'text-align:start' }, f.rel), h('td', {}, bytes(f.bytes))))),
      c.premiere_running ? h('div', { class: 'errbox' }, 'פרימייר פתוח עכשיו. סגור אותו ואז נקה.') : '',
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: close }, 'ביטול'), h('button', { class: 'btn primary', disabled: c.premiere_running, onclick: async (e) => {
        e.target.disabled = true;
        try { const r = await api('/api/premiere-cache-clear', {}); close(); toast(`פינית ${bytes(r.freed)} 🧹`, 'good'); route(); } catch (err) { e.target.disabled = false; toast(err.message, 'bad'); }
      } }, `נקה ${bytes(c.bytes)}`)));
  });
}
function cardMenu(anchor, p) {
  menu(anchor, [
    { label: 'פתח לסקירה', icon: 'open', fn: () => { location.hash = `#/p/${enc(p.slug)}`; } },
    p.latest ? { label: `הורד ${p.latest.id}`, icon: 'down', fn: () => { location.href = `/download/${enc(p.slug)}/${p.latest.id}`; } } : null,
    { label: 'שם, לקוח וסטטוס…', icon: 'edit', fn: () => editMeta(p) },
    { label: 'הצג בתיקייה', icon: 'open', fn: () => reveal((LIB && LIB.root ? LIB.root + '\\' : '') + p.slug) },
    '-',
    { label: 'קלוט עוד חומר לפרויקט…', icon: 'down', fn: () => importWizard(p.slug) },
    '-',
    { label: 'צמצם', icon: 'broom', hint: p.reclaim > 1 << 20 ? bytes(p.reclaim) : 'אין מה לפנות', fn: () => compactFlow(p) },
    { label: 'מחק גלם…', icon: 'trash', hint: p.raw_bytes ? bytes(p.raw_bytes) : 'אין גלם', fn: () => deleteRaw(p) },
    { label: 'מחק את כל הפרויקט…', icon: 'trash', danger: true, fn: () => deleteProject(p) },
  ].filter(Boolean));
}
function editMeta(p, after) {
  const clients = [...new Set((LIB ? LIB.projects : []).map((x) => x.client))];
  modal((box, close) => {
    const t = h('input', { class: 'inp', value: p.title }), c = h('input', { class: 'inp', value: p.client, list: 'wh-clients' });
    const s = h('select', { class: 'sel', style: 'width:100%' }, STATUSES.map((x) => h('option', { value: x, selected: x === p.status }, x)));
    box.append(h('h3', {}, 'פרטי הסרטון'), h('p', {}, 'הלקוח קובע באיזו תיקייה הסרטון מופיע. התיקייה במחשב לא זזה.'),
      h('label', {}, 'שם'), t, h('div', { style: 'height:10px' }), h('label', {}, 'לקוח'), c,
      h('datalist', { id: 'wh-clients' }, clients.map((x) => h('option', { value: x }))), h('div', { style: 'height:10px' }), h('label', {}, 'סטטוס'), s,
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: close }, 'ביטול'), h('button', { class: 'btn primary', onclick: async () => {
        try { await api(`/api/project/${enc(p.slug)}/meta`, { title: t.value, client: c.value, status: s.value }); close(); toast('נשמר ✓', 'good'); after ? after() : route(); } catch (e) { toast(e.message, 'bad'); }
      } }, 'שמור')));
  });
}
async function compactFlow(p, force) {
  let pv;
  try { pv = await api(`/api/project/${enc(p.slug)}/compact-preview`); } catch (e) { return toast(e.message, 'bad'); }
  if (!pv.total) return toast('אין כאן קבצי ביניים לפינוי. הפרויקט כבר רזה ✓', 'good');
  const approved = p.status === 'אושר' || p.status === 'נמסר';
  modal((box, close) => {
    box.append(h('h3', {}, `צמצום: ${p.title}`),
      h('p', {}, 'מוחק לצמיתות רק קבצים שאפשר לייצר מחדש: רינדורי ביניים, טיוטות ישנות, פריימים ותמונות בדיקה.'),
      h('div', { class: 'total' }, bytes(pv.total)), h('div', { style: 'color:var(--muted);font-size:12.5px' }, 'יתפנו מהדיסק'),
      h('table', {}, pv.groups.slice(0, 12).map((g) => h('tr', {}, h('td', { class: 'mono', style: 'text-align:left' }, g.path), h('td', {}, `${g.files} קבצים · ${bytes(g.bytes)}`)))),
      h('div', { class: 'keep' }, '✓ נשאר: הסרטונים הסופיים (final), קוד העריכה (hf), חומרי המקור (source), כל ההערות והגרסאות במחסן, ובתוך _work גם ' + pv.kept.join(', ') + ', כל האודיו וכל קבצי הטקסט.'),
      !approved ? h('div', { class: 'keep', style: 'color:var(--note)' }, '⚠ הסרטון עוד לא מסומן כ"אושר" או "נמסר". בדרך כלל מצמצמים רק עבודות גמורות.') : '',
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: close }, 'ביטול'),
        h('button', { class: 'btn primary', onclick: async (e) => {
          e.target.disabled = true;
          try { const r = await api(`/api/project/${enc(p.slug)}/compact`, { force: !approved }); close(); toast(`פינית ${r.freed_h} 🧹`, 'good'); route(); } catch (err) { e.target.disabled = false; toast(err.message, 'bad'); }
        } }, `צמצם ופנה ${bytes(pv.total)}`)));
  });
}
async function bulkCompact(list) {
  const ok = list.filter((p) => (p.status === 'אושר' || p.status === 'נמסר') && p.reclaim > 1 << 20);
  if (!ok.length) return toast('אין עבודות מאושרות עם מה לפנות', 'good');
  const sum = ok.reduce((a, p) => a + p.reclaim, 0);
  modal((box, close) => {
    box.append(h('h3', {}, 'צמצום כל העבודות המאושרות'), h('p', {}, ok.map((p) => p.title).join(' · ')), h('div', { class: 'total' }, bytes(sum)),
      h('div', { class: 'keep' }, 'אותו כלל כמו בצמצום רגיל: הסופיים, הקוד, המקור, האודיו, הטקסט וההערות נשארים.'),
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: close }, 'ביטול'), h('button', { class: 'btn primary', onclick: async (e) => {
        e.target.disabled = true; let freed = 0;
        for (const p of ok) { try { freed += (await api(`/api/project/${enc(p.slug)}/compact`, {})).freed; } catch (err) { toast(`${p.title}: ${err.message}`, 'bad'); } }
        close(); toast(`פינית ${bytes(freed)} 🧹`, 'good'); route();
      } }, `צמצם ${ok.length} עבודות`)));
  });
}
function typedConfirm(title, text, word, label, fn) {
  modal((box, close) => {
    const inp = h('input', { class: 'inp mono', placeholder: word, style: 'text-align:left' });
    const go = h('button', { class: 'btn danger', disabled: true, onclick: async () => { go.disabled = true; try { await fn(); close(); } catch (e) { go.disabled = false; toast(e.message, 'bad'); } } }, label);
    inp.addEventListener('input', () => { go.disabled = inp.value.trim() !== word; });
    inp.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !go.disabled) go.click(); });
    box.append(h('h3', {}, title), h('p', {}, text), h('label', {}, 'כדי לאשר, הקלד: ', h('b', { class: 'mono' }, word)), inp,
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: close }, 'ביטול'), go));
  });
}
function deleteProject(p) {
  typedConfirm(`למחוק את "${p.title}"?`, `כל התיקייה (${bytes(p.bytes)}): מקור, קוד, סרטונים והערות, עוברת לסל המיחזור של Windows. משם אפשר לשחזר, וכשתרוקן את הסל המקום יתפנה.`,
    p.slug, 'מחק לסל המיחזור', async () => { await api(`/api/project/${enc(p.slug)}/delete`, { confirm: p.slug }); toast('הועבר לסל המיחזור 🗑'); location.hash = '#/'; route(); });
}
function deleteClient(client, list) {
  typedConfirm(`למחוק את כל הלקוח ${client}?`, `${list.length} פרויקטים (${bytes(list.reduce((a, p) => a + p.bytes, 0))}) עוברים לסל המיחזור של Windows. משם אפשר לשחזר.`,
    client, `מחק ${list.length} פרויקטים`, async () => { await api(`/api/client-delete/${enc(client)}`, { confirm: client }); toast('הועבר לסל המיחזור 🗑'); location.hash = '#/'; });
}

/* ---------------------------------------------------------------- review */
const KIND = { fix: { label: 'לתקן', emoji: '👎' }, like: { label: 'אהבתי', emoji: '👍' }, note: { label: 'הערה', emoji: '💬' } };
const STATE = { pending: 'טיוטה', open: 'פתוח', resolved: 'טופל', sent: 'נשלח' };
const COLORS = ['#ff4d4d', '#ffd23f', '#34d399', '#ffffff', '#7c6cff'];

async function review(slug, vidWanted) {
  app.innerHTML = '';
  let data;
  try { data = await api(`/api/project/${enc(slug)}`); } catch (e) { app.appendChild(h('div', { class: 'empty' }, 'הפרויקט לא נמצא: ' + e.message)); return; }
  const isLib = !!data.library_file;
  const R = {
    slug, st: data.state, hasWords: data.has_transcript, tab: 'notes', filter: 'all', kind: 'fix', mode: 'point', general: false,
    inT: null, outT: null, draw: false, tool: 'ellipse', color: COLORS[0], strokes: [], sel: null, loop: false, cmp: null, words: null, picked: null, rev: data.state.updated_utc,
  };
  const live = R.st.versions.filter((v) => !v.missing);
  const v = R.st.versions.find((x) => x.id === vidWanted) || live[live.length - 1] || R.st.versions[R.st.versions.length - 1];
  R.v = v;
  crumbs([{ label: 'כל הלקוחות', href: '#/' }, { label: R.st.client, href: '#/c/' + enc(R.st.client) }, { label: R.st.title }]);
  if (!v) {
    app.appendChild(h('div', { class: 'empty', style: 'flex:1' }, h('div', { class: 'big' }, '⏳'), 'עוד אין סרטון בפרויקט הזה. ברגע ש-Claude ירנדר טיוטה היא תופיע כאן.'));
    return;
  }
  const fps = v.fps || 30;
  const dur = () => (isFinite(video.duration) && video.duration) || v.duration || 0;

  /* --- top bar */
  const statusSel = h('select', { class: 'sel', title: 'סטטוס', onchange: async (e) => {
    try { const r = await api(`/api/project/${enc(slug)}/meta`, { status: e.target.value }); R.st = r.state; R.rev = r.state.updated_utc; toast('הסטטוס עודכן ✓', 'good'); } catch (err) { toast(err.message, 'bad'); }
  } }, STATUSES.map((s) => h('option', { value: s, selected: s === R.st.status }, s)));
  const verSel = h('select', { class: 'sel', title: 'גרסה', onchange: (e) => { location.hash = `#/p/${enc(slug)}/${e.target.value}`; } },
    R.st.versions.map((x) => h('option', { value: x.id, selected: x.id === v.id, disabled: x.missing }, `${x.id} · ${x.label}${x.missing ? ' (נמחק)' : ''}${x.approved_utc ? ' ✓' : ''}`)));
  const cmpBtn = h('button', { class: 'btn', title: 'השוואה בין גרסאות', disabled: live.length < 2, onclick: (e) => { e.stopPropagation(); compareMenu(e.currentTarget); } }, icon('cmp'), 'השווה');
  const bar = h('div', { class: 'rv-bar' },
    h('div', { class: 'rv-title' }, h('b', {}, R.st.title), h('span', {}, `${R.st.client} · ${v.label} · ⁦${v.w || '?'}×${v.h || '?'} · ${fps}fps⁩`)),
    verSel, statusSel, cmpBtn,
    h('a', { class: 'btn', href: `/download/${enc(slug)}/${v.id}`, title: 'הורדת הגרסה הזו' }, icon('down'), 'הורד'),
    h('button', { class: 'btn ghost', title: 'עוד', onclick: (e) => { e.stopPropagation(); menu(e.currentTarget, isLib ? [
      { label: 'הצג בתיקייה', icon: 'open', fn: () => reveal(data.library_file) },
      '-', { label: 'מחק לסל המיחזור…', icon: 'trash', danger: true, fn: () => deleteLibFile({ id: slug, title: R.st.title, rel: data.library_file, bytes: v.bytes }) }] : [
      { label: 'הצג בתיקייה', icon: 'open', fn: () => reveal(data.folder) },
      { label: 'שם, לקוח וסטטוס…', icon: 'edit', fn: () => editMeta({ slug, title: R.st.title, client: R.st.client, status: R.st.status }, () => route()) },
      { label: 'צמצם', icon: 'broom', fn: () => compactFlow({ slug, title: R.st.title, status: R.st.status }) },
      { label: 'מחק גלם…', icon: 'trash', fn: () => deleteRaw({ slug, title: R.st.title }) },
      '-', { label: 'מחק לסל המיחזור…', icon: 'trash', danger: true, fn: () => deleteProject({ slug, title: R.st.title, bytes: 0 }) }]); } }, icon('dots')));

  /* --- stage */
  const video = h('video', { src: `/media/${enc(slug)}/${v.id}`, preload: 'auto', playsinline: true, crossorigin: 'anonymous' });
  const canvas = h('canvas');
  const tcchip = h('div', { class: 'tcchip mono' });
  const drawHint = h('div', { class: 'draw-hint', hidden: true }, 'הקף או סמן על הפריים · Esc לביטול');
  const screen = h('div', { class: 'screen' }, video, canvas, tcchip, drawHint);
  const stage = h('div', { class: 'stage' }, v.missing ? h('div', { class: 'missing' }, 'הקובץ של הגרסה הזו נמחק (למשל בצמצום). ההערות שלה נשמרו בצד.') : screen);
  let video2 = null, screen2 = null;

  /* --- controls */
  const playBtn = h('button', { class: 'ctl play', title: 'נגן / עצור (רווח)', html: I.play, onclick: () => togglePlay() });
  const timeEl = h('span', { class: 'time mono' });
  const speed = h('select', { class: 'speed', title: 'מהירות', onchange: (e) => { video.playbackRate = +e.target.value; if (video2) video2.playbackRate = +e.target.value; } },
    [0.25, 0.5, 1, 1.5, 2].map((s) => h('option', { value: s, selected: s === 1 }, s + 'x')));
  const loopBtn = h('button', { class: 'ctl', title: 'לופ על הקטע המסומן', html: I.loop, onclick: () => { R.loop = !R.loop; loopBtn.classList.toggle('on', R.loop); } });
  const muteBtn = h('button', { class: 'ctl', title: 'השתק (M)', html: I.vol, onclick: () => { video.muted = !video.muted; muteBtn.innerHTML = video.muted ? I.mute : I.vol; } });
  const step = (label, title, fn) => h('button', { class: 'ctl', title, onclick: fn }, label);
  const controls = h('div', { class: 'controls' },
    step('-1s', 'שנייה אחורה (Shift+←)', () => seek(video.currentTime - 1)), step('-1f', 'פריים אחורה (←)', () => stepFrame(-1)),
    playBtn, step('+1f', 'פריים קדימה (→)', () => stepFrame(1)), step('+1s', 'שנייה קדימה (Shift+→)', () => seek(video.currentTime + 1)),
    timeEl, h('div', { class: 'grow' }), loopBtn, speed, muteBtn,
    h('button', { class: 'ctl', title: 'מסך מלא (F)', html: I.full, onclick: () => (document.fullscreenElement ? document.exitFullscreen() : screen.requestFullscreen()) }));

  /* --- timeline */
  const prog = h('div', { class: 'tl-prog' }), buf = h('div', { class: 'tl-buf' });
  const selBand = h('div', { class: 'tl-sel', hidden: true }), head = h('div', { class: 'tl-head' }), hover = h('div', { class: 'tl-hover mono', hidden: true });
  const marks = h('div');
  const track = h('div', { class: 'tl-track' }, buf, prog);
  const tl = h('div', { class: 'tl', title: 'לחץ לקפיצה · גרור עם Shift לסימון קטע' }, track, selBand, marks, head, hover);
  const ruler = h('div', { class: 'ruler mono' });

  /* --- composer */
  const ta = h('textarea', { rows: 1, placeholder: 'מה אהבת? מה לתקן? כתוב כאן… (Enter להוספה, Shift+Enter לשורה חדשה)' });
  const kindSeg = h('div', { class: 'seg', role: 'radiogroup', 'aria-label': 'סוג ההערה' });
  const modeSeg = h('div', { class: 'seg' });
  const when = h('span', { class: 'when mono' });
  const drawTools = h('div', { class: 'draw-tools', hidden: true });
  const addBtn = h('button', { class: 'btn primary', onclick: () => addNote() }, 'הוסף הערה');
  const composer = h('div', { class: 'composer' },
    h('div', { class: 'comp-row' }, kindSeg, modeSeg, when, h('div', { class: 'grow' }), drawTools),
    ta, h('div', { class: 'comp-row' }, h('span', { class: 'foot-note' }, 'ההערות נשמרות מיד, ונשלחות ל-Claude רק כשתלחץ "שלח"'), h('div', { class: 'grow' }), addBtn));

  /* --- side panel */
  const tabs = h('div', { class: 'tabs' });
  const pane = h('div', { class: 'pane' });
  const sendBtn = h('button', { class: 'btn primary lg', onclick: () => sendRound() });
  const approveBtn = h('button', { class: 'btn good lg', onclick: () => approve() });
  const footInfo = h('div', { class: 'foot-note' });
  const panel = h('aside', { class: 'panel' }, tabs, pane, h('div', { class: 'panel-foot' }, h('div', { class: 'row' }, sendBtn, approveBtn), footInfo));

  app.appendChild(h('div', { class: 'rv' }, h('section', { class: 'stage-wrap' }, bar, stage, controls, tl, ruler, composer), panel));

  /* ---------------- playback */
  function togglePlay() { if (v.missing) return; if (video.paused) { if (R.draw) setDraw(false); video.play(); } else video.pause(); }
  function seek(t) { video.currentTime = Math.max(0, Math.min(dur() || 0, t)); }
  function stepFrame(n) { video.pause(); const f = Math.round(video.currentTime * fps) + n; seek((f + 0.5) / fps); }
  function tick() {
    const t = video.currentTime, d = dur();
    tcchip.innerHTML = '';
    tcchip.append(h('span', {}, fmtT(t)), h('span', { class: 'f' }, `/ ${fmtT(d, false)}`), h('span', { class: 'f' }, 'F' + String(Math.floor(t * fps + 1e-6)).padStart(4, '0')));
    timeEl.innerHTML = '';
    timeEl.append(h('b', {}, fmtT(t)), ' / ' + fmtT(d, false));
    const pct = d ? (t / d) * 100 : 0;
    prog.style.width = pct + '%';
    head.style.left = pct + '%';
    if (video.buffered.length && d) buf.style.width = (video.buffered.end(video.buffered.length - 1) / d) * 100 + '%';
    if (R.loop && R.inT != null && R.outT != null && !video.paused && t >= R.outT) seek(R.inT);
    if (!R.general && R.mode === 'point') renderWhen();
    if (video2 && Math.abs(video2.currentTime - t) > 0.15) video2.currentTime = t;
    paint();
    highlightWord(t);
  }
  video.addEventListener('timeupdate', tick);
  video.addEventListener('seeked', tick);
  video.addEventListener('play', () => { playBtn.innerHTML = I.pause; if (video2) video2.play(); });
  video.addEventListener('pause', () => { playBtn.innerHTML = I.play; if (video2) { video2.pause(); video2.currentTime = video.currentTime; } tick(); });
  video.addEventListener('loadedmetadata', () => { drawRuler(); drawMarks(); layoutCanvas(); tick(); });
  let raf = 0;
  const loopRaf = () => { if (!video.paused) tick(); raf = requestAnimationFrame(loopRaf); };
  raf = requestAnimationFrame(loopRaf);

  /* ---------------- timeline */
  const timeAt = (e) => { const r = track.getBoundingClientRect(); return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * dur(); };
  let drag = null;
  tl.addEventListener('pointerdown', (e) => {
    if (e.target.classList.contains('mk') || v.missing) return;
    tl.setPointerCapture(e.pointerId);
    const t = timeAt(e);
    if (e.shiftKey || R.mode === 'range') { drag = { range: true, a: t }; setRange(t, null); } else { drag = { range: false }; seek(t); }
  });
  tl.addEventListener('pointermove', (e) => {
    const t = timeAt(e), r = track.getBoundingClientRect();
    hover.hidden = false; hover.textContent = fmtT(t); hover.style.left = ((e.clientX - r.left) / r.width) * 100 + '%';
    if (!drag) return;
    if (drag.range) { const a = Math.min(drag.a, t), b = Math.max(drag.a, t); setRange(a, b - a > 0.04 ? b : null); seek(t); } else seek(t);
  });
  tl.addEventListener('pointerup', () => { if (drag && drag.range && R.outT != null) { setMode('range'); ta.focus(); } drag = null; });
  tl.addEventListener('pointerleave', () => { hover.hidden = true; });
  function drawRuler() {
    ruler.innerHTML = '';
    const d = dur(); if (!d) return;
    const stepS = [1, 2, 5, 10, 15, 30, 60, 120].find((s) => d / s <= 10) || 300;
    for (let s = 0; s <= d + 0.01; s += stepS) ruler.appendChild(h('span', { style: `left:${(s / d) * 100}%` }, fmtT(s, false)));
  }
  function setRange(a, b) {
    R.inT = a; R.outT = b;
    const d = dur();
    if (a == null || !d) selBand.hidden = true;
    else { selBand.hidden = false; selBand.style.left = (a / d) * 100 + '%'; selBand.style.width = Math.max(0.4, (((b ?? a) - a) / d) * 100) + '%'; }
    renderWhen();
  }
  function versionNotes() { return R.st.notes.filter((n) => n.version === v.id); }
  function drawMarks() {
    marks.innerHTML = '';
    const d = dur(); if (!d) return;
    for (const n of versionNotes()) {
      if (n.t == null) continue;
      const cls = `k-${n.kind}-bg` + (n.state === 'resolved' ? ' done' : '') + (R.sel === n.id ? ' on' : '');
      if (n.end != null) marks.appendChild(h('div', { class: 'mk band ' + cls, style: `left:${(n.t / d) * 100}%;width:${((n.end - n.t) / d) * 100}%` }));
      marks.appendChild(h('div', { class: 'mk ' + cls, style: `left:${(n.t / d) * 100}%`, title: `${KIND[n.kind].label} · ${fmtT(n.t)} · ${n.text}`, onclick: (e) => { e.stopPropagation(); selectNote(n, true); } }));
    }
  }

  /* ---------------- composer */
  function renderKinds() {
    kindSeg.innerHTML = '';
    for (const k of ['fix', 'like', 'note']) kindSeg.appendChild(h('button', { class: (R.kind === k ? 'on ' : '') + 'k-' + k, role: 'radio', 'aria-checked': String(R.kind === k), onclick: () => { R.kind = k; renderKinds(); ta.focus(); } }, KIND[k].emoji + ' ' + KIND[k].label));
  }
  function setMode(m) { R.mode = m; R.general = false; if (m === 'point') setRange(null, null); else if (R.inT == null) setRange(video.currentTime, null); renderModes(); renderWhen(); }
  function renderModes() {
    modeSeg.innerHTML = '';
    modeSeg.append(
      h('button', { class: R.mode === 'point' && !R.general ? 'on' : '', title: 'הערה על הרגע הנוכחי (C)', onclick: () => setMode('point') }, icon('pin'), 'רגע'),
      h('button', { class: R.mode === 'range' && !R.general ? 'on' : '', title: 'הערה על קטע (I / O או גרירה עם Shift)', onclick: () => setMode('range') }, icon('range'), 'קטע'),
      h('button', { class: R.draw ? 'on' : '', title: 'ציור והקפה על הפריים (D)', onclick: () => setDraw(!R.draw) }, icon('draw'), 'ציור'),
      h('button', { class: R.general ? 'on' : '', title: 'הערה כללית על כל הסרטון, בלי זמן', onclick: () => { R.general = !R.general; if (R.general) { setRange(null, null); setDraw(false); } renderModes(); renderWhen(); } }, 'כללי'));
  }
  function renderWhen() {
    when.innerHTML = '';
    if (R.general) { when.append('כל הסרטון'); return; }
    if (R.mode === 'point') { when.append('@ ' + fmtT(video.currentTime)); return; }
    when.append(h('button', { title: 'סמן התחלה (I)', onclick: () => setRange(video.currentTime, R.outT != null && R.outT > video.currentTime ? R.outT : null) }, '['),
      fmtT(R.inT), ' → ', R.outT != null ? fmtT(R.outT) : '…',
      h('button', { title: 'סמן סוף (O)', onclick: () => markOut() }, ']'));
  }
  function markIn() { if (R.mode !== 'range') { R.mode = 'range'; R.general = false; renderModes(); } setRange(video.currentTime, R.outT != null && R.outT > video.currentTime ? R.outT : null); }
  function markOut() {
    if (R.mode !== 'range') { R.mode = 'range'; R.general = false; renderModes(); }
    const t = video.currentTime;
    if (R.inT == null || t <= R.inT) { toast('הסוף צריך להיות אחרי ההתחלה', 'bad'); return; }
    setRange(R.inT, t);
  }
  ta.addEventListener('focus', () => { if (!video.paused) video.pause(); });
  ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(140, ta.scrollHeight) + 'px'; });
  ta.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); addNote(); }
    if (e.key === 'Escape') { ta.blur(); }
  });
  async function addNote() {
    const text = ta.value.trim();
    const hasDraw = R.strokes.length > 0;
    if (!text && !hasDraw) { ta.focus(); toast('כתוב משהו או צייר על הפריים'); return; }
    let t = null, end = null;
    if (!R.general) {
      if (R.mode === 'range') {
        if (R.inT == null) { toast('סמן התחלה לקטע (I)', 'bad'); return; }
        t = R.inT; end = R.outT;
        if (end == null) { if (video.currentTime > t + 0.04) end = video.currentTime; else { toast('סמן סוף לקטע (O)', 'bad'); return; } }
      } else t = video.currentTime;
    }
    let png = null;
    if (hasDraw) { try { png = framePng(R.strokes); } catch (e) { png = null; } }
    addBtn.disabled = true;
    try {
      const r = await api(`/api/project/${enc(slug)}/note`, { action: 'create', version: v.id, note: { t, end, text, kind: R.kind, drawing: hasDraw ? R.strokes : null }, png });
      R.st = r.state; R.rev = r.state.updated_utc;
      ta.value = ''; ta.style.height = ''; ta.blur();
      R.strokes = [];
      if (R.draw) setDraw(false);
      if (R.mode === 'range') setRange(null, null);
      R.mode = 'point'; R.general = false; renderModes(); renderWhen();
      R.tab = 'notes'; R.filter = 'all';
      renderPanel(); drawMarks();
      toast(KIND[R.kind].emoji + ' נשמר', 'good');
    } catch (e) { toast(e.message, 'bad'); }
    addBtn.disabled = false;
  }

  /* ---------------- drawing */
  function renderDrawTools() {
    drawTools.innerHTML = '';
    drawTools.hidden = !R.draw;
    if (!R.draw) return;
    const tb = (t, ic, title) => h('button', { class: 'ctl' + (R.tool === t ? ' on' : ''), title, html: I[ic], onclick: () => { R.tool = t; renderDrawTools(); } });
    drawTools.append(tb('ellipse', 'circle', 'הקפה'), tb('arrow', 'arrow', 'חץ'), tb('pen', 'pen', 'עט חופשי'),
      ...COLORS.map((c) => h('button', { class: 'swatch' + (R.color === c ? ' on' : ''), style: `background:${c}`, title: 'צבע', onclick: () => { R.color = c; renderDrawTools(); } })),
      h('button', { class: 'ctl', title: 'בטל אחרון (Ctrl+Z)', html: I.undo, onclick: () => { R.strokes.pop(); paint(); } }));
  }
  function setDraw(on) {
    if (v.missing) return;
    R.draw = on; R.general = on ? false : R.general;
    if (on) { video.pause(); R.sel = null; }
    else R.strokes = [];
    screen.classList.toggle('drawing', on);
    drawHint.hidden = !on;
    renderModes(); renderDrawTools(); layoutCanvas(); paint();
  }
  function box() {
    const vw = video.videoWidth || v.w || 16, vh = video.videoHeight || v.h || 9;
    const cw = video.clientWidth, ch = video.clientHeight;
    const s = Math.min(cw / vw, ch / vh);
    const w = vw * s, hh = vh * s;
    return { x: video.offsetLeft + (cw - w) / 2, y: video.offsetTop + (ch - hh) / 2, w, h: hh };
  }
  function layoutCanvas() {
    const b = box(), dpr = window.devicePixelRatio || 1;
    Object.assign(canvas.style, { left: b.x + 'px', top: b.y + 'px', width: b.w + 'px', height: b.h + 'px' });
    canvas.width = Math.max(1, Math.round(b.w * dpr)); canvas.height = Math.max(1, Math.round(b.h * dpr));
    paint();
  }
  const ro = new ResizeObserver(() => layoutCanvas());
  ro.observe(screen);
  function strokesTo(ctx, strokes, W, H) {
    const lw = Math.max(3, Math.min(W, H) * 0.008);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    for (const s of strokes) {
      const P = s.pts.map(([x, y]) => [x * W, y * H]);
      if (!P.length) continue;
      ctx.strokeStyle = s.color; ctx.lineWidth = lw;
      ctx.shadowColor = 'rgba(0,0,0,.55)'; ctx.shadowBlur = lw * 1.2;
      ctx.beginPath();
      if (s.tool === 'pen') { P.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); }
      else if (s.tool === 'ellipse' && P[1]) {
        const cx = (P[0][0] + P[1][0]) / 2, cy = (P[0][1] + P[1][1]) / 2;
        ctx.ellipse(cx, cy, Math.max(2, Math.abs(P[1][0] - P[0][0]) / 2), Math.max(2, Math.abs(P[1][1] - P[0][1]) / 2), 0, 0, Math.PI * 2);
      } else if (s.tool === 'arrow' && P[1]) {
        const [a, b] = P, ang = Math.atan2(b[1] - a[1], b[0] - a[0]), L = lw * 4.5;
        ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
        ctx.moveTo(b[0], b[1]); ctx.lineTo(b[0] - L * Math.cos(ang - 0.5), b[1] - L * Math.sin(ang - 0.5));
        ctx.moveTo(b[0], b[1]); ctx.lineTo(b[0] - L * Math.cos(ang + 0.5), b[1] - L * Math.sin(ang + 0.5));
      }
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
  }
  function paint() {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let strokes = null;
    if (R.draw) strokes = R.strokes;
    else if (R.sel) {
      const n = R.st.notes.find((x) => x.id === R.sel);
      if (n && n.drawing && n.t != null && video.paused && Math.abs(video.currentTime - n.t) < 0.3) strokes = n.drawing;
    }
    if (strokes && strokes.length) strokesTo(ctx, strokes, canvas.width, canvas.height);
  }
  let cur = null;
  const norm = (e) => { const r = canvas.getBoundingClientRect(); return [Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)), Math.max(0, Math.min(1, (e.clientY - r.top) / r.height))]; };
  canvas.addEventListener('pointerdown', (e) => {
    if (!R.draw) return;
    canvas.setPointerCapture(e.pointerId);
    const p = norm(e);
    cur = { tool: R.tool, color: R.color, pts: R.tool === 'pen' ? [p] : [p, p] };
    R.strokes.push(cur); paint();
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!cur) return;
    const p = norm(e);
    if (cur.tool === 'pen') { const l = cur.pts[cur.pts.length - 1]; if (Math.hypot(p[0] - l[0], p[1] - l[1]) > 0.002) cur.pts.push(p); } else cur.pts[1] = p;
    paint();
  });
  canvas.addEventListener('pointerup', () => {
    if (!cur) return;
    if (cur.tool !== 'pen' && Math.hypot(cur.pts[1][0] - cur.pts[0][0], cur.pts[1][1] - cur.pts[0][1]) < 0.01) R.strokes.pop();
    cur.pts = cur.pts.map(([x, y]) => [Math.round(x * 10000) / 10000, Math.round(y * 10000) / 10000]);
    cur = null; paint();
    if (R.strokes.length === 1) { drawHint.textContent = 'מעולה. עכשיו כתוב מה לעשות שם ולחץ Enter'; ta.focus(); }
  });
  function framePng(strokes) {
    const vw = video.videoWidth, vh = video.videoHeight; if (!vw) return null;
    const s = Math.min(1, 1280 / Math.max(vw, vh));
    const c = document.createElement('canvas'); c.width = Math.round(vw * s); c.height = Math.round(vh * s);
    const ctx = c.getContext('2d');
    ctx.drawImage(video, 0, 0, c.width, c.height);
    strokesTo(ctx, strokes, c.width, c.height);
    return c.toDataURL('image/png');
  }

  /* ---------------- side panel */
  function renderTabs() {
    tabs.innerHTML = '';
    const ns = versionNotes();
    const t = (id, label, n) => h('button', { class: R.tab === id ? 'on' : '', onclick: () => { R.tab = id; renderPanel(); } }, label, n != null ? h('span', { class: 'cnt' }, n) : null);
    tabs.append(t('notes', 'הערות', ns.length), R.hasWords ? t('words', 'תמלול') : '', t('versions', 'גרסאות', R.st.versions.length));
  }
  function renderPanel() {
    renderTabs();
    pane.innerHTML = '';
    if (R.tab === 'notes') renderNotes();
    else if (R.tab === 'words') renderWords();
    else renderVersions();
    renderFoot();
  }
  function renderFoot() {
    const pend = versionNotes().filter((n) => n.state === 'pending');
    const pendFix = pend.filter((n) => n.kind === 'fix').length;
    sendBtn.innerHTML = ''; sendBtn.append(icon('send'), pend.length ? `שלח ל-Claude (${pend.length})` : 'שלח ל-Claude');
    sendBtn.disabled = !pend.length || v.missing;
    approveBtn.innerHTML = ''; approveBtn.append(icon('check'), v.approved_utc ? 'אושר ✓' : 'מאשר');
    approveBtn.disabled = pendFix > 0 || v.missing;
    approveBtn.title = pendFix ? 'יש הערות "לתקן" שעוד לא נשלחו: שלח אותן או מחק אותן' : 'אישור הגרסה: Claude ימשיך לרינדור הסופי ולמסירה';
    const open = versionNotes().filter((n) => n.state === 'open').length;
    footInfo.textContent = pend.length ? `${pend.length} הערות שמורות שעוד לא נשלחו` : open ? `${open} הערות מחכות. כתוב ל-Claude "יש הערות במחסן"` : v.approved_utc ? `אושר ${dateStr(v.approved_utc)}` : 'צפה, עצור, הקף וכתוב. אחר כך שלח הכל בבת אחת';
  }
  function renderNotes() {
    const all = versionNotes();
    const F = { all: ['הכל', () => true], fix: ['👎 לתקן', (n) => n.kind === 'fix'], like: ['👍 אהבתי', (n) => n.kind === 'like'], open: ['פתוחות', (n) => n.state === 'open' || n.state === 'pending'], resolved: ['טופלו', (n) => n.state === 'resolved'] };
    pane.appendChild(h('div', { class: 'nfilters' }, Object.entries(F).map(([k, [label, f]]) => {
      const c = all.filter(f).length;
      return h('button', { class: R.filter === k ? 'on' : '', onclick: () => { R.filter = k; renderPanel(); } }, `${label} ${c}`);
    })));
    const list = all.filter(F[R.filter][1]);
    if (!all.length) {
      pane.appendChild(h('div', { class: 'empty', style: 'padding:40px 10px' }, h('div', { class: 'big' }, '🎯'),
        h('div', {}, 'עוד אין הערות על ' + v.id), h('div', { style: 'font-size:12.5px;margin-top:8px;line-height:1.8' },
          'עצור איפה שבא לך ← בחר 👎 או 👍 ← כתוב. ', h('br'), 'רוצה להראות בדיוק איפה? ', h('b', {}, 'D'), ' לציור על הפריים.', h('br'), 'קטע: ', h('b', {}, 'I'), ' ו-', h('b', {}, 'O'), ' או גרירה עם Shift.')));
      return;
    }
    const tsort = (a, b) => (a.t == null) - (b.t == null) || (a.t || 0) - (b.t || 0);
    const pend = list.filter((n) => n.state === 'pending').sort(tsort);
    if (pend.length) { pane.appendChild(h('div', { class: 'round-sep' }, 'טיוטה · עוד לא נשלח')); pend.forEach((n) => pane.appendChild(noteCard(n))); }
    const rounds = [...new Set(list.filter((n) => n.round).map((n) => n.round))].sort((a, b) => b - a);
    for (const r of rounds) {
      const meta = R.st.rounds.find((x) => x.n === r);
      pane.appendChild(h('div', { class: 'round-sep' }, `סבב ${r}` + (meta ? ` · ${dateStr(meta.sent_utc)}` + (meta.approved ? ' · אושר ✓' : '') : '')));
      list.filter((n) => n.round === r).sort(tsort).forEach((n) => pane.appendChild(noteCard(n)));
    }
  }
  function noteCard(n) {
    const textEl = h('div', { class: 'note-text' }, n.text || (n.drawing ? '(ציור בלבד)' : ''));
    const tlabel = n.t == null ? 'כללי' : n.end != null ? `${fmtT(n.t)}–${fmtT(n.end)}` : fmtT(n.t);
    const acts = h('div', { class: 'note-acts' });
    let replyBox = null;
    if (n.state === 'pending') {
      acts.append(
        h('button', { class: 'btn sm ghost', onclick: (e) => { e.stopPropagation(); editNote(n, textEl, acts); } }, icon('edit'), 'ערוך'),
        h('button', { class: 'btn sm ghost', title: 'החלף סוג', onclick: async (e) => { e.stopPropagation(); const order = ['fix', 'like', 'note']; await noteOp({ action: 'update', id: n.id, kind: order[(order.indexOf(n.kind) + 1) % 3] }); } }, 'החלף סוג'),
        h('button', { class: 'btn sm ghost', style: 'color:var(--bad)', onclick: async (e) => { e.stopPropagation(); await noteOp({ action: 'delete', id: n.id }); toast('נמחק'); } }, icon('trash'), 'מחק'));
    } else {
      const rb = h('div', { class: 'reply-box', hidden: true });
      const ri = h('input', { class: 'inp', placeholder: 'תגובה…', onkeydown: async (e) => { if (e.key === 'Enter' && ri.value.trim()) { await noteOp({ action: 'reply', id: n.id, text: ri.value, reopen: true }); } } });
      rb.append(ri, h('button', { class: 'btn sm primary', onclick: async (e) => { e.stopPropagation(); if (ri.value.trim()) await noteOp({ action: 'reply', id: n.id, text: ri.value, reopen: true }); } }, 'שלח'));
      rb.addEventListener('click', (e) => e.stopPropagation());
      acts.append(h('button', { class: 'btn sm ghost', onclick: (e) => { e.stopPropagation(); rb.hidden = !rb.hidden; if (!rb.hidden) ri.focus(); } }, 'הגב'));
      if (n.state !== 'sent') acts.append(h('button', { class: 'btn sm ghost', onclick: async (e) => { e.stopPropagation(); await noteOp({ action: n.state === 'resolved' ? 'reopen' : 'resolve', id: n.id }); } }, n.state === 'resolved' ? 'פתח מחדש' : '✓ טופל'));
      if (n.end != null) acts.append(h('button', { class: 'btn sm ghost', onclick: (e) => { e.stopPropagation(); setRange(n.t, n.end); R.mode = 'range'; renderModes(); R.loop = true; loopBtn.classList.add('on'); seek(n.t); video.play(); } }, icon('play'), 'נגן קטע'));
      replyBox = rb;
    }
    const card = h('div', { class: `note k-${n.kind} ${n.state}` + (R.sel === n.id ? ' on' : ''), 'data-id': n.id, onclick: () => selectNote(n) },
      h('div', { class: 'note-h' }, h('span', { class: `k k-${n.kind}-c` }, KIND[n.kind].emoji + ' ' + KIND[n.kind].label), h('span', { class: 'tchip mono' }, tlabel),
        n.drawing ? h('span', { title: 'יש ציור', style: 'color:var(--muted)', html: I.draw }) : null, h('span', { class: 'grow' }), h('span', { class: 'state ' + n.state }, STATE[n.state] || n.state)),
      textEl,
      n.png ? h('img', { class: 'drw', src: `/drawing/${enc(slug)}/${n.png.split('/').pop()}`, alt: 'הפריים עם הציור', loading: 'lazy' }) : null,
      (n.replies || []).map((r) => h('div', { class: 'reply ' + (r.author === 'claude' ? 'claude' : '') }, h('div', { class: 'who' }, r.author === 'claude' ? '✦ Claude' : 'אתה', h('span', { style: 'font-weight:500' }, rel(r.utc))), r.text)),
      acts, replyBox);
    return card;
  }
  function editNote(n, textEl, acts) {
    textEl.contentEditable = 'true'; textEl.focus();
    document.getSelection().selectAllChildren(textEl);
    const done = async (save) => {
      textEl.contentEditable = 'false';
      if (save && textEl.textContent.trim() !== n.text) await noteOp({ action: 'update', id: n.id, text: textEl.textContent });
      else textEl.textContent = n.text;
    };
    textEl.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); done(true); } if (e.key === 'Escape') { e.stopPropagation(); done(false); } });
    textEl.addEventListener('blur', () => done(true), { once: true });
    textEl.addEventListener('click', (e) => e.stopPropagation());
  }
  async function noteOp(body) {
    try { const r = await api(`/api/project/${enc(slug)}/note`, body); R.st = r.state; R.rev = r.state.updated_utc; renderPanel(); drawMarks(); }
    catch (e) { toast(e.message, 'bad'); }
  }
  function selectNote(n, scroll) {
    R.sel = n.id;
    if (R.draw) setDraw(false);
    video.pause();
    if (n.t != null) seek(n.t);
    if (n.end != null) setRange(n.t, n.end); else if (R.mode === 'point') setRange(null, null);
    if (R.tab !== 'notes') { R.tab = 'notes'; }
    renderPanel(); drawMarks();
    if (scroll) { const el = pane.querySelector(`[data-id="${n.id}"]`); if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
    setTimeout(paint, 60);
  }

  /* ---------------- transcript */
  let wordEls = [], lastWord = -1, hits = [], hitAt = -1;
  async function renderWords() {
    if (!R.words) { pane.appendChild(h('div', { class: 'empty' }, 'טוען תמלול…')); try { R.words = (await api(`/api/project/${enc(slug)}/transcript`)).words || []; } catch (e) { R.words = []; } if (R.tab === 'words') { pane.innerHTML = ''; renderWords(); } return; }
    const W = R.words;
    const q = h('input', { class: 'inp', placeholder: 'חיפוש בתמלול… (Enter לתוצאה הבאה)' });
    const cnt = h('span', { class: 'foot-note' });
    pane.append(h('div', { style: 'display:flex;gap:8px;align-items:center;margin-bottom:10px' }, q, cnt),
      h('div', { class: 'foot-note', style: 'text-align:start;margin-bottom:8px' }, 'לחיצה על מילה קופצת אליה · Shift+לחיצה על מילה שנייה מסמנת קטע להערה'));
    const body = h('div');
    wordEls = []; lastWord = -1;
    let line = null, count = 0;
    W.forEach((w, i) => {
      const prev = W[i - 1];
      if (!line || (prev && w.s - prev.e > 0.7) || count >= 11 || (prev && /[.?!]$/.test(prev.w))) {
        count = 0;
        const ws = w.s;
        const tEl = h('span', { class: 'mono', onclick: () => seek(ws) }, fmtT(w.s, false));
        line = h('div', { class: 'tr-line' }, tEl, h('div'));
        body.appendChild(line);
      }
      const el = h('span', { class: 'w', onclick: (e) => wordClick(i, e) }, w.w);
      wordEls.push(el);
      line.lastChild.append(el, ' ');
      count++;
    });
    pane.appendChild(body);
    q.addEventListener('input', () => {
      const s = q.value.trim();
      hits = []; hitAt = -1;
      wordEls.forEach((el, i) => { const m = s && W[i].w.includes(s); el.classList.toggle('hit', !!m); if (m) hits.push(i); });
      cnt.textContent = s ? `${hits.length} תוצאות` : '';
    });
    q.addEventListener('keydown', (e) => { if (e.key === 'Enter' && hits.length) { hitAt = (hitAt + 1) % hits.length; const i = hits[hitAt]; seek(W[i].s); wordEls[i].scrollIntoView({ block: 'center', behavior: 'smooth' }); } });
    highlightWord(video.currentTime, true);
  }
  function wordClick(i, e) {
    const W = R.words;
    if (e.shiftKey && R.picked != null) {
      const a = Math.min(R.picked, i), b = Math.max(R.picked, i);
      wordEls.forEach((el, k) => el.classList.toggle('picked', k >= a && k <= b));
      R.mode = 'range'; R.general = false; renderModes();
      setRange(W[a].s, Math.max(W[b].e, W[a].s + 0.1));
      seek(W[a].s);
      const quote = W.slice(a, b + 1).map((x) => x.w).join(' ');
      if (!ta.value.trim()) ta.value = `«${quote}» `;
      ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
      R.picked = null;
      return;
    }
    R.picked = i;
    wordEls.forEach((el, k) => el.classList.toggle('picked', k === i));
    seek(W[i].s);
  }
  function highlightWord(t, force) {
    if (R.tab !== 'words' || !R.words || !wordEls.length) return;
    const W = R.words;
    let lo = 0, hi = W.length - 1, k = -1;
    while (lo <= hi) { const m = (lo + hi) >> 1; if (W[m].s <= t) { k = m; lo = m + 1; } else hi = m - 1; }
    if (k >= 0 && t > W[k].e + 0.4) k = -1;
    if (k === lastWord && !force) return;
    if (lastWord >= 0 && wordEls[lastWord]) wordEls[lastWord].classList.remove('now');
    lastWord = k;
    if (k >= 0) { wordEls[k].classList.add('now'); if (!video.paused) wordEls[k].scrollIntoView({ block: 'nearest' }); }
  }

  /* ---------------- versions + compare */
  function renderVersions() {
    [...R.st.versions].reverse().forEach((x) => {
      const n = R.st.notes.filter((m) => m.version === x.id).length;
      pane.appendChild(h('div', { class: 'ver' + (x.id === v.id ? ' on' : ''), onclick: () => { if (!x.missing) location.hash = `#/p/${enc(slug)}/${x.id}`; } },
        x.missing ? h('div', { style: 'width:54px;height:72px;border-radius:8px;background:var(--panel2);display:grid;place-items:center;color:var(--faint);font-size:11px' }, 'נמחק') : h('img', { src: `/thumb/${enc(slug)}/${x.id}.jpg`, alt: '' }),
        h('div', { class: 'vi' }, h('b', {}, x.id + (x.approved_utc ? ' · אושר ✓' : '') + (x.draft ? ' · טיוטה' : '')), h('span', { title: x.file }, x.label),
          h('span', {}, `${dateStr(x.added_utc)}` + (x.duration ? ` · ${fmtT(x.duration, false)}` : '') + (n ? ` · ${n} הערות` : ''))),
        x.id !== v.id && !x.missing && !v.missing ? h('button', { class: 'btn sm', onclick: (e) => { e.stopPropagation(); startCompare(x); } }, icon('cmp'), 'השווה') : null));
    });
  }
  function compareMenu(anchor) {
    if (R.cmp) return stopCompare();
    menu(anchor, live.filter((x) => x.id !== v.id).map((x) => ({ label: `${v.id} מול ${x.id}`, hint: x.label, icon: 'cmp', fn: () => startCompare(x) })));
  }
  function startCompare(x) {
    stopCompare(true);
    R.cmp = x.id;
    video2 = h('video', { src: `/media/${enc(slug)}/${x.id}`, preload: 'auto', muted: true, playsinline: true });
    video2.muted = true;
    video2.addEventListener('loadedmetadata', () => { video2.currentTime = video.currentTime; });
    screen2 = h('div', { class: 'screen' }, video2, h('div', { class: 'tcchip mono' }, x.id + ' · ' + x.label));
    screen.appendChild(h('div', { class: 'tcchip mono', style: 'top:auto;bottom:12px', 'data-cmp': '1' }, v.id + ' (הסאונד מכאן)'));
    stage.prepend(screen2);
    cmpBtn.innerHTML = ''; cmpBtn.append(icon('cmp'), 'סגור השוואה');
    video2.playbackRate = video.playbackRate;
    setTimeout(layoutCanvas, 50);
  }
  function stopCompare(silent) {
    if (screen2) { screen2.remove(); screen2 = null; video2 = null; }
    const lab = screen.querySelector('[data-cmp]'); if (lab) lab.remove();
    R.cmp = null;
    cmpBtn.innerHTML = ''; cmpBtn.append(icon('cmp'), 'השווה');
    if (!silent) setTimeout(layoutCanvas, 50);
  }

  /* ---------------- send / approve */
  async function sendRound() {
    const pend = versionNotes().filter((n) => n.state === 'pending');
    if (!pend.length) return;
    sendBtn.disabled = true;
    try {
      const r = await api(`/api/project/${enc(slug)}/send`, { version: v.id });
      R.st = r.state; R.rev = r.state.updated_utc;
      statusSel.value = R.st.status;
      renderPanel(); drawMarks();
      handoff(`יש הערות חדשות במחסן על ${slug} (סבב ${r.round}). תטפל בהן.`, `✓ ${pend.length} הערות נשמרו (סבב ${r.round})`);
    } catch (e) { toast(e.message, 'bad'); renderFoot(); }
  }
  function approve() {
    const likes = versionNotes().filter((n) => n.state === 'pending').length;
    modal((box, close) => {
      box.append(h('h3', {}, `לאשר את ${v.id}?`),
        h('p', {}, 'Claude ימשיך מכאן לרינדור הסופי, לבדיקות ולמסירה.' + (likes ? ` ${likes} ההערות השמורות (אהבתי / הערה) יישלחו יחד עם האישור.` : '')),
        h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: close }, 'עוד לא'), h('button', { class: 'btn good', onclick: async () => {
          try {
            const r = await api(`/api/project/${enc(slug)}/approve`, { version: v.id });
            R.st = r.state; R.rev = r.state.updated_utc; Object.assign(v, R.st.versions.find((x) => x.id === v.id));
            statusSel.value = R.st.status; close(); renderPanel(); drawMarks(); confetti();
            handoff(`אישרתי במחסן את ${v.id} של ${slug}. תמשיך לרינדור הסופי ולמסירה.`, `✓ ${v.id} אושר 🎉`);
          } catch (e) { toast(e.message, 'bad'); }
        } }, icon('check'), 'מאשר')));
    });
  }

  /* ---------------- keyboard + live refresh */
  function onKey(e) {
    if ($('#modal').hidden === false) return;
    if (isTyping(document.activeElement)) return;
    const k = e.key;
    if (k === ' ' || k === 'k' || k === 'K') { e.preventDefault(); togglePlay(); }
    else if (k === 'ArrowLeft') { e.preventDefault(); e.shiftKey ? seek(video.currentTime - 1) : stepFrame(-1); }
    else if (k === 'ArrowRight') { e.preventDefault(); e.shiftKey ? seek(video.currentTime + 1) : stepFrame(1); }
    else if (k === 'i' || k === 'I' || k === 'ן') markIn();
    else if (k === 'o' || k === 'O' || k === 'ם') markOut();
    else if (k === 'c' || k === 'C' || k === 'ב') { e.preventDefault(); setMode('point'); ta.focus(); }
    else if (k === 'r' || k === 'R' || k === 'ר') setMode(R.mode === 'range' ? 'point' : 'range');
    else if (k === 'd' || k === 'D' || k === 'ג') setDraw(!R.draw);
    else if (k === 'm' || k === 'M' || k === 'צ') muteBtn.click();
    else if (k === 'f' || k === 'F' || k === 'כ') { document.fullscreenElement ? document.exitFullscreen() : screen.requestFullscreen(); }
    else if (k === '1') { R.kind = 'fix'; renderKinds(); } else if (k === '2') { R.kind = 'like'; renderKinds(); } else if (k === '3') { R.kind = 'note'; renderKinds(); }
    else if ((e.ctrlKey || e.metaKey) && (k === 'z' || k === 'ז') && R.draw) { R.strokes.pop(); paint(); }
    else if (k === 'Escape') { if (R.draw) setDraw(false); else if (R.inT != null) { setRange(null, null); setMode('point'); } else if (R.sel) { R.sel = null; renderPanel(); drawMarks(); paint(); } }
  }
  document.addEventListener('keydown', onKey);
  const poll = setInterval(async () => {
    if (document.hidden) return;
    try {
      const r = await api(`/api/project/${enc(slug)}/rev`);
      if (r.updated_utc !== R.rev && !isTyping(document.activeElement)) {
        const d = await api(`/api/project/${enc(slug)}`);
        const hadReplies = R.st.notes.reduce((a, n) => a + (n.replies || []).filter((x) => x.author === 'claude').length, 0);
        R.st = d.state; R.rev = d.state.updated_utc; statusSel.value = R.st.status;
        const nowReplies = R.st.notes.reduce((a, n) => a + (n.replies || []).filter((x) => x.author === 'claude').length, 0);
        renderPanel(); drawMarks();
        if (nowReplies > hadReplies) toast('✦ Claude ענה על הערות', 'good');
        if (R.st.versions.length > verSel.options.length) toast('✦ יש גרסה חדשה. פתח את לשונית הגרסאות', 'good');
      }
    } catch (e) { /* server restarting */ }
  }, 4000);
  cleanup = () => { document.removeEventListener('keydown', onKey); clearInterval(poll); cancelAnimationFrame(raf); ro.disconnect(); video.pause(); video.removeAttribute('src'); video.load(); };

  renderKinds(); renderModes(); renderWhen(); renderPanel();
  if (v.missing) { composer.hidden = true; controls.hidden = true; tl.hidden = true; }
}


/* ---------------------------------------------------------------- import wizard (card -> project/source, verified) */
function slugify(s) {
  const map = { 'א': 'a', 'ב': 'b', 'ג': 'g', 'ד': 'd', 'ה': 'h', 'ו': 'v', 'ז': 'z', 'ח': 'ch', 'ט': 't', 'י': 'y', 'כ': 'k', 'ך': 'k', 'ל': 'l', 'מ': 'm', 'ם': 'm', 'נ': 'n', 'ן': 'n', 'ס': 's', 'ע': 'a', 'פ': 'p', 'ף': 'f', 'צ': 'tz', 'ץ': 'tz', 'ק': 'k', 'ר': 'r', 'ש': 'sh', 'ת': 't' };
  return [...(s || '').toLowerCase()].map((c) => map[c] ?? c).join('').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40);
}
const today = () => new Date().toISOString().slice(0, 10).replace(/-/g, '');
function importWizard(presetProject, presetClient) {
  const W = { step: 1, scan: null, sel: new Set(), target: presetProject ? 'existing' : 'new', project: presetProject || '', client: presetClient || '', title: '', slug: '', slugTouched: false, job: null, free: null,
    month: '', libRoot: null, libClients: [], inLib: false };
  const under = (p, r) => !!(p && r) && (p.toLowerCase() + '\\').startsWith(r.toLowerCase().replace(/\\+$/, '') + '\\');
  let box, timer = null;
  modal((b, close) => { box = b; box.classList.add('wide'); W.close = () => { clearInterval(timer); close(); }; });
  const projs = LIB ? LIB.projects : [];
  const clients = [...new Set(projs.map((p) => p.client))];
  function head(n) {
    box.innerHTML = '';
    box.append(h('h3', {}, '📥 קליטת חומר'),
      h('div', { class: 'steps' }, ['מקור', 'בחירת קבצים', 'לאן', 'העתקה ובדיקה'].map((t, i) => h('span', { class: i + 1 === n ? 'on' : '' }, `${i + 1}. ${t}`))));
  }
  function render() {
    if (W.step === 1) return stepSource();
    if (W.step === 2) return stepPick();
    if (W.step === 3) return stepTarget();
    return stepCopy();
  }
  async function stepSource() {
    head(1);
    box.append(h('p', {}, 'בחר את הכרטיס או את המצלמה. המחסן רק קורא מהכרטיס, ואף פעם לא כותב או מוחק בו.'));
    const list = h('div', { class: 'drives' }, h('div', { class: 'foot-note' }, 'מחפש כוננים…'));
    const path = h('input', { class: 'inp mono', placeholder: 'D:\\DCIM', style: 'text-align:left' });
    box.append(list, h('div', { class: 'field', style: 'margin-top:16px' }, h('label', {}, 'או נתיב לתיקייה (גם תיקייה במחשב)'),
      h('div', { style: 'display:flex;gap:8px' }, path, h('button', { class: 'btn', onclick: () => path.value.trim() && doScan(path.value.trim()) }, 'סרוק'))),
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: W.close }, 'ביטול')));
    path.addEventListener('keydown', (e) => { if (e.key === 'Enter' && path.value.trim()) doScan(path.value.trim()); });
    try {
      const d = await api('/api/drives', {});
      W.free = d.projects_free; W.month = W.month || d.month; W.libRoot = d.library_root; W.libClients = d.library_clients || [];
      list.innerHTML = '';
      if (W.libRoot) list.appendChild(h('button', { class: 'drive card', onclick: () => browse(W.libRoot) }, h('span', { class: 'big' }, '📁'),
        h('div', {}, h('b', {}, 'חומר שכבר בתיקיות שלך'), h('span', {}, 'מקשר לפרויקט בלי להעתיק. 0 MB נוספים'))));
      const ds = d.drives.filter((x) => !x.root.toUpperCase().startsWith('C:'));
      if (!ds.length) list.appendChild(h('div', { class: 'foot-note', style: 'text-align:start' }, 'לא מצאתי כרטיס. הכנס אותו לקורא (או חבר את המצלמה) ולחץ "רענן". אפשר גם להקליד נתיב למטה.'));
      ds.forEach((x) => list.appendChild(h('button', { class: 'drive' + (x.type === 'removable' || x.camera ? ' card' : ''), onclick: () => doScan(x.root) },
        h('span', { class: 'big' }, x.camera ? '📷' : x.type === 'removable' ? '💾' : x.type === 'network' ? '🌐' : '🖴'),
        h('div', {}, h('b', {}, `${x.label || 'כונן'} (${x.root.slice(0, 2)})`), h('span', {}, `${bytes(x.total - x.free)} בשימוש מתוך ${bytes(x.total)}` + (x.camera ? ' · כרטיס מצלמה' : ''))))));
      list.appendChild(h('button', { class: 'drive', onclick: () => stepSource() }, h('span', { class: 'big' }, '🔄'), h('div', {}, h('b', {}, 'רענן'), h('span', {}, 'אחרי שהכנסת כרטיס'))));
    } catch (e) { list.innerHTML = ''; list.appendChild(h('div', { class: 'errbox' }, e.message)); }
  }
  async function browse(path) {
    head(1);
    let d;
    try { d = await api('/api/listdir', { path }); } catch (e) { toast(e.message, 'bad'); return stepSource(); }
    const rel = d.path.length > d.root.length ? d.path.slice(d.root.length + 1) : '';
    box.append(h('p', {}, 'בחר את התיקייה שבה הגלם יושב (למשל הלקוח ← החודש ← גלם), ולחץ "זו התיקייה".'),
      h('div', { class: 'crumb-path' }, '📁 ' + (rel || d.root.split(/[\\/]/).pop())),
      h('div', { class: 'dirs' }, d.parent ? h('button', { class: 'dirrow', onclick: () => browse(d.parent) }, '↩', 'למעלה') : '',
        d.dirs.map((n) => h('button', { class: 'dirrow', onclick: () => browse(d.path + '\\' + n) }, n.startsWith('גלם') ? '🎞' : n.startsWith('מוכנים') ? '✅' : '📁', n))),
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: () => stepSource() }, 'חזור'),
        rel ? h('button', { class: 'btn primary', onclick: () => doScan(d.path) }, 'זו התיקייה') : ''));
  }
  async function doScan(path) {
    head(1);
    box.append(h('div', { class: 'empty', style: 'padding:50px' }, h('div', { class: 'big' }, '🔎'), `סורק את ${path}…`));
    try {
      W.scan = await api('/api/scan', { path });
      W.sel = new Set(W.scan.files.map((f) => f.path));
      W.inLib = under(W.scan.base, W.libRoot);
      if (W.inLib && !W.client) W.client = W.scan.base.slice(W.libRoot.replace(/\\+$/, '').length + 1).split('\\')[0];
      if (!W.scan.files.length) { toast('לא נמצאו קבצי וידאו, אודיו או תמונות בתיקייה הזו', 'bad'); return stepSource(); }
      W.step = 2; render();
    } catch (e) { toast(e.message, 'bad'); stepSource(); }
  }
  function stepPick() {
    head(2);
    const files = W.scan.files;
    const selBytes = () => files.filter((f) => W.sel.has(f.path)).reduce((a, f) => a + f.size, 0);
    const summary = h('b');
    const next = h('button', { class: 'btn primary', onclick: () => { W.step = 3; render(); } }, 'המשך');
    const upd = () => { summary.textContent = `נבחרו ${W.sel.size} מתוך ${files.length} קבצים · ${bytes(selBytes())}`; next.disabled = !W.sel.size; };
    const kinds = { video: '🎬 וידאו', audio: '🎙 אודיו', photo: '📷 תמונות' };
    const kindBtns = Object.entries(kinds).filter(([k]) => files.some((f) => f.kind === k)).map(([k, label]) => {
      const of = files.filter((f) => f.kind === k);
      return h('button', { class: 'btn sm', title: 'סמן / בטל את כל הסוג הזה', onclick: () => { const all = of.every((f) => W.sel.has(f.path)); of.forEach((f) => (all ? W.sel.delete(f.path) : W.sel.add(f.path))); paint(); } }, `${label} ${of.length}`);
    });
    const list = h('div', { class: 'scroll' });
    function paint() {
      list.querySelectorAll('.clip').forEach((c) => c.classList.toggle('on', W.sel.has(c.dataset.p)));
      list.querySelectorAll('[data-g]').forEach((cb) => { const g = files.filter((f) => f.folder === cb.dataset.g); cb.checked = g.every((f) => W.sel.has(f.path)); cb.indeterminate = !cb.checked && g.some((f) => W.sel.has(f.path)); });
      upd();
    }
    const groups = {};
    files.forEach((f) => (groups[f.folder] = groups[f.folder] || []).push(f));
    for (const [g, fs] of Object.entries(groups)) {
      const cb = h('input', { type: 'checkbox', 'data-g': g, onchange: (e) => { fs.forEach((f) => (e.target.checked ? W.sel.add(f.path) : W.sel.delete(f.path))); paint(); } });
      list.appendChild(h('div', { class: 'fgroup' },
        h('label', { class: 'fgroup-h' }, cb, h('span', { class: 'mono' }, g === '.' ? '(ראשי)' : g), h('span', { style: 'margin-inline-start:auto;color:var(--muted);font-weight:500' }, `${fs.length} קבצים · ${bytes(fs.reduce((a, f) => a + f.size, 0))}`)),
        h('div', { class: 'clips' }, fs.map((f) => h('div', { class: 'clip', 'data-p': f.path, title: `${f.name} · ${bytes(f.size)} · ${new Date(f.mtime * 1000).toLocaleString('he-IL')}`, onclick: () => { W.sel.has(f.path) ? W.sel.delete(f.path) : W.sel.add(f.path); paint(); } },
          f.kind === 'audio' ? h('div', { class: 'ic' }, '🎙') : h('img', { src: '/clipthumb?path=' + enc(f.path), loading: 'lazy', alt: '', onerror: (e) => e.target.replaceWith(h('div', { class: 'ic' }, f.kind === 'photo' ? '📷' : '🎬')) }),
          h('span', { class: 'ck' }, '✓'), h('span', { class: 'nm' }, f.name))))));
    }
    box.append(h('div', { class: 'pick-head' }, summary, h('div', { class: 'grow' }), ...kindBtns,
      h('button', { class: 'btn sm', onclick: () => { files.forEach((f) => W.sel.add(f.path)); paint(); } }, 'הכל'),
      h('button', { class: 'btn sm ghost', onclick: () => { W.sel.clear(); paint(); } }, 'נקה')),
      W.scan.truncated ? h('div', { class: 'errbox' }, `יש יותר מ-${files.length} קבצים. בחר תיקייה מצומצמת יותר.`) : '',
      list, h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: () => { W.step = 1; render(); } }, 'חזור'), next));
    paint();
  }
  function stepTarget() {
    head(3);
    const total = W.scan.files.filter((f) => W.sel.has(f.path)).reduce((a, f) => a + f.size, 0);
    const seg = h('div', { class: 'seg radio-row' },
      h('button', { class: W.target === 'new' ? 'on' : '', onclick: () => { W.target = 'new'; stepTarget(); } }, '✨ פרויקט חדש'),
      h('button', { class: W.target === 'existing' ? 'on' : '', disabled: !projs.length, onclick: () => { W.target = 'existing'; stepTarget(); } }, '➕ להוסיף לפרויקט קיים'));
    const body = h('div');
    const go = h('button', { class: 'btn primary lg', onclick: () => start() }, W.inLib ? '🔗 קשר לפרויקט' : `התחל קליטה · ${bytes(total)}`);
    const err = h('div', { class: 'errbox', hidden: true });
    if (W.target === 'new') {
      const client = h('input', { class: 'inp', value: W.client, list: 'wiz-clients', placeholder: 'למשל: שם הלקוח' });
      const title = h('input', { class: 'inp', value: W.title, placeholder: 'למשל: יום צילום 1, ראיון ובירולים' });
      const slug = h('input', { class: 'inp mono', value: W.slug, style: 'text-align:left' });
      const auto = () => { if (!W.slugTouched) { W.slug = (slugify(W.client) || 'shoot') + '-' + today(); slug.value = W.slug; } };
      client.addEventListener('input', () => { W.client = client.value; auto(); });
      title.addEventListener('input', () => { W.title = title.value; });
      slug.addEventListener('input', () => { W.slugTouched = true; W.slug = slug.value.toLowerCase(); });
      if (!W.slug) auto();
      const month = h('input', { class: 'inp', value: W.month, placeholder: 'אוקטובר 26' });
      const where = h('div', { class: 'hint mono', style: 'text-align:start' });
      const paintWhere = () => { where.textContent = W.inLib ? 'הגלם נשאר איפה שהוא: ' + W.scan.base : W.libRoot ? `הגלם יישמר ב: ${W.libRoot}\\${W.client || '<לקוח>'}\\${W.month ? W.month + '\\' : ''}גלם` : ''; };
      client.addEventListener('input', paintWhere); month.addEventListener('input', () => { W.month = month.value; paintWhere(); });
      paintWhere();
      body.append(h('div', { class: 'field' }, h('label', {}, 'לקוח (תיקיית הלקוח אצלך)'), client, h('datalist', { id: 'wiz-clients' }, [...new Set([...W.libClients, ...clients])].map((c) => h('option', { value: c })))),
        !W.inLib && W.libRoot ? h('div', { class: 'field' }, h('label', {}, 'תיקיית חודש'), month, h('span', { class: 'hint' }, 'כמו שאתה עובד היום. אפשר להשאיר ריק אם לא צריך.')) : '',
        h('div', { class: 'field' }, where),
        h('div', { class: 'field' }, h('label', {}, 'שם הפרויקט (מה שתראה במחסן)'), title),
        h('div', { class: 'field' }, h('label', {}, 'שם התיקייה במחשב'), slug, h('span', { class: 'hint' }, 'באנגלית בלבד, כי הכלים של העריכה צריכים נתיב בלי עברית. נוצר אוטומטית, ואפשר לשנות.')));
    } else {
      if (!W.project && projs[0]) W.project = projs[0].slug;
      const sel = h('select', { class: 'sel', style: 'width:100%', onchange: (e) => { W.project = e.target.value; } },
        projs.map((p) => h('option', { value: p.slug, selected: p.slug === W.project }, `${p.title} · ${p.client}`)));
      body.append(h('div', { class: 'field' }, h('label', {}, 'לאיזה פרויקט'), sel, h('span', { class: 'hint' }, 'למשל יום צילום שני לאותו סרטון. קבצים שכבר נמצאים בפרויקט לא יועתקו שוב.')));
    }
    const enough = W.inLib || W.free == null || total + (2 * 1024 ** 3) <= W.free;
    box.append(seg, body,
      h('div', { class: 'keep' }, W.inLib ? `${W.sel.size} קבצים (${bytes(total)}) יקושרו לפרויקט העבודה של Claude בלי להעתיק: אותו קובץ, שני שמות, 0 MB נוספים. התיקייה שלך לא משתנה.`
        : `יועתקו ${W.sel.size} קבצים (${bytes(total)}) פעם אחת לתיקייה שלך, וכל קובץ ייבדק מול הכרטיס. הפרויקט של Claude יקבל אותם כקישור, בלי עותק נוסף.` + (W.free != null ? ` פנוי בדיסק: ${bytes(W.free)}.` : '')),
      !enough ? h('div', { class: 'errbox' }, 'אין מספיק מקום בדיסק. צמצם עבודות ישנות או מחק גלם של פרויקטים שנמסרו, ואז נסה שוב.') : '',
      err, h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: () => { W.step = 2; render(); } }, 'חזור'), go));
    go.disabled = !enough;
    async function start() {
      err.hidden = true;
      const payload = { files: W.scan.files.filter((f) => W.sel.has(f.path)).map((f) => f.path) };
      if (W.target === 'existing') payload.project = W.project;
      else {
        if (!W.client.trim()) { err.hidden = false; err.textContent = 'כתוב שם לקוח'; return; }
        if (!/^[a-z0-9][a-z0-9-]{1,60}$/.test(W.slug)) { err.hidden = false; err.textContent = 'שם התיקייה: אותיות באנגלית קטנות, ספרות ומקפים'; return; }
        payload.new = { client: W.client.trim(), title: W.title.trim() || W.client.trim(), slug: W.slug };
        if (!W.inLib && W.libRoot) payload.library = { client: W.client.trim(), month: (W.month || '').trim() };
      }
      go.disabled = true; go.textContent = 'מתחיל…';
      try { const r = await api('/api/import', payload); W.job = r.job; W.project = r.project; W.step = 4; render(); }
      catch (e) { go.disabled = false; go.textContent = 'התחל קליטה'; err.hidden = false; err.textContent = e.message; }
    }
  }
  function stepCopy() {
    head(4);
    const bar = h('i', { style: 'width:0%' }), meta = h('div', { class: 'prog-meta' }), cur = h('div', { class: 'foot-note', style: 'text-align:start;direction:ltr' });
    const result = h('div');
    const acts = h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: W.close }, 'הסתר (ההעתקה ממשיכה ברקע)'));
    const lead = h('p', {}, 'מעתיק ובודק… אל תוציא את הכרטיס עד שיופיע ✓.');
    box.append(lead, h('div', { class: 'bar' }, bar), meta, cur, result, acts);
    let lastB = 0, lastT = Date.now(), speed = 0;
    const tick = async () => {
      if (!document.body.contains(box)) { clearInterval(timer); return; }  // closed with Esc: the copy goes on in the background
      let j;
      try { j = await api('/api/jobs/' + W.job); } catch (e) { return; }
      bar.style.width = (j.bytes_total ? (j.bytes_done / j.bytes_total) * 100 : 100).toFixed(1) + '%';
      const dt = (Date.now() - lastT) / 1000;
      if (dt > 0.5) { const s = (j.bytes_done - lastB) / dt; speed = speed ? speed * 0.7 + s * 0.3 : s; lastB = j.bytes_done; lastT = Date.now(); }
      const eta = speed > 0 ? (j.bytes_total - j.bytes_done) / speed : 0;
      meta.innerHTML = '';
      meta.append(h('span', {}, `${j.files_done} / ${j.files_total} קבצים · ${bytes(j.bytes_done)} מתוך ${bytes(j.bytes_total)}`),
        h('span', {}, j.state === 'running' && speed > 0 ? `${bytes(speed)} לשנייה · נותרו ${eta > 90 ? Math.round(eta / 60) + ' דק׳' : Math.round(eta) + ' שנ׳'}` : ''));
      cur.textContent = j.state === 'running' ? (j.phase === 'check' ? 'בודק: ' : 'מעתיק: ') + j.current : '';
      if (j.state === 'running') return;
      clearInterval(timer);
      const copied = j.files_done - j.skipped - j.errors.length;
      result.innerHTML = '';
      lead.textContent = j.errors.length ? 'הקליטה הסתיימה, אבל לא הכל עבר:' : 'הקליטה הסתיימה.';
      result.append(h('div', { class: 'okbox' }, h('b', {}, j.errors.length ? `⚠ ${copied} קבצים הועתקו ונבדקו, ${j.errors.length} נכשלו`
        : j.mode === 'link' ? `✓ ${j.files_total} קבצים קושרו לפרויקט, בלי העתקה` : copied ? `✓ כל ${copied} הקבצים הועתקו ונבדקו מול הכרטיס` : '✓ הכל כבר היה בפרויקט, לא היה צריך להעתיק כלום'),
        j.skipped ? h('div', {}, `${j.skipped} קבצים כבר היו בפרויקט (אותו תוכן בדיוק), אז דילגתי עליהם.`) : '',
        !j.errors.length && j.mode !== 'link' ? h('div', { style: 'margin-top:6px' }, 'אפשר להוציא את הכרטיס. בשבועות הראשונים עם המחסן: לא לפרמט אותו עד שהסרטון נמסר.') : ''));
      if (j.errors.length) result.append(h('div', { class: 'errbox' }, 'הקבצים האלה לא הועתקו. אפשר לנסות שוב, וקבצים שכבר עברו לא יועתקו פעמיים:', h('ul', {}, j.errors.slice(0, 8).map((e) => h('li', { class: 'mono', style: 'text-align:left' }, e.file + ' – ' + e.error)))));
      const msg = `יש גלם חדש במחסן: ${W.project}. בוא נתחיל.`;
      acts.innerHTML = '';
      acts.append(h('button', { class: 'btn', onclick: async () => { try { await navigator.clipboard.writeText(msg); toast('הועתק. הדבק בשיחה חדשה עם Claude', 'good'); } catch (e) { toast(msg); } } }, '📋 העתק הודעה ל-Claude'),
        h('button', { class: 'btn primary', onclick: () => { W.close(); location.hash = '#/'; route(); } }, 'סיום'));
      if (!j.errors.length) confetti();
    };
    timer = setInterval(tick, 700);
    tick();
  }
  render();
}
async function deleteRaw(p) {
  let info;
  try { info = await api(`/api/project/${enc(p.slug)}/raw-info`, {}); } catch (e) { return toast(e.message, 'bad'); }
  if (!info.files) return toast('אין גלם בפרויקט הזה');
  typedConfirm(`למחוק את הגלם של "${p.title}"?`,
    `${info.files} קבצי גלם (${bytes(info.bytes)}) מהתיקייה source עוברים לסל המיחזור. נשארים: הסרטונים הסופיים, קוד העריכה והמדיה המעובדת שלה, וכל ההערות. עדיין אפשר לתקן כתוביות, טקסט וצבע ולרנדר מחדש, אבל אי אפשר לבחור טייקים חדשים מהגלם. אם הגלם גדול מדי לסל, Windows יפתח חלון ויבקש אישור לפני מחיקה לצמיתות.`,
    p.slug, 'מחק גלם', async () => { await api(`/api/project/${enc(p.slug)}/delete-raw`, { confirm: p.slug }); toast('הגלם הועבר לסל המיחזור 🎞'); route(); });
}
async function duplicatesFlow() {
  toast('מחפש עותקים כפולים…');
  let d;
  try { d = await api('/api/duplicates', {}); } catch (e) { return toast(e.message, 'bad'); }
  if (!d.files.length) return toast('אין עותקים כפולים ✓', 'good');
  modal((box, close) => {
    box.append(h('h3', {}, 'עותקים כפולים בתיקייה incoming'),
      h('p', {}, 'הקבצים האלה זהים בדיוק (נבדק לפי תוכן) לקבצים שכבר נמצאים בתיקיות source של הפרויקטים. מחיקה שלהם לא מוחקת שום חומר.'),
      h('div', { class: 'total' }, bytes(d.bytes)), h('div', { style: 'color:var(--muted);font-size:12.5px' }, `${d.files.length} קבצים יתפנו`),
      h('table', {}, d.files.slice(0, 10).map((f) => h('tr', {}, h('td', { class: 'mono', style: 'text-align:left' }, f.rel), h('td', {}, bytes(f.bytes))))),
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: close }, 'ביטול'), h('button', { class: 'btn primary', onclick: async (e) => {
        e.target.disabled = true;
        try { const r = await api('/api/duplicates-clean', {}); close(); toast(`פינית ${bytes(r.freed)} 🧹`, 'good'); route(); } catch (err) { e.target.disabled = false; toast(err.message, 'bad'); }
      } }, `מחק ${d.files.length} עותקים כפולים`)));
  });
}

function handoff(msg, title) {  // Claude does not watch the page by itself: the person tells the project's chat, and that chat picks the notes up
  modal((box, close) => {
    box.append(h('h3', {}, title), h('p', {}, 'נשמר במחסן. Claude לא רואה את זה לבד: הוא קורא את ההערות רק כשיש שיחה פתוחה איתו.'),
      h('div', { class: 'keep' }, h('b', {}, 'עכשיו: '), 'פתח את השיחה של הפרויקט עם Claude (או שיחה חדשה), הדבק את ההודעה ושלח. אם כבר יש שיחה שמחכה להערות, היא קיבלה אותן לבד.'),
      h('div', { class: 'keep mono', style: 'text-align:start;direction:rtl' }, msg),
      h('div', { class: 'acts' }, h('button', { class: 'btn ghost', onclick: close }, 'סגור'),
        h('button', { class: 'btn primary', onclick: async () => { try { await navigator.clipboard.writeText(msg); toast('הועתק. הדבק בשיחה עם Claude', 'good'); close(); } catch (e) { toast(msg); } } }, '📋 העתק הודעה ל-Claude')));
  });
}
/* ---------------------------------------------------------------- help */
function help() {
  modal((box, close) => {
    const row = (k, t) => [h('span', { class: 'kbd' }, k), h('span', {}, t)];
    box.append(h('h3', {}, 'קיצורי מקלדת'), h('p', {}, 'בחדר הסקירה. עובד גם כשהמקלדת בעברית.'),
      h('div', { class: 'keys' }, row('Space', 'נגן / עצור'), row('← →', 'פריים אחורה / קדימה'), row('Shift + ← →', 'שנייה אחורה / קדימה'),
        row('C', 'הערה על הרגע הנוכחי'), row('I / O', 'התחלה / סוף של קטע'), row('Shift + גרירה', 'סימון קטע על ציר הזמן'), row('D', 'ציור והקפה על הפריים'),
        row('1 / 2 / 3', '👎 לתקן / 👍 אהבתי / 💬 הערה'), row('Enter', 'הוספת ההערה'), row('Ctrl + Z', 'ביטול קו אחרון בציור'), row('M / F', 'השתק / מסך מלא'), row('Esc', 'ביטול')),
      h('div', { class: 'acts' }, h('button', { class: 'btn primary', onclick: close }, 'הבנתי')));
  });
}
$('#helpBtn').addEventListener('click', help);
document.addEventListener('keydown', (e) => { if (e.key === '?' && !isTyping(document.activeElement) && $('#modal').hidden) help(); });

route();
})();
