/* Mapping Épi : les 12 tableaux de bord (données : window.TDB, calculées par core/tableaux.py ; cartes : window.TDB_CARTES). */
(function () {
'use strict';
const D = window.TDB, CARTES = window.TDB_CARTES || {nat: '', prov: []};

const C = {s1: '#2a78d6', s2: '#eb6834', s3: '#1baf7a', s1l: '#cde2fb', good: '#0ca30c', warn: '#fab219', serious: '#ec835a', crit: '#d03b3b',
           nd: '#B8C0CC', ink: '#121A26', ink2: '#4B5768', ink3: '#7A8597', grid: '#EEF1F5', line: '#E3E8EF', navy: '#1F3A5F'};
const $ = s => document.querySelector(s);
const fr = n => n === null || n === undefined ? 'ND' : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
const pct = n => n === null ? 'ND' : (Math.round(n * 10) / 10).toString().replace('.', ',') + ' %';
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
const ton = p => p === null ? 'nd' : p < 60 ? 'crit' : p < 85 ? 'warn' : 'good';
const tonC = t => ({good: C.good, warn: C.warn, serious: C.serious, crit: C.crit, nd: C.nd})[t];
const rbar = (x, y, w, h, r, fill, top = true) => {           // barre arrondie du côté des données seulement
  if (h <= 0 || w <= 0) return '';
  r = Math.min(r, h, w / 2);
  return top ? `<path d="M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z" fill="${fill}"/>`
             : `<path d="M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z" fill="${fill}"/>`;
};
const svg = (w, h, body) => `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" style="display:block">${body}</svg>`;

// ------------------------------------------------------------------ composants
function niceMax(m) { const pas = [1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000]; for (const p of pas) if (4 * p >= m) return 4 * p; return Math.ceil(m / 1000) * 1000; }
function spark(vals, color, w = 96, h = 30) {
  const mx = Math.max(...vals), mn = Math.min(...vals), sx = w / (vals.length - 1);
  const pts = vals.map((v, i) => [i * sx, h - 3 - (h - 6) * (v - mn) / ((mx - mn) || 1)]);
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join('');
  const l = pts[pts.length - 1];
  return `<svg width="${w}" height="${h}"><path d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/><circle cx="${l[0]}" cy="${l[1]}" r="3.2" fill="${color}" stroke="#fff" stroke-width="1.5"/></svg>`;
}
function kpis(sel, items) {
  $(sel).innerHTML = items.map(k => `<div class="kpi${k.sp ? ' avec-sp' : ''}">${k.st ? `<div class="bar4" style="background:${tonC(k.st)}"></div>` : ''}
    <div class="t">${k.t}</div><div class="v">${k.v}${k.u ? `<small>${k.u}</small>` : ''}</div>
    <div class="d">${k.chip ? `<span class="chip ${k.chip[0]}">${k.chip[1]}</span>` : ''}<span>${k.d || ''}</span></div>
    ${k.sp ? `<div class="sp">${spark(k.sp, k.spc || C.s1)}</div>` : ''}</div>`).join('');
}
function barsV(sel, labels, vals, opt = {}) {
  const w = opt.w || 900, h = opt.h || 300, l = 34, b = 26, t = 16, r = 8;
  const mx = opt.max || niceMax(Math.max(...vals)), pw = (w - l - r) / vals.length, bw = Math.min(pw * 0.62, 46);
  let s = '';
  for (let k = 0; k <= 4; k++) { const v = mx * k / 4, y = t + (h - t - b) * (1 - k / 4);
    s += `<line x1="${l}" x2="${w - r}" y1="${y}" y2="${y}" stroke="${C.grid}"/><text x="${l - 6}" y="${y + 4}" text-anchor="end" class="axis">${Math.round(v)}</text>`; }
  vals.forEach((v, i) => { const x = l + i * pw + (pw - bw) / 2, bh = (h - t - b) * v / mx, y = h - b - bh;
    const col = opt.colors ? opt.colors[i] : C.s1;
    s += `<g><title>${labels[i]} : ${v}</title>${rbar(x, y, bw, bh, 4, col)}</g>`;
    if (opt.lab === 'all' || (opt.lab === 'last' && i === vals.length - 2) || (opt.labIdx || []).includes(i))
      s += `<text x="${x + bw / 2}" y="${y - 5}" text-anchor="middle" class="lbl">${v}</text>`;
    s += `<text x="${x + bw / 2}" y="${h - 8}" text-anchor="middle" class="axis">${labels[i]}</text>`; });
  s += `<line x1="${l}" x2="${w - r}" y1="${h - b}" y2="${h - b}" stroke="#C9D1DC"/>`;
  if (opt.ann) opt.ann.forEach(a => { const x = l + a.i * pw + pw / 2;
    s += `<line x1="${x}" x2="${x}" y1="${t}" y2="${h - b}" stroke="${C.ink3}" stroke-dasharray="3 4"/><text x="${x + 6}" y="${t + 10}" class="lbl2">${a.t}</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
function hbars(sel, rows, opt = {}) {
  // rows: [label, value, color?, text?, extra?]
  const w = opt.w || 520, rh = opt.rh || 30, lw = opt.lw || 150, vw = opt.vw || 70, h = rows.length * rh + 6;
  const mx = opt.max || Math.max(...rows.map(r => r[1] || 0)) || 1, bw = w - lw - vw - 10;
  let s = '';
  rows.forEach((r, i) => { const y = i * rh + 4, val = r[1], ww = val ? bw * val / mx : 0;
    s += `<text x="0" y="${y + rh / 2 + 1}" class="lbl2" dominant-baseline="middle">${esc(r[0])}</text>`;
    s += `<rect x="${lw}" y="${y + rh / 2 - 6}" width="${bw}" height="12" rx="6" fill="${C.grid}"/>`;
    s += `<g><title>${esc(r[0])} : ${r[3] || val}</title>${rbar(lw, y + rh / 2 - 6, ww, 12, 4, r[2] || C.s1, false)}</g>`;
    if (opt.target) { const tx = lw + bw * opt.target / mx; s += `<line x1="${tx}" x2="${tx}" y1="${y + rh / 2 - 10}" y2="${y + rh / 2 + 10}" stroke="${C.ink}" stroke-width="2"/>`; }
    s += `<text x="${w}" y="${y + rh / 2 + 1}" text-anchor="end" class="lbl" dominant-baseline="middle">${r[3] !== undefined ? r[3] : fr(val)}</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
function bullets(sel, rows) {          // [label, valeur %, cible %, sens ('haut'|'bas'), texte]
  const w = 520, rh = 46, lw = 210, h = rows.length * rh;
  let s = '';
  rows.forEach((r, i) => { const y = i * rh + 6, bw = w - lw - 64, v = r[1], cible = r[2];
    const ok = r[3] === 'bas' ? v <= cible : v >= cible, warn = r[3] === 'bas' ? v <= cible * 1.4 : v >= cible * 0.8;
    const col = ok ? C.good : warn ? C.warn : C.crit, mx = r[5] || 100;
    s += `<text x="0" y="${y + 12}" class="lbl" style="font-size:12.5px">${esc(r[0])}</text><text x="0" y="${y + 28}" class="lbl2">${esc(r[4])}</text>`;
    s += `<rect x="${lw}" y="${y + 6}" width="${bw}" height="14" rx="7" fill="${C.grid}"/>`;
    s += rbar(lw, y + 6, bw * Math.min(v, mx) / mx, 14, 7, col, false);
    const tx = lw + bw * cible / mx; s += `<line x1="${tx}" x2="${tx}" y1="${y + 1}" y2="${y + 25}" stroke="${C.ink}" stroke-width="2.2"/>`;
    s += `<text x="${w}" y="${y + 18}" text-anchor="end" class="lbl" style="font-size:14px">${r[6] || pct(v)}</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
function segbar(sel, parts, opt = {}) {   // part-to-whole horizontal, <= 6 segments, labels below
  const w = opt.w || 520, tot = parts.reduce((a, p) => a + p[1], 0); let x = 0, s = '';
  parts.forEach((p, i) => { const ww = (w - (parts.length - 1) * 2) * p[1] / tot;
    s += `<g><title>${p[0]} : ${p[1]}</title><rect x="${x}" y="0" width="${ww}" height="26" rx="${i === 0 || i === parts.length - 1 ? 6 : 0}" fill="${p[2]}"/></g>`; x += ww + 2; });
  const lg = parts.map(p => `<span><i style="background:${p[2]}"></i>${p[0]} <b>${fr(p[1])}</b> <span style="color:var(--ink3)">(${Math.round(100 * p[1] / tot)} %)</span></span>`).join('');
  $(sel).innerHTML = svg(w, 28, s) + `<div class="lgd" style="margin-top:10px">${lg}</div>`;
}
function funnel(sel, steps, opt = {}) {  // [label, n] décroissant ; % de l'étape précédente sous le libellé
  const w = opt.w || 820, rh = 50, lw = opt.lw || 230, h = steps.length * rh, mx = steps[0][1], flag = opt.flag === undefined ? steps.length : opt.flag;
  let s = '';
  steps.forEach((st, i) => { const y = i * rh + 4, ww = Math.max(3, (w - lw - 70) * st[1] / mx), conv = i ? Math.round(100 * st[1] / steps[i - 1][1]) : null;
    const alerte = conv !== null && i < flag && conv < 85, col = alerte ? C.s2 : C.s1;
    s += `<text x="0" y="${y + 17}" class="lbl" style="font-size:13px">${st[0]}</text>`;
    if (conv !== null) s += `<text x="0" y="${y + 34}" class="lbl2" style="fill:${alerte ? '#9A3D16' : C.ink3};font-weight:${alerte ? 700 : 400}">${conv} % de l'étape précédente</text>`;
    s += `<g><title>${st[0]} : ${st[1]}</title>${rbar(lw, y + 8, ww, 24, 5, col, false)}</g>`;
    s += `<text x="${lw + ww + 10}" y="${y + 25}" class="lbl" style="font-size:14px">${fr(st[1])}</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
function dots(sel, rows, opt = {}) {    // [label, q1, med, q3, seuil]
  const w = opt.w || 900, rh = 40, lw = 250, h = rows.length * rh + 28, mx = opt.max || 10, pw = w - lw - 70;
  const X = v => lw + pw * v / mx; let s = '';
  for (let k = 0; k <= mx; k += (opt.step || 2)) s += `<line x1="${X(k)}" x2="${X(k)}" y1="0" y2="${h - 22}" stroke="${C.grid}"/><text x="${X(k)}" y="${h - 6}" text-anchor="middle" class="axis">${k} j</text>`;
  rows.forEach((r, i) => { const y = i * rh + 18, late = r[4] !== null && r[2] > r[4];
    s += `<text x="0" y="${y + 4}" class="lbl" style="font-size:13px">${r[0]}</text>`;
    if (r[4] !== null) s += `<line x1="${X(r[4])}" x2="${X(r[4])}" y1="${y - 13}" y2="${y + 13}" stroke="${C.crit}" stroke-width="2"/>`;
    s += `<rect x="${X(r[1])}" y="${y - 5}" width="${X(r[3]) - X(r[1])}" height="10" rx="5" fill="${late ? '#F8D3C3' : C.s1l}"/>`;
    s += `<g><title>${r[0]} : médiane ${r[2]} j (IQR ${r[1]}–${r[3]})</title><circle cx="${X(r[2])}" cy="${y}" r="7" fill="${late ? C.s2 : C.s1}" stroke="#fff" stroke-width="2"/></g>`;
    s += `<text x="${w}" y="${y + 4}" text-anchor="end" class="lbl" style="font-size:13.5px;fill:${late ? '#9A3D16' : C.ink}">${String(r[2]).replace('.', ',')} j</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
function line(sel, vals, opt = {}) {
  const w = opt.w || 560, h = opt.h || 240, l = 38, b = 24, t = 14, r = 10, mx = opt.max || Math.ceil(Math.max(...vals) / 50) * 50;
  const n = vals.length + (opt.proj ? opt.proj.length - 1 : 0), X = i => l + (w - l - r - 70) * i / (n - 1), Y = v => t + (h - t - b) * (1 - v / mx);
  let s = '';
  for (let k = 0; k <= 4; k++) { const y = Y(mx * k / 4); s += `<line x1="${l}" x2="${w - r}" y1="${y}" y2="${y}" stroke="${C.grid}"/><text x="${l - 6}" y="${y + 4}" text-anchor="end" class="axis">${fr(Math.round(mx * k / 4))}</text>`; }
  const d = vals.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(v).toFixed(1)).join('');
  s += `<path d="${d}L${X(vals.length - 1)},${Y(0)}L${X(0)},${Y(0)}Z" fill="${C.s1}" opacity=".10"/><path d="${d}" fill="none" stroke="${C.s1}" stroke-width="2"/>`;
  if (opt.proj) { const p = opt.proj, base = vals.length - 1, dd = p.map((v, i) => (i ? 'L' : 'M') + X(base + i).toFixed(1) + ',' + Y(v).toFixed(1)).join('');
    s += `<path d="${dd}" fill="none" stroke="${C.s1}" stroke-width="2" stroke-dasharray="5 5"/>`; }
  (opt.xl || []).forEach(([i, txt]) => s += `<text x="${X(i)}" y="${h - 6}" text-anchor="middle" class="axis">${txt}</text>`);
  const li = vals.length - 1; s += `<circle cx="${X(li)}" cy="${Y(vals[li])}" r="4.5" fill="${C.s1}" stroke="#fff" stroke-width="2"/><text x="${X(li) - 8}" y="${Y(vals[li]) - 10}" text-anchor="end" class="lbl">${fr(vals[li])} aujourd'hui</text>`;
  $(sel).innerHTML = svg(w, h, s);
}
function diverge(sel, rows) {            // [ZS, écart] + = sous-listing (orange), − = contacts en plus dans DHIS2 (bleu)
  const w = 520, rh = 30, lw = 110, h = rows.length * rh + 24, mx = Math.max(...rows.map(r => Math.abs(r[1]))), mid = lw + (w - lw - 50) / 2, half = (w - lw - 50) / 2;
  let s = `<line x1="${mid}" x2="${mid}" y1="0" y2="${h - 18}" stroke="#C9D1DC"/>`;
  s += `<text x="${mid - 6}" y="${h - 4}" text-anchor="end" class="axis">◀ plus dans DHIS2</text><text x="${mid + 6}" y="${h - 4}" class="axis">sous-listing ▶</text>`;
  rows.forEach((r, i) => { const y = i * rh + 4, ww = half * Math.abs(r[1]) / mx, pos = r[1] > 0;
    s += `<text x="0" y="${y + 17}" class="lbl2">${r[0]}</text>`;
    s += `<g><title>${r[0]} : ${r[1] > 0 ? '+' : ''}${r[1]}</title>` + (pos ? rbar(mid, y + 8, ww, 13, 4, C.s2, false)
      : `<path d="M${mid},${y + 8}H${mid - ww + 4}Q${mid - ww},${y + 8} ${mid - ww},${y + 12}V${y + 17}Q${mid - ww},${y + 21} ${mid - ww + 4},${y + 21}H${mid}Z" fill="${C.s1}"/>`) + '</g>';
    s += `<text x="${w}" y="${y + 18}" text-anchor="end" class="lbl">${r[1] > 0 ? '+' : ''}${fr(r[1])}</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
function heat(sel, cols, rows, fmt, tone, opt = {}) {
  const th = `<tr><th></th>${cols.map(c => `<th style="text-align:center">${c}</th>`).join('')}${opt.extra ? `<th class="n">${opt.extra}</th>` : ''}</tr>`;
  const tr = rows.map(r => `<tr><td><b>${r[0]}</b></td>${r[1].map(v => { const t = tone(v); const bg = tonC(t);
    return `<td class="h" style="background:${bg};color:${t === 'warn' || t === 'nd' ? '#3A2B00' : '#fff'}" title="${r[0]} : ${fmt(v)}">${fmt(v)}</td>`; }).join('')}${opt.extra ? `<td class="n"><b>${r[2]}</b></td>` : ''}</tr>`).join('');
  $(sel).innerHTML = `<table class="t heat">${th}${tr}</table>`;
}
function seqHeat(sel, cols, rows) {     // intensité (bleu séquentiel), pour % de symptômes
  const ramp = ['#F4F8FD', '#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95'];
  const th = `<tr><th></th>${cols.map(c => `<th style="text-align:center">${c}</th>`).join('')}</tr>`;
  const tr = rows.map(r => `<tr><td>${r[0]}</td>${r[1].map(v => { const k = Math.min(6, Math.floor(v / 15)); return `<td class="h" style="background:${ramp[k]};color:${k >= 4 ? '#fff' : C.ink}">${v} %</td>`; }).join('')}</tr>`).join('');
  $(sel).innerHTML = `<table class="t heat">${th}${tr}</table><div class="lgd" style="margin-top:6px">${ramp.map((c, i) => `<span><i style="background:${c};border:1px solid #E3E8EF"></i>${i * 15}${i < 6 ? '–' + (i * 15 + 14) : '+'} %</span>`).join('')}</div>`;
}
function pyramide(sel, ages, h_, f_, dh, df) {
  const w = 520, rh = 24, mid = 260, half = 190, h = ages.length * rh + 30, mx = Math.max(...h_, ...f_);
  let s = `<text x="${mid - 40}" y="12" text-anchor="end" class="lbl">Hommes</text><text x="${mid + 40}" y="12" class="lbl">Femmes</text>`;
  ages.forEach((a, i) => { const y = 22 + i * rh, wh = half * h_[i] / mx, wf = half * f_[i] / mx, wdh = half * dh[i] / mx, wdf = half * df[i] / mx;
    s += `<rect x="${mid - 28 - wh}" y="${y}" width="${wh}" height="${rh - 6}" rx="3" fill="${C.s1l}"/><rect x="${mid - 28 - wdh}" y="${y}" width="${wdh}" height="${rh - 6}" rx="3" fill="${C.s1}"/>`;
    s += `<rect x="${mid + 28}" y="${y}" width="${wf}" height="${rh - 6}" rx="3" fill="#FAD3C2"/><rect x="${mid + 28}" y="${y}" width="${wdf}" height="${rh - 6}" rx="3" fill="${C.s2}"/>`;
    s += `<text x="${mid}" y="${y + 13}" text-anchor="middle" class="axis">${a}</text>`;
    s += `<text x="${mid - 34 - wh}" y="${y + 13}" text-anchor="end" class="lbl2">${h_[i]}</text><text x="${mid + 34 + wf}" y="${y + 13}" class="lbl2">${f_[i]}</text>`; });
  $(sel).innerHTML = svg(w, h, s) + `<div class="lgd"><span><i style="background:${C.s1l}"></i>Cas hommes</span><span><i style="background:${C.s1}"></i>dont décès</span><span><i style="background:#FAD3C2"></i>Cas femmes</span><span><i style="background:${C.s2}"></i>dont décès</span></div>`;
}
function table(sel, heads, rows, aligns = []) {
  $(sel).innerHTML = `<table class="t"><tr>${heads.map((h, i) => `<th class="${aligns[i] === 'n' ? 'n' : ''}">${h}</th>`).join('')}</tr>` +
    rows.map(r => `<tr>${r.map((c, i) => `<td class="${aligns[i] === 'n' ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('') + '</table>';
}
const chip = (t, txt) => `<span class="chip ${t}">${txt}</span>`;


// ------------------------------------------------------------------ icônes (traits)
const I = {
  grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z', layers: 'M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5M3 17l9 5 9-5',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2', bed: 'M3 18V7M3 12h18v6M21 18v-4a3 3 0 00-3-3H11v4M7 11a2 2 0 100-4 2 2 0 000 4z',
  net: 'M12 5a2 2 0 100-4 2 2 0 000 4zM5 21a2 2 0 100-4 2 2 0 000 4zM19 21a2 2 0 100-4 2 2 0 000 4zM12 5v6M12 11l-6 7M12 11l6 7',
  users: 'M9 11a4 4 0 100-8 4 4 0 000 8zM2 21v-1a6 6 0 0112 0v1M17 11a3 3 0 100-6M22 21v-1a5 5 0 00-4-4.9',
  clip: 'M9 4h6v3H9zM7 5H5v16h14V5h-2M8 12l2.5 2.5L16 9', globe: 'M12 22a10 10 0 100-20 10 10 0 000 20zM2 12h20M12 2c3 3 3 17 0 20M12 2c-3 3-3 17 0 20',
  send: 'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z', shield: 'M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5l8-3z', heart: 'M12 21s-8-5-8-11a5 5 0 019-3 5 5 0 019 3c0 6-8 11-8 11z',
  db: 'M12 8c4.4 0 8-1.3 8-3s-3.6-3-8-3-8 1.3-8 3 3.6 3 8 3zM4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
  alert: 'M12 3l10 18H2L12 3zM12 10v5M12 18h.01', clock: 'M12 22a10 10 0 100-20 10 10 0 000 20zM12 6v6l4 2', check: 'M20 6L9 17l-5-5',
  map: 'M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14', link: 'M10 14a5 5 0 007 0l3-3a5 5 0 00-7-7l-1 1M14 10a5 5 0 00-7 0l-3 3a5 5 0 007 7l1-1',
  truck: 'M1 4h14v12H1zM15 9h4l4 4v3h-8M5 19a2 2 0 100-4 2 2 0 000 4zM19 19a2 2 0 100-4 2 2 0 000 4z', drop: 'M12 2s7 7.5 7 13a7 7 0 01-14 0c0-5.5 7-13 7-13z',
  pin: 'M12 22s7-6.5 7-12a7 7 0 10-14 0c0 5.5 7 12 7 12zM12 12a2 2 0 100-4 2 2 0 000 4z', virus: 'M12 17a5 5 0 100-10 5 5 0 000 10zM12 2v5M12 17v5M2 12h5M17 12h5M5 5l3.5 3.5M15.5 15.5L19 19M19 5l-3.5 3.5M8.5 15.5L5 19',
  target: 'M12 22a10 10 0 100-20 10 10 0 000 20zM12 18a6 6 0 100-12 6 6 0 000 12zM12 14a2 2 0 100-4 2 2 0 000 4z', file: 'M14 2H6v20h12V6l-4-4zM14 2v4h4M9 13h6M9 17h6'};
const ico = (k, c = '#2a78d6', s = 22, sw = 2) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round"><path d="${I[k]}"/></svg>`;
const K = D.kpi, n = D.n;
const p1 = (a, b) => b ? (Math.round(1000 * a / b) / 10).toString().replace('.', ',') : 'ND';
const MENU = [['strat', 'Vue stratégique', 'grid'], ['couv', 'Couverture des mappings', 'layers'], ['dyn', 'Dynamique épidémiologique', 'chart'], ['parc', 'Parcours thérapeutique', 'bed'],
  ['chain', 'Chaînes de transmission', 'net'], ['cont', 'Surveillance et contacts', 'users'], ['act', 'Suivi des actions', 'clip'], ['geo', 'Analyse géospatiale', 'globe'],
  ['mob', 'Mobilité et déplacements', 'send'], ['pci', 'PCI et structures sanitaires', 'shield'], ['clin', 'Profil clinique et symptômes', 'heart'], ['qual', 'Qualité des données', 'db']];

// ------------------------------------------------------------------ composants supplémentaires
function kc(cls, icon, col, t, v, u, chipc, chipt, s, extra = '') {
  return `<div class="kcard ${cls}${extra ? ' avec-ring' : ''}"><div class="kh"><div class="ic">${ico(icon, col, 26)}</div><div><div class="t">${t}</div>
    <div class="v">${v}${u ? `<small>${u}</small>` : ''}${chipt ? `<span class="ch ${chipc}">${chipt}</span>` : ''}</div></div></div>
    <div class="s">${s}</div>${extra ? '' : `<div class="wm">${ico(icon, col, 110, 1.4)}</div>`}${extra}</div>`;
}
function ring(pctv, col, size = 78) {
  const r = size / 2 - 7, c = 2 * Math.PI * r, d = c * Math.min(pctv, 100) / 100;
  return `<svg class="ring" width="${size}" height="${size}"><circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="rgba(255,255,255,.7)" stroke-width="9"/>
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${col}" stroke-width="9" stroke-linecap="round" stroke-dasharray="${d} ${c}" transform="rotate(-90 ${size / 2} ${size / 2})"/>
    <text x="${size / 2}" y="${size / 2 + 5}" text-anchor="middle" style="font-size:15px;font-weight:800;fill:${C.ink}">${Math.round(pctv)} %</text></svg>`;
}
function donut(sel, parts, centre, sous, size = 210) {
  const tot = parts.reduce((a, p) => a + p[1], 0), r = size / 2 - 16, cx = size / 2, c = 2 * Math.PI * r; let off = 0, s = '';
  parts.forEach(p => { const d = c * p[1] / tot; s += `<circle cx="${cx}" cy="${cx}" r="${r}" fill="none" stroke="${p[2]}" stroke-width="26" stroke-dasharray="${Math.max(0, d - 2)} ${c}" stroke-dashoffset="${-off}" transform="rotate(-90 ${cx} ${cx})"><title>${p[0]} : ${p[1]}</title></circle>`; off += d; });
  s += `<text x="${cx}" y="${cx - 2}" text-anchor="middle" style="font-size:30px;font-weight:800;fill:${C.ink}">${fr(centre)}</text><text x="${cx}" y="${cx + 20}" text-anchor="middle" class="lbl2">${sous}</text>`;
  const lg = parts.map(p => `<div style="display:flex;gap:7px;align-items:center;margin:7px 0;font-size:13px;white-space:nowrap"><i style="width:12px;height:12px;border-radius:3px;background:${p[2]};display:inline-block"></i>${p[0]} : <b>${fr(p[1])}</b> <span style="color:var(--ink3)">(${p1(p[1], tot)} %)</span></div>`).join('');
  $(sel).innerHTML = `<div style="display:flex;gap:22px;align-items:center"><svg width="${size}" height="${size}">${s}</svg><div>${lg}</div></div>`;
}
function funnelShape(sel, steps, cols) {
  const w = 560, rh = 54, h = steps.length * rh; let s = '';
  steps.forEach((st, i) => { const top = 360 - i * 50, bot = 360 - (i + 1) * 50, y = i * rh;
    s += `<path d="M${(380 - top) / 2},${y + 2}H${(380 + top) / 2}L${(380 + bot) / 2},${y + rh - 4}H${(380 - bot) / 2}Z" fill="${cols[i]}"/>`;
    s += `<text x="190" y="${y + rh / 2 + 7}" text-anchor="middle" style="font-size:19px;font-weight:800;fill:#fff">${fr(st[1])}</text>`;
    s += `<text x="400" y="${y + rh / 2}" class="lbl" style="font-size:13px">${st[0]}</text><text x="400" y="${y + rh / 2 + 17}" class="lbl2">${st[2]}</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
function reseau(sel, chaines, w = 980, h = 420) {
  const col = {Décès: C.crit, Vivant: C.s1, 'En traitement': C.s3, Inconnu: C.nd};
  const cells = chaines.slice(0, 14); let s = '';
  const big = cells[0], places = [[200, 210, 150]];
  const reste = cells.slice(1), cw = (w - 430) / 4;
  reste.forEach((c, i) => places.push([440 + (i % 4) * cw + cw / 2, 52 + Math.floor(i / 4) * 96, 26]));
  cells.forEach((ch, k) => { const [cx, cy, R] = places[k], deg = Array(ch.n).fill(0); ch.edges.forEach(([a, b]) => { deg[a]++; deg[b]++; });
    const root = deg.indexOf(Math.max(...deg)), pos = [];
    let j = 0; for (let i = 0; i < ch.n; i++) { if (i === root) { pos[i] = [cx, cy]; continue; } const ang = ch.n === 2 ? 0 : 2 * Math.PI * j / (ch.n - 1) - Math.PI / 2; pos[i] = [cx + R * Math.cos(ang), cy + R * Math.sin(ang)]; j++; }
    ch.edges.forEach(([a, b]) => s += `<line x1="${pos[a][0]}" y1="${pos[a][1]}" x2="${pos[b][0]}" y2="${pos[b][1]}" stroke="#AFC0D4" stroke-width="2"/>`);
    pos.forEach((p, i) => { const r = i === root ? (k === 0 ? 24 : 12) : (k === 0 ? 14 : 8); s += `<circle cx="${p[0]}" cy="${p[1]}" r="${r}" fill="${col[ch.etat[i]] || C.nd}" stroke="#fff" stroke-width="2.5"><title>${ch.etat[i]}</title></circle>`; });
    s += `<text x="${cx}" y="${cy + R + (k === 0 ? 34 : 22)}" text-anchor="middle" class="lbl2" style="font-weight:600;font-size:${k === 0 ? 12.5 : 11}px">C-${String(k + 1).padStart(2, '0')} · ${ch.zs} (${ch.n})</text>`; });
  $(sel).innerHTML = svg(w, h, s) + `<div class="lgd" style="margin-top:4px"><span><i style="background:${C.s1}"></i>Vivant</span><span><i style="background:${C.s3}"></i>En traitement</span><span><i style="background:${C.crit}"></i>Décès</span><span><i style="background:${C.nd}"></i>Inconnu</span><span style="margin-left:auto">Un lien = « ID du cas source » renseigné et présent dans Mapping Épi · gros nœud = cas source</span></div>`;
}
function bars2(sel, labels, a, b, opt = {}) {    // barres groupées, une seule échelle
  const w = opt.w || 900, h = opt.h || 280, l = 34, bb = 26, t = 18, r = 8, mx = opt.max || niceMax(Math.max(...a, ...b)), pw = (w - l - r) / labels.length, bw = Math.min(pw * 0.34, 26);
  let s = ''; for (let k = 0; k <= 4; k++) { const v = mx * k / 4, y = t + (h - t - bb) * (1 - k / 4); s += `<line x1="${l}" x2="${w - r}" y1="${y}" y2="${y}" stroke="${C.grid}"/><text x="${l - 6}" y="${y + 4}" text-anchor="end" class="axis">${Math.round(v)}</text>`; }
  labels.forEach((lb, i) => { const x0 = l + i * pw + pw / 2 - bw - 1;
    [[a[i], opt.ca || C.s1], [b[i], opt.cb || C.s2]].forEach(([v, c], k) => { const bh = (h - t - bb) * v / mx, x = x0 + k * (bw + 2);
      s += `<g><title>${lb} : ${v}</title>${rbar(x, h - bb - bh, bw, bh, 4, c)}</g>`; if (v && (opt.lab !== false)) s += `<text x="${x + bw / 2}" y="${h - bb - bh - 5}" text-anchor="middle" class="lbl" style="font-size:11px">${v}</text>`; });
    s += `<text x="${l + i * pw + pw / 2}" y="${h - 8}" text-anchor="middle" class="axis">${lb}</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
function lines2(sel, labels, a, b, opt = {}) {
  const w = opt.w || 900, h = opt.h || 280, l = 34, bb = 26, t = 18, r = 10, mx = opt.max || Math.ceil(Math.max(...a, ...b) / 5) * 5;
  const X = i => l + (w - l - r) * i / (labels.length - 1), Y = v => t + (h - t - bb) * (1 - v / mx); let s = '';
  for (let k = 0; k <= 4; k++) { const y = Y(mx * k / 4); s += `<line x1="${l}" x2="${w - r}" y1="${y}" y2="${y}" stroke="${C.grid}"/><text x="${l - 6}" y="${y + 4}" text-anchor="end" class="axis">${Math.round(mx * k / 4)}</text>`; }
  [[a, opt.ca || C.navy, true], [b, opt.cb || C.s3, false]].forEach(([v, c, area]) => { const d = v.map((x, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + Y(x).toFixed(1)).join('');
    if (area) s += `<path d="${d}L${X(v.length - 1)},${Y(0)}L${X(0)},${Y(0)}Z" fill="${c}" opacity=".07"/>`;
    s += `<path d="${d}" fill="none" stroke="${c}" stroke-width="2.2"/>` + v.map((x, i) => `<circle cx="${X(i)}" cy="${Y(x)}" r="3.2" fill="#fff" stroke="${c}" stroke-width="2"><title>${labels[i]} : ${x}</title></circle>`).join(''); });
  labels.forEach((lb, i) => { if (i % 3 === 0 || i === labels.length - 1) s += `<text x="${X(i)}" y="${h - 8}" text-anchor="middle" class="axis">${lb}</text>`; });
  $(sel).innerHTML = svg(w, h, s);
}
const sig = (c, ic, t, s) => `<div class="sig ${c}"><div class="ic">${ic}</div><div><b>${t}</b><span>${s}</span></div><div class="ar">›</div></div>`;

// ------------------------------------------------------------------ écrans
const SRC = `Calculé en direct sur les ${n} fiches du périmètre et des filtres · agrégats uniquement (aucun ID ni nom) · délais aberrants écartés`;
const S1 = D.sem_lib ? D.sem_lib[0] : 'S-1', S2 = D.sem_lib ? D.sem_lib[1] : 'S0';
const ECRANS = {
strat: () => `
  <div class="kc">${kc('b', 'users', C.s1, 'Cas confirmés', fr(K.cas), '', K.cas7 < K.cas7p ? 'dn-good' : 'up-bad', (K.cas7 < K.cas7p ? '▼ ' : '▲ ') + Math.abs(Math.round(100 * (K.cas7 - K.cas7p) / K.cas7p)) + ' %', `${K.cas7} sur 7 jours (contre ${K.cas7p} la semaine d'avant)`)}
  ${kc('r', 'alert', C.crit, 'Décès · létalité', K.deces, p1(K.deces, n) + ' %', 'up-bad', K.comm + ' communautaires', `${p1(K.comm, K.deces)} % des décès survenus hors structure`)}
  ${kc('a', 'map', '#C88400', 'Zones de santé touchées', K.zs, `· ${K.prov} provinces`, 'neu', K.as + ' aires', D.prov.filter(p => p[0] !== '?').map(p => p[0]).join(', '))}
  ${kc('g', 'clock', C.s3, 'J0 → isolement (médiane)', String(K.d_iso).replace('.', ','), 'jours', 'up-bad', 'cible ≤ 3 j', `confirmation à J+${K.d_conf} · notification à J+${K.d_notif}`)}</div>
  <div class="g" style="grid-template-columns:1.45fr 1fr 1fr">
    <div class="card"><h3>${ico('chart')}Cas et décès par semaine</h3><div class="q">Semaine épidémiologique de confirmation (cas) et de décès</div>
      <div class="lgd"><span><i style="background:${C.s1}"></i>Cas confirmés</span><span><i style="background:${C.crit}"></i>Décès</span></div><div id="v-sem"></div></div>
    <div class="card carte"><h3>${ico('globe')}Provinces touchées</h3><div class="q">Couleur : délai depuis le dernier cas</div>${CARTES.nat}</div>
    <div class="card"><h3>${ico('target')}Niveau de risque des cas</h3><div class="q">Risque global calculé sur chaque mapping</div><div id="v-risk"></div>
      <h3 style="margin-top:18px">${ico('layers')}Cas par province</h3><div id="v-prov" style="margin-top:8px"></div></div>
  </div>
  <div class="g" style="grid-template-columns:1.25fr 1fr;margin-top:16px">
    <div class="card"><h3>${ico('pin')}Zones de santé les plus touchées</h3><div class="q">Cas, décès, nouveaux cas 7 jours et jours depuis le dernier cas</div><div id="t-zs"></div></div>
    <div class="card"><h3>${ico('alert', C.crit)}Signaux à surveiller</h3><div class="q">Calculés automatiquement sur les fiches</div><div id="l-sig"></div></div>
  </div>`,
couv: () => `
  <div class="kc">${kc('b', 'layers', C.s1, 'Fiches de mapping', fr(n), '', 'neu', (n - D.qualite.sans_id) + ' avec ID', `${K.zs} zones de santé · ${K.as} aires de santé`)}
  ${kc('g', 'check', C.s3, 'Complétude moyenne', String(K.compl).replace('.', ','), '%', 'up-bad', 'cible 95 %', `${D.compl_dist[3]} fiches à 90 % ou plus`, ring(K.compl, C.s3))}
  ${kc('a', 'file', '#C88400', 'Fiches à compléter', D.compl_dist[0] + D.compl_dist[1], '', 'neu', '< 70 %', `${D.compl_dist[0]} fiches sous 50 %`)}
  ${kc('r', 'alert', C.crit, 'Fiches sans ID du cas', D.qualite.sans_id, '', 'up-bad', 'à identifier', 'non comptées dans les analyses par cas')}</div>
  <div class="g" style="grid-template-columns:1.1fr 1fr 1fr">
    <div class="card"><h3>${ico('chart')}Complétude par zone de santé</h3><div class="q">Score moyen des fiches · trait noir = cible 95 % · zones ≥ 5 fiches</div><div id="v-czs"></div></div>
    <div class="card"><h3>${ico('layers')}Répartition des fiches par complétude</h3><div class="q">Nombre de fiches par classe de score</div><div id="v-cdist"></div></div>
    <div class="card"><h3>${ico('file')}Champs renseignés</h3><div class="q">% des fiches où le champ est rempli</div><div id="v-champs"></div></div>
  </div>
  <div class="card" style="margin-top:16px"><h3>${ico('target', C.crit)}Zones prioritaires à compléter</h3><div class="q">Zones dont la complétude moyenne est la plus basse</div><div id="t-prio"></div></div>`,
dyn: () => `
  <div class="kc">${kc('b', 'users', C.s1, 'Cas confirmés · 7 jours', K.cas7, '', K.cas7 < K.cas7p ? 'dn-good' : 'up-bad', (K.cas7 < K.cas7p ? '▼ ' : '▲ ') + Math.abs(Math.round(100 * (K.cas7 - K.cas7p) / K.cas7p)) + ' %', `contre ${K.cas7p} les 7 jours précédents`)}
  ${kc('g', 'chart', C.s3, 'Cas · 28 jours', K.cas28, '', 'neu', p1(K.cas28, n) + ' % du total', 'période active de l\'épidémie')}
  ${kc('a', 'map', '#C88400', 'ZS avec cas en 7 jours', D.zs.filter(z => z.n7).length, `/ ${K.zs}`, 'neu', 'zones actives', `${D.zs.filter(z => z.jours !== null && z.jours > 14).length} ZS sans cas depuis plus de 14 jours`)}
  ${kc('r', 'clock', C.crit, 'J0 → notification (médiane)', String(K.d_notif).replace('.', ','), 'jours', 'up-bad', 'cible ≤ 3 j', 'délai entre les premiers signes et la notification')}</div>
  <div class="g" style="grid-template-columns:1.5fr 1fr">
    <div class="card"><h3>${ico('chart')}Évolution quotidienne · 28 derniers jours</h3><div class="q">Cas par date de confirmation et par date de notification</div>
      <div class="lgd"><span><i style="background:${C.navy}"></i>Notifiés</span><span><i style="background:${C.s3}"></i>Confirmés</span></div><div id="v-jour"></div></div>
    <div class="card"><h3>${ico('chart')}Cas par semaine épidémiologique</h3><div class="q">8 dernières semaines (la dernière est en cours)</div><div id="v-sem2"></div></div>
  </div>
  <div class="g" style="grid-template-columns:1fr 1.25fr;margin-top:16px">
    <div class="card"><h3>${ico('alert', C.crit)}Signaux à surveiller</h3><div class="q">Variation ${S2} / ${S1}</div><div id="l-sig2"></div></div>
    <div class="card"><h3>${ico('target')}Évolution par zone de santé</h3><div class="q">Cas confirmés ${S1} et ${S2} · zones les plus touchées</div><div id="t-var"></div></div>
  </div>`,
parc: () => `
  <div class="kc">${kc('b', 'bed', C.s1, 'Cas isolés (date connue)', D.funnel[4][1], '', 'neu', p1(D.funnel[4][1], n) + ' %', `sur ${n} cas · isolement non daté : ${n - D.funnel[4][1]}`)}
  ${kc('g', 'clock', C.s3, 'J0 → isolement', String(K.d_iso).replace('.', ','), 'jours', 'up-bad', 'cible ≤ 3 j', `intervalle interquartile ${D.delais[1][1][0]}–${D.delais[1][1][2]} j`)}
  ${kc('a', 'clock', '#C88400', 'Prélèvement → résultat', String(K.d_lab).replace('.', ','), 'heures', 'dn-good', 'seuil 48 h', `IQR ${D.lab_iqr[0]}–${D.lab_iqr[2]} h`)}
  ${kc('r', 'alert', C.crit, 'Décès communautaires', K.comm, `/ ${K.deces}`, 'up-bad', p1(K.comm, K.deces) + ' %', `inhumation sécurisée documentée : ${D.eds[0]} sur ${D.eds[0] + D.eds[1]} renseignées`)}</div>
  <div class="card"><h3>${ico('bed')}Flux du parcours des cas <small>· étapes documentées dans les fiches</small></h3>
    <div style="display:grid;grid-template-columns:1fr 400px;gap:20px;align-items:center;margin-top:10px"><div class="flow" id="v-flow"></div><div id="v-issue"></div></div></div>
  <div class="g" style="grid-template-columns:1fr 1fr 1fr;margin-top:16px">
    <div class="card"><h3>${ico('chart')}J0 → isolement par zone de santé</h3><div class="q">Médiane en jours · trait = médiane globale (${K.d_iso} j) · zones ≥ 5 cas</div><div id="v-isozs"></div></div>
    <div class="card"><h3>${ico('clock')}Délais du parcours</h3><div class="q">Médiane (point) et intervalle interquartile (barre) · trait rouge = seuil</div><div id="v-dl"></div></div>
    <div class="card"><h3>${ico('target')}Actions prioritaires</h3><div class="q">Déduites des délais et des issues</div><div id="l-parc"></div></div>
  </div>`,
chain: () => `
  <div class="kc">${kc('b', 'net', C.s1, 'Chaînes reconstituées', D.chaines.length, '', 'neu', D.chaines.reduce((a, c) => a + c.n, 0) + ' cas liés', 'à partir de l\'« ID du cas source » des fiches')}
  ${kc('g', 'link', C.s3, 'Cas avec cas source renseigné', D.src_total, '', 'neu', p1(D.src_total, n) + ' %', `${D.src_base} retrouvés dans Mapping Épi`, ring(100 * D.src_total / n, C.s3))}
  ${kc('r', 'alert', C.crit, 'Chaînes actives (≤ 21 j)', D.chaines.filter(c => c.ouverte).length, '', 'up-bad', 'ouvertes', 'dernier cas de la chaîne il y a 21 jours ou moins')}
  ${kc('a', 'target', '#C88400', 'Cas sans lien connu', D.lien.filter(l => l[0] === 'Non contact' || l[0] === 'Inconnu').reduce((a, l) => a + l[1], 0), '', 'up-bad', 'à investiguer', 'non contacts et lien inconnu')}</div>
  <div class="g" style="grid-template-columns:1.6fr 1fr">
    <div class="card"><h3>${ico('net')}Réseau des chaînes de transmission <small>· ${D.chaines.length} chaînes</small></h3><div id="v-net"></div></div>
    <div class="card"><h3>${ico('link')}Lien épidémiologique des cas</h3><div class="q">Le cas était-il déjà connu comme contact ?</div><div id="v-lien"></div>
      <h3 style="margin-top:18px">${ico('target')}Origine de l'exposition</h3><div class="q">Comment la date d'exposition est établie</div><div id="v-expo"></div></div>
  </div>
  <div class="g" style="grid-template-columns:1.4fr 1fr;margin-top:16px">
    <div class="card"><h3>${ico('layers')}Chaînes actives</h3><div class="q">Identifiant de chaîne attribué par l'outil (aucun ID de cas)</div><div id="t-ch"></div></div>
    <div class="card"><h3>${ico('file')}Investigations recommandées</h3><div class="q">Priorités de l'équipe de surveillance</div><div id="l-ch"></div></div>
  </div>`,
cont: () => `
  <div class="kc">${kc('b', 'users', C.s1, 'Contacts listés', fr(D.ct.listes), '', 'neu', 'médiane ' + D.ct.med + ' / cas', `renseignés sur ${D.ct.fiches_cl} fiches · ${D.ct.sans} fiches sans nombre`)}
  ${kc('g', 'check', C.s3, 'Contacts suivis', fr(D.ct.suivis), '', 'up-bad', p1(D.ct.suivis, D.ct.listes) + ' %', `nombre de suivis saisi sur ${D.ct.fiches_cs} fiches seulement`, ring(100 * D.ct.suivis / D.ct.listes, C.s3))}
  ${kc('a', 'alert', '#C88400', 'Contacts à haut risque', fr(D.ct.haut), '', 'neu', p1(D.ct.haut, D.ct.listes) + ' %', 'catégories « Haut » et « Très haut »')}
  ${kc('r', 'db', C.crit, 'Cas retrouvés dans DHIS2', D.ct.dh_ok, `/ ${D.ct.dh_tot}`, 'up-bad', p1(D.ct.dh_ok, D.ct.dh_tot) + ' %', `${D.ct.dh_tot - D.ct.dh_ok} ID introuvables dans la liste linéaire`)}</div>
  <div class="g" style="grid-template-columns:1fr 1fr 1fr">
    <div class="card"><h3>${ico('target')}Entonnoir des contacts</h3><div class="q">Somme des nombres saisis dans les fiches</div><div id="v-fun"></div></div>
    <div class="card"><h3>${ico('db')}Concordance Mapping × DHIS2</h3><div class="q">Cas retrouvés dans DHIS2 : contacts déclarés dans le mapping et contacts enregistrés</div><div id="v-dh"></div><div id="v-dhh" style="margin-top:10px"></div></div>
    <div class="card"><h3>${ico('alert', C.crit)}Alertes opérationnelles</h3><div class="q">Calculées sur les fiches</div><div id="l-ct"></div></div>
  </div>
  <div class="card" style="margin-top:16px"><h3>${ico('pin')}Contacts par zone de santé</h3><div class="q">Listés, suivis et part suivie · zones ≥ 5 cas</div><div id="t-ct"></div></div>`,
act: () => `
  <div class="kc">${kc('b', 'clip', C.s1, 'Actions ouvertes', D.actions.total, '', 'neu', 'toutes fiches', 'actions saisies ou suggérées non terminées')}
  ${kc('a', 'file', '#C88400', 'Fiches avec action ouverte', D.actions.fiches, `/ ${n}`, 'neu', p1(D.actions.fiches, n) + ' %', 'à suivre par les piliers')}
  ${kc('r', 'alert', C.crit, 'Fiches avec 5 actions ou plus', D.actions.dist[5] + D.actions.dist[6], '', 'up-bad', 'surcharge', 'cas à revoir en réunion')}
  ${kc('g', 'check', C.s3, 'Fiches sans action ouverte', D.actions.dist[0], '', 'dn-good', p1(D.actions.dist[0], n) + ' %', 'toutes les actions sont faites')}</div>
  <div class="g" style="grid-template-columns:1fr 1fr 1fr">
    <div class="card"><h3>${ico('chart')}Actions ouvertes par fiche</h3><div class="q">Nombre de fiches selon le nombre d'actions ouvertes</div><div id="v-adist"></div></div>
    <div class="card"><h3>${ico('pin')}Actions ouvertes par zone de santé</h3><div class="q">Zones les plus chargées</div><div id="v-azs"></div></div>
    <div class="card"><h3>${ico('target')}Actions ouvertes par niveau de risque du cas</h3><div class="q">Les cas à risque très élevé concentrent les actions</div><div id="v-arisk"></div></div>
  </div>
  <div class="card" style="margin-top:16px"><h3>${ico('target')}Priorités opérationnelles</h3><div class="q">Le détail par pilier, échéance et preuve est dans l'outil (tableau de bord › À traiter)</div><div id="l-act" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px"></div></div>`,
geo: () => `
  <div class="kc">${kc('b', 'globe', C.s1, 'Provinces touchées', K.prov, '', 'neu', 'RDC', D.prov.slice(0, 4).map(p => p[0] + ' ' + p[1]).join(' · '))}
  ${kc('a', 'map', '#C88400', 'Zones de santé touchées', K.zs, '', 'neu', `${D.zs.filter(z => z.n7).length} actives sur 7 j`, `${D.zs.filter(z => z.jours !== null && z.jours <= 3).length} zones avec un cas dans les 3 derniers jours`)}
  ${kc('g', 'pin', C.s3, 'Aires de santé touchées', K.as, '', 'neu', 'niveau le plus fin', `${(K.as / K.zs).toFixed(1).replace('.', ',')} aires par zone en moyenne`)}
  ${kc('r', 'alert', C.crit, 'Zones sans cas depuis 21 j', D.zs.filter(z => z.jours !== null && z.jours > 21).length, '', 'dn-good', 'vers la fin', 'compte à rebours de 42 jours')}</div>
  <div class="g" style="grid-template-columns:1fr 1fr 1fr">
    ${CARTES.prov.map(([p, svg]) => `<div class="card carte"><h3>${ico('map')}${esc(p)}</h3><div class="q">Délai depuis le dernier cas par zone de santé · cliquer pour descendre</div>${svg}</div>`).join('')}
  </div>
  <div class="card" style="margin-top:16px"><h3>${ico('pin')}Situation géographique par zone de santé</h3><div class="q">Toutes les zones touchées, de la plus récente à la plus ancienne</div><div id="t-geo"></div></div>`,
mob: () => `
  <div class="kc">${kc('b', 'send', C.s1, 'Cas avec déplacement', D.mob.depl, `/ ${n}`, 'up-bad', p1(D.mob.depl, n) + ' %', 'déplacements documentés dans la chronologie')}
  ${kc('a', 'truck', '#C88400', 'Déplacements par cas', String(D.mob.moy).replace('.', ','), 'en moyenne', 'neu', 'période contagieuse', `${D.mob.etapes_med} étapes par chronologie (médiane)`)}
  ${kc('g', 'pin', C.s3, 'Lieux fréquentés', fr(D.mob.lieux), '', 'neu', (D.mob.lieux / n).toFixed(1).replace('.', ',') + ' / cas', 'structures, domiciles, marchés, lieux de culte')}
  ${kc('r', 'alert', C.crit, 'Cas passés par des funérailles', D.mob.fun, '', 'up-bad', 'risque élevé', 'participation à des funérailles ou enterrements')}</div>
  <div class="g" style="grid-template-columns:1fr 1fr 1fr">
    <div class="card"><h3>${ico('truck')}Moyens de transport utilisés</h3><div class="q">Nombre de cas ayant utilisé chaque moyen</div><div id="v-tr"></div></div>
    <div class="card"><h3>${ico('send')}Déplacements moyens par zone de santé</h3><div class="q">Nombre moyen de déplacements par cas · zones ≥ 5 cas</div><div id="v-dzs"></div></div>
    <div class="card"><h3>${ico('target')}Points d'attention</h3><div class="q">Mobilité et risque de diffusion</div><div id="l-mob"></div></div>
  </div>
  <div class="note-src">Les rapports journaliers des points d'entrée et de contrôle (Riposte ▾ › PoE / PoC) alimenteront la couverture du screening sur cet écran ; ils ne sont pas dans l'export « Liste des cas ».</div>`,
pci: () => `
  <div class="kc">${kc('b', 'shield', C.s1, 'Sites PCI documentés', D.pci.sites, '', 'neu', (D.pci.sites / n).toFixed(1).replace('.', ',') + ' / cas', `${D.pci.sans_site} fiches sans aucun site PCI`)}
  ${kc('g', 'check', C.s3, 'Sites décontaminés', D.pci.ok, '', 'up-bad', p1(D.pci.ok, D.pci.sites) + ' %', 'cible : 100 % des lieux d\'exposition', ring(100 * D.pci.ok / D.pci.sites, C.s3))}
  ${kc('r', 'alert', C.crit, 'Sites « Non » ou inconnu', D.pci.non, '', 'up-bad', 'à traiter', 'décontamination non faite ou non documentée')}
  ${kc('a', 'users', '#C88400', 'Agents de santé infectés', D.pci.ppl, '', 'up-bad', p1(D.pci.ppl, n) + ' % des cas', 'signal d\'infection en structure de soins')}</div>
  <div class="g" style="grid-template-columns:1.2fr 1fr 1fr">
    <div class="card"><h3>${ico('chart')}Décontamination par zone de santé</h3><div class="q">Sites décontaminés et restants · zones ≥ 5 sites</div>
      <div class="lgd"><span><i style="background:${C.good}"></i>Décontaminés</span><span><i style="background:${C.crit}"></i>Restants</span></div><div id="v-pzs"></div></div>
    <div class="card"><h3>${ico('drop')}Expositions à risque documentées</h3><div class="q">Nombre de cas dont la chronologie contient l'exposition</div><div id="v-expr"></div></div>
    <div class="card"><h3>${ico('target')}Priorités PCI</h3><div class="q">Structures et lieux</div><div id="l-pci"></div></div>
  </div>`,
clin: () => `
  <div class="kc">${kc('b', 'users', C.s1, 'Âge médian', String(D.age_med).replace('.', ','), 'ans', 'neu', p1(D.femmes, n) + ' % de femmes', `${D.pyr.H.reduce((a, b) => a + b, 0)} hommes · ${D.pyr.F.reduce((a, b) => a + b, 0)} femmes`)}
  ${kc('r', 'alert', C.crit, 'Létalité', p1(K.deces, n), '%', 'up-bad', K.deces + ' décès', `décès à J+${K.d_dc} en médiane après le J0`)}
  ${kc('g', 'heart', C.s3, 'Phase sèche documentée', D.sympt.phases.seche.n, `/ ${n}`, 'neu', p1(D.sympt.phases.seche.n, n) + ' %', `humide : ${D.sympt.phases.humide.n} · critique : ${D.sympt.phases.critique.n}`)}
  ${kc('a', 'virus', '#C88400', 'Fièvre en phase sèche', D.sympt.phases.seche.v[0], '%', 'neu', 'signe d\'appel', 'définition de cas à rappeler aux équipes')}</div>
  <div class="g" style="grid-template-columns:1.25fr 1fr 1fr">
    <div class="card"><h3>${ico('heart')}Symptômes par phase de la maladie</h3><div class="q">% des cas documentés présentant le signe dans la phase</div><div id="t-sy"></div></div>
    <div class="card"><h3>${ico('users')}Pyramide des âges</h3><div class="q">Cas par âge et sexe · décès en couleur pleine</div><div id="v-pyr"></div></div>
    <div class="card"><h3>${ico('chart')}Létalité par tranche d'âge</h3><div class="q">% de décès parmi les cas de la tranche</div><div id="v-let"></div></div>
  </div>`,
qual: () => `
  <div class="kc">${kc('g', 'check', C.s3, 'Complétude moyenne', String(K.compl).replace('.', ','), '%', 'up-bad', 'cible 95 %', `${D.compl_dist[3]} fiches à 90 % ou plus`, ring(K.compl, C.s3))}
  ${kc('a', 'file', '#C88400', 'Valeurs à harmoniser', (D.qualite.zs_non_harmonisee || 0) + (D.qualite.lien_non_harmonise || 0) + (D.qualite.etat_non_harmonise || 0) + (D.qualite.province_non_harmonisee || 0), '', 'up-bad', 'saisie libre', 'ex. « Decede », « DECECE », « De Beni »')}
  ${kc('r', 'alert', C.crit, 'Dates ou délais aberrants', (D.qualite.date_aberrante || 0) + (D.qualite.delai_aberrant || 0), '', 'up-bad', 'à corriger', 'J0 hors épidémie (2021, 2028), délais > 60 j')}
  ${kc('b', 'db', C.s1, 'ID introuvables dans DHIS2', D.ct.dh_tot - D.ct.dh_ok, `/ ${D.ct.dh_tot}`, 'up-bad', p1(D.ct.dh_tot - D.ct.dh_ok, D.ct.dh_tot) + ' %', 'N° EPID à vérifier dans la fiche')}</div>
  <div class="g" style="grid-template-columns:1fr 1fr 1fr">
    <div class="card"><h3>${ico('file')}Champs renseignés</h3><div class="q">% des fiches · trait noir = cible 90 %</div><div id="v-ch2"></div></div>
    <div class="card"><h3>${ico('db')}Rapprochement DHIS2 par province</h3><div class="q">% des ID du mapping retrouvés dans la liste linéaire DHIS2</div><div id="v-dhp"></div></div>
    <div class="card"><h3>${ico('alert', C.crit)}Anomalies détectées</h3><div class="q">Contrôles automatiques sur l'export</div><div id="v-anom"></div></div>
  </div>`};

// ------------------------------------------------------------------ remplissage
const Zs5 = D.zs.filter(z => z.n >= 5);
const jchip = j => j === null ? chip('nd', 'ND') : j <= 3 ? chip('crit', j ? `${j} j` : "aujourd'hui") : j <= 7 ? chip('serious', `${j} j`) : j <= 21 ? chip('warn', `${j} j`) : chip('good', `${j} j`);
const REMPLIR = {
strat() {
  bars2('#v-sem', D.semaines.map(s => 'S' + s), D.cas_sem, D.dc_sem, {w: 820, h: 300, ca: C.s1, cb: C.crit});
  segbar('#v-risk', D.risque.slice(0, 4).map((r, i) => [r[0], r[1], [C.crit, C.s2, C.nd, C.warn][i]]), {w: 470});
  hbars('#v-prov', D.prov.slice(0, 5).map(p => [p[0] === '?' ? 'Non précisée' : p[0], p[1], C.s1]), {w: 470, lw: 120, rh: 28});
  table('#t-zs', ['Zone de santé', 'Province', 'Cas', 'Décès', '7 j', 'Dernier cas'], D.zs.slice(0, 8).map(z => [`<b>${z.zs}</b>`, z.prov, `<b>${z.n}</b>`, z.dc, z.n7 ? `<b style="color:#9A3D16">+${z.n7}</b>` : '0', jchip(z.jours)]), ['', '', 'n', 'n', 'n', '']);
  const hausse = D.zs.filter(z => z.s48 > z.s47 && z.s48 >= 3).sort((a, b) => (b.s48 - b.s47) - (a.s48 - a.s47));
  $('#l-sig').innerHTML = sig('r', '!', `Létalité de ${p1(K.deces, n)} % et ${K.comm} décès communautaires`, 'détection tardive : renforcer l\'alerte communautaire et les EDS') +
    sig('a', '⏱', `Isolement à J+${K.d_iso} en médiane`, `cible ≤ 3 jours · ${n - D.funnel[4][1]} cas sans date d'isolement`) +
    (hausse[0] ? sig('a', '▲', `Hausse à ${hausse[0].zs}`, `${hausse[0].s47} → ${hausse[0].s48} cas (${S1} → ${S2})`) : '') +
    sig('b', 'i', `${D.lien.filter(l => l[0] === 'Non contact' || l[0] === 'Inconnu').reduce((a, l) => a + l[1], 0)} cas sans lien connu`, 'chaînes de transmission à investiguer');
},
couv() {
  hbars('#v-czs', Zs5.slice().sort((a, b) => b.compl - a.compl).slice(0, 12).map(z => [z.zs, z.compl, tonC(ton(z.compl)), z.compl + ' %']), {max: 100, target: 95, lw: 140});
  barsV('#v-cdist', ['< 50 %', '50–69 %', '70–89 %', '≥ 90 %'], D.compl_dist, {w: 520, h: 300, lab: 'all', colors: [C.crit, C.warn, C.s1, C.good]});
  hbars('#v-champs', D.champs.map(c => [c[0], c[1], tonC(ton(c[1])), c[1] + ' %']), {max: 100, target: 90, lw: 190});
  table('#t-prio', ['#', 'Zone de santé', 'Province', 'Fiches', 'Complétude', 'Statut', 'Action recommandée'], Zs5.slice().sort((a, b) => a.compl - b.compl).slice(0, 6).map((z, i) => [i + 1, `<b>${z.zs}</b>`, z.prov, z.n, `<b>${z.compl} %</b>`,
    z.compl < 70 ? chip('crit', 'Critique') : chip('warn', 'À compléter'), '→ ' + (z.compl < 70 ? 'Relancer l\'équipe d\'investigation' : 'Compléter les champs manquants')]), ['', '', '', 'n', 'n', '', '']);
},
dyn() {
  lines2('#v-jour', D.jours, D.notif_j, D.cas_j, {w: 880, h: 290});
  bars2('#v-sem2', D.semaines.slice(-8).map(s => 'S' + s), D.cas_sem.slice(-8), D.dc_sem.slice(-8), {w: 560, h: 290, ca: C.s1, cb: C.crit});
  $('#v-sem2').insertAdjacentHTML('beforebegin', `<div class="lgd"><span><i style="background:${C.s1}"></i>Cas confirmés</span><span><i style="background:${C.crit}"></i>Décès</span></div>`);
  const v = D.zs.filter(z => z.s47 + z.s48 >= 3).map(z => ({...z, var: z.s47 ? Math.round(100 * (z.s48 - z.s47) / z.s47) : null})).sort((a, b) => b.s48 - a.s48).slice(0, 7);
  table('#t-var', ['Zone de santé', S1, S2, 'Variation', 'Tendance'], v.map(z => [`<b>${z.zs}</b>`, z.s47, `<b>${z.s48}</b>`, z.var === null ? chip('crit', 'nouveau') : z.var > 0 ? `<b style="color:#A11F1F">+${z.var} %</b>` : `<b style="color:#11643A">${z.var} %</b>`,
    z.var === null || z.var > 20 ? chip('crit', 'Élevé') : z.var > 0 ? chip('warn', 'Modéré') : chip('good', 'En baisse')]), ['', 'n', 'n', 'n', '']);
  const up = v.filter(z => z.var === null || z.var > 0);
  $('#l-sig2').innerHTML = (up[0] ? sig('r', '▲', `Hausse à ${up[0].zs}`, `${up[0].s47} → ${up[0].s48} cas`) : '') + (up[1] ? sig('a', '▲', `Hausse à ${up[1].zs}`, `${up[1].s47} → ${up[1].s48} cas`) : '') +
    sig('a', '⏱', `Notification à J+${K.d_notif}`, 'cible ≤ 3 jours après les premiers signes') + sig('b', 'i', `${D.zs.filter(z => z.jours !== null && z.jours > 14).length} zones sans cas depuis plus de 14 jours`, 'surveillance active à maintenir');
},
parc() {
  const f = D.funnel, ic = ['users', 'file', 'drop', 'check', 'bed'];
  $('#v-flow').innerHTML = f.map((s, i) => `${i ? '<div class="ar">➜</div>' : ''}<div class="st">${ico(ic[i], C.s1, 26)}<span style="display:block;margin-top:6px">${s[0]}</span><b>${fr(s[1])}</b><em>${p1(s[1], n)} %</em></div>`).join('');
  donut('#v-issue', D.issue.map((x, i) => [x[0], x[1], {Vivant: C.s1, 'Décès': C.crit, 'En traitement': C.s3, Inconnu: C.nd}[x[0]]]), n, 'cas', 170);
  const iz = D.iso_zs.slice(0, 9);
  (function () { const w = 520, rh = 30, lw = 140, h = iz.length * rh + 10, mx = Math.max(...iz.map(x => x[1]), K.d_iso) + 1, bw = w - lw - 50; let s = '';
    iz.forEach((x, i) => { const y = i * rh + 4, c = x[1] <= 3 ? C.good : x[1] <= 5 ? C.warn : C.crit; s += `<text x="0" y="${y + 17}" class="lbl2">${x[0]}</text>` + rbar(lw, y + 6, bw * x[1] / mx, 15, 4, c, false) + `<text x="${w}" y="${y + 18}" text-anchor="end" class="lbl">${String(x[1]).replace('.', ',')} j</text>`; });
    const gx = lw + bw * K.d_iso / mx; s += `<line x1="${gx}" x2="${gx}" y1="0" y2="${h}" stroke="${C.crit}" stroke-dasharray="4 3" stroke-width="1.5"/>`; $('#v-isozs').innerHTML = svg(w, h, s); })();
  dots('#v-dl', D.delais.map(d => [d[0], d[1][0], d[1][1], d[1][2], {"J0 → notification": 3, "J0 → isolement": 3, "J0 → confirmation": 5, "J0 → décès": null}[d[0]]]), {w: 520, max: 20, step: 5});
  $('#l-parc').innerHTML = sig('r', '⏱', 'Réduire le délai J0 → isolement', `${K.d_iso} j en médiane, cible ≤ 3 j`) + sig('a', '⌂', 'Documenter l\'isolement', `${n - D.funnel[4][1]} fiches sans date d'isolement`) +
    sig('a', '!', 'Inhumations dignes et sécurisées', `${D.eds[2]} décès sans information sur l'inhumation`) + sig('g', '✓', 'Laboratoire dans les délais', `résultat en ${K.d_lab} h (seuil 48 h)`);
},
chain() {
  reseau('#v-net', D.chaines, 1040, 400);
  segbar('#v-lien', D.lien.map(l => [l[0], l[1], {'Contact connu suivi': C.s1, 'Contact connu (suivi non précisé)': '#86b6ef', 'Non contact': C.s2, Inconnu: C.nd}[l[0]]]), {w: 560});
  hbars('#v-expo', D.expo.map(e => [{'estimée': 'Estimée depuis le J0', 'dernier contact': 'Dernier contact avec le cas source', 'à rechercher': 'Source à rechercher'}[e[0]] || e[0], e[1], e[0] === 'à rechercher' ? C.s2 : C.s1]), {w: 560, lw: 230});
  table('#t-ch', ['Chaîne', 'Zone de santé', 'Cas', 'Décès', 'Dernier cas', 'Statut'], D.chaines.slice(0, 7).map((c, i) => [`<span class="chip blue">C-${String(i + 1).padStart(2, '0')}</span>`, `<b>${c.zs}</b>`, c.n, c.dc,
    c.der ? c.der.slice(8, 10) + '/' + c.der.slice(5, 7) : 'ND', c.ouverte ? chip('crit', '● Active') : chip('good', 'Close')]), ['', '', 'n', 'n', '', '']);
  const c1 = D.chaines[0];
  $('#l-ch').innerHTML = sig('r', '!', `C-01 · ${c1.zs} : ${c1.n} cas liés`, 'plus grande chaîne : élargir la recherche des contacts') +
    sig('a', '?', `${D.expo.find(e => e[0] === 'à rechercher')[1]} cas avec source à rechercher`, 'investigation du lien épidémiologique') +
    sig('a', '↔', `${D.src_total - D.src_base} cas source absents de Mapping Épi`, 'créer ou retrouver la fiche du cas source') + sig('b', 'i', `${D.lien.find(l => l[0] === 'Non contact')[1]} non contacts`, 'cas apparus hors des listes de contacts');
},
cont() {
  funnelShape('#v-fun', [['Contacts listés', D.ct.listes, '100 %'], ['À haut risque', D.ct.haut, p1(D.ct.haut, D.ct.listes) + ' % des listés'], ['Suivis', D.ct.suivis, p1(D.ct.suivis, D.ct.listes) + ' % des listés'], ['Vaccinés', D.ct.vaccines, p1(D.ct.vaccines, D.ct.listes) + ' % des listés']],
    ['#1C4F8F', '#2a78d6', '#1baf7a', '#0ca30c']);
  hbars('#v-dh', [['Contacts déclarés dans le mapping', D.ct.dh_cl, C.s1], ['Contacts enregistrés dans DHIS2', D.ct.dh_n, C.s2]], {w: 520, lw: 230, rh: 34});
  const dd = D.ct.dh_diff, b = [['Plus dans DHIS2', dd.filter(x => x < 0).length], ['Égal', dd.filter(x => x === 0).length], ['+1 à +10', dd.filter(x => x > 0 && x <= 10).length], ['+11 à +50', dd.filter(x => x > 10 && x <= 50).length], ['> +50', dd.filter(x => x > 50).length]];
  barsV('#v-dhh', b.map(x => x[0]), b.map(x => x[1]), {w: 520, h: 200, lab: 'all', colors: [C.s1, C.good, C.warn, C.s2, C.crit]});
  $('#v-dhh').insertAdjacentHTML('beforebegin', '<div class="q" style="margin-top:12px">Écart mapping − DHIS2 par cas (nombre de cas)</div>');
  $('#l-ct').innerHTML = sig('r', '!', `Suivi documenté sur ${D.ct.fiches_cs} fiches seulement`, `${D.ct.fiches_cl - D.ct.fiches_cs} fiches avec contacts listés mais sans nombre de suivis`) +
    sig('a', '↔', `Sous-listing DHIS2 : ${fr(D.ct.dh_cl - D.ct.dh_n)} contacts d'écart`, 'sur les cas retrouvés dans DHIS2') + sig('a', '?', `${D.ct.sans} fiches sans nombre de contacts`, 'catégories à dénombrer') +
    sig('b', 'i', `${fr(D.ct.vaccines)} contacts vaccinés saisis`, 'compléter la vaccination par groupe de contacts');
  table('#t-ct', ['Zone de santé', 'Province', 'Cas', 'Contacts listés', 'Contacts suivis', 'Part suivie', 'Retrouvés DHIS2'], Zs5.slice(0, 9).map(z => [`<b>${z.zs}</b>`, z.prov, z.n, fr(z.cl), fr(z.cs),
    z.cl ? (p => chip(ton(p), Math.round(p) + ' %'))(100 * z.cs / z.cl) : chip('nd', 'ND'), `${z.dh_ok} / ${z.dh_tot}`]), ['', '', 'n', 'n', 'n', 'n', 'n']);
},
act() {
  barsV('#v-adist', ['0', '1', '2', '3', '4', '5', '6 et +'], D.actions.dist, {w: 520, h: 290, lab: 'all', colors: [C.good, C.s1, C.s1, C.s1, C.s1, C.s2, C.s2]});
  hbars('#v-azs', D.zs.filter(z => z.actions).sort((a, b) => b.actions - a.actions).slice(0, 9).map(z => [z.zs, z.actions, C.s1]), {w: 520, lw: 140});
  hbars('#v-arisk', D.risque_actions.map(r => [r[0], r[1], r[0] === 'Très élevé' ? C.crit : r[0] === 'Élevé' ? C.s2 : C.s1]), {w: 520, lw: 140});
  const top = D.zs.filter(z => z.actions).sort((a, b) => b.actions - a.actions);
  $('#l-act').innerHTML = sig('r', '1', `Revoir les ${D.actions.dist[5] + D.actions.dist[6]} fiches très chargées`, '5 actions ouvertes ou plus') + sig('a', '2', `Appuyer ${top[0].zs} et ${top[1].zs}`, `${top[0].actions + top[1].actions} actions ouvertes à elles deux`) +
    sig('b', '3', 'Valider les actions faites', 'preuve et superviseur dans l\'étape 8 de la fiche');
},
geo() {
  table('#t-geo', ['Zone de santé', 'Province', 'Aires touchées', 'Cas', 'Décès', 'Nouveaux 7 j', 'Dernier cas'], D.zs.slice().sort((a, b) => (a.jours ?? 999) - (b.jours ?? 999)).slice(0, 10).map(z => [`<b>${z.zs}</b>`, z.prov, z.as, `<b>${z.n}</b>`, z.dc, z.n7 ? `+${z.n7}` : '0', jchip(z.jours)]), ['', '', 'n', 'n', 'n', 'n', '']);
},
mob() {
  hbars('#v-tr', D.transports.map(t => [t[0], t[1], C.s1]), {w: 520, lw: 200});
  hbars('#v-dzs', D.depl_zs.map(z => [z[0], z[1], C.s1, String(z[1]).replace('.', ',')]), {w: 520, lw: 150});
  $('#l-mob').innerHTML = sig('r', '!', `${p1(D.mob.depl, n)} % des cas se sont déplacés`, 'pendant la période contagieuse') + sig('a', '⚑', `${D.mob.fun} cas passés par des funérailles`, 'événements à fort potentiel de diffusion') +
    sig('a', '➜', `Taxi-moto : ${(D.transports.find(t => /moto/i.test(t[0])) || ['', 0])[1]} cas`, 'motards à lister comme contacts') + sig('b', 'i', `${fr(D.mob.lieux)} lieux fréquentés`, 'base des lieux communs et de la PCI');
},
pci() {
  const pz = D.pci_zs; (function () { const w = 640, rh = 32, lw = 140, h = pz.length * rh + 6, mx = Math.max(...pz.map(p => p[1])), bw = w - lw - 70; let s = '';
    pz.forEach((p, i) => { const y = i * rh + 4, a = bw * p[2] / mx, b = bw * (p[1] - p[2]) / mx; s += `<text x="0" y="${y + 18}" class="lbl2">${p[0]}</text><rect x="${lw}" y="${y + 7}" width="${Math.max(0, a - 2)}" height="16" fill="${C.good}"/>` +
      rbar(lw + a, y + 7, b, 16, 4, C.crit, false) + `<text x="${w}" y="${y + 20}" text-anchor="end" class="lbl">${p1(p[2], p[1])} %</text>`; });
    $('#v-pzs').innerHTML = svg(w, h, s); })();
  hbars('#v-expr', [['Liquides biologiques', D.pci.liq, C.s2], ['Contact avec le corps', D.pci.corps, C.crit], ['Soins sans mesures PCI', D.pci.sanspci, C.s2], ['Agents de santé infectés', D.pci.ppl, C.s1]], {w: 520, lw: 200});
  $('#l-pci').innerHTML = sig('r', '!', `${D.pci.non} sites non décontaminés ou inconnus`, 'planifier les équipes PCI') + sig('r', '+', `${D.pci.ppl} agents de santé infectés`, 'triage, isolement et EPI dans les structures') +
    sig('a', '?', `${D.pci.sans_site} fiches sans site PCI`, 'compléter l\'étape 6 de la fiche') + sig('b', 'i', `${D.pci.sanspci} cas soignés sans PCI`, 'structures à évaluer');
},
clin() {
  seqHeat('#t-sy', ['Phase sèche', 'Phase humide', 'Phase critique'], D.sympt.labels.map((l, i) => [l, [D.sympt.phases.seche.v[i], D.sympt.phases.humide.v[i], D.sympt.phases.critique.v[i]]]));
  pyramide('#v-pyr', ['0–4', '5–14', '15–24', '25–34', '35–44', '45–54', '55–64', '65+'], D.pyr.H, D.pyr.F, D.pyr.dH, D.pyr.dF);
  barsV('#v-let', ['0–4', '5–14', '15–24', '25–34', '35–44', '45–54', '55–64', '65+'], D.let_age, {w: 520, h: 300, max: 100, lab: 'all', colors: Array(8).fill(C.crit)});
},
qual() {
  hbars('#v-ch2', D.champs.map(c => [c[0], c[1], tonC(ton(c[1])), c[1] + ' %']), {max: 100, target: 90, lw: 190});
  hbars('#v-dhp', D.dh_prov.map(p => [p[0], p[2] ? Math.round(100 * p[1] / p[2]) : 0, tonC(ton(p[2] ? 100 * p[1] / p[2] : null)), `${p[1]} / ${p[2]}`]), {max: 100, lw: 120, vw: 80});
  const q = D.qualite;
  hbars('#v-anom', [['Fiches sans ID du cas', q.sans_id || 0, C.crit], ['Zone de santé mal écrite', q.zs_non_harmonisee || 0, C.warn], ['État du cas non harmonisé', q.etat_non_harmonise || 0, C.warn],
    ['Lien épidémiologique non harmonisé', q.lien_non_harmonise || 0, C.warn], ['Délai aberrant (> 60 j)', q.delai_aberrant || 0, C.crit], ['Date hors épidémie', q.date_aberrante || 0, C.crit],
    ['Nombre impossible (téléphone)', q.nombre_impossible || 0, C.crit]], {w: 520, lw: 230});
}};


// ------------------------------------------------------------------ amorçage : l'écran demandé par la page
const vue = window.TDB_VUE, zone = document.getElementById('tdb-vue');
document.querySelectorAll('[data-ico]').forEach(e => { const on = e.closest('.it.on'); e.innerHTML = e.id === 'tdb-ico' ? ico(e.dataset.ico, C.s1, 30) : ico(e.dataset.ico, on ? '#fff' : '#9FB6D1', 19); });
const ALIAS = {strategique: 'strat', couverture: 'couv', dynamique: 'dyn', parcours: 'parc', chaines: 'chain', contacts: 'cont', actions: 'act',
               geo: 'geo', mobilite: 'mob', pci: 'pci', clinique: 'clin', qualite: 'qual'};
const k = ALIAS[vue] || 'strat';
if (!D || !D.n) { zone.innerHTML = '<div class="vide">Aucune fiche dans le périmètre et la période choisis.</div>'; return; }
zone.innerHTML = ECRANS[k]() + `<div class="note-src">${SRC}</div>`;
REMPLIR[k]();
})();

