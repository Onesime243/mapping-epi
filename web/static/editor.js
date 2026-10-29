/* Mapping Épi — éditeur web (sans dépendance externe). */
(function () {
  'use strict';
  const ID = window.CASE_ID;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  let S = null, PYR = {}, C = null, CTRL = null, dirty = false, saving = null, timer = null, visual = 'mapping';

  // ------------------------------------------------------------------ réseau
  async function api(url, opts) {
    opts = opts || {};
    opts.headers = Object.assign({'X-CSRF': window.CSRF, 'Content-Type': 'application/json'}, opts.headers || {});
    const r = await fetch(url, opts);
    if (r.status === 401) { location.href = '/connexion?next=' + encodeURIComponent(location.pathname); throw new Error('session'); }
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || ('Erreur ' + r.status));
    return j;
  }
  function toast(msg, ms) {
    const t = $('#toast'); t.textContent = msg; t.style.display = 'block';
    clearTimeout(t._h); t._h = setTimeout(() => { t.style.display = 'none'; }, ms || 2600);
  }
  function setStatus(txt, err) { const s = $('#status'); s.textContent = txt; s.className = 'status' + (err ? ' err' : ''); }

  function changed() {
    dirty = true; setStatus('Modifications non enregistrées…');
    clearTimeout(timer); timer = setTimeout(() => save(false), 900);
  }
  async function save(version, comment) {
    if (saving) await saving.catch(() => {});
    if (!dirty && !version) return;
    dirty = false; setStatus('Enregistrement…');
    const q = version ? ('?version=1&commentaire=' + encodeURIComponent(comment || '')) : '';
    saving = api('/api/cas/' + ID + q, {method: 'PUT', body: JSON.stringify(C)}).then(j => {
      CTRL = j.controls; updateComputed(); renderControls(); renderSuggestions(); refreshPreview();
      const t = new Date(j.saved_at);
      setStatus((version ? 'Version enregistrée' : 'Enregistré') + ' à ' + t.toLocaleTimeString('fr-FR', {hour: '2-digit', minute: '2-digit'}));
      updateTitle();
    }).catch(e => { dirty = true; setStatus('Échec : ' + e.message, true); });
    return saving;
  }
  async function flush() { clearTimeout(timer); if (dirty) await save(false); else if (saving) await saving.catch(() => {}); }
  window.addEventListener('beforeunload', e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });

  function updateTitle() {
    const rang = C.rang ? 'Cas ' + C.rang : 'Cas';
    $('#caseTitle').textContent = rang + ' – ' + C.maladie + ' – ZS ' + (C.zs || '?') + ' (' + (C.aire_sante || '?') + ')';
  }

  // ------------------------------------------------------------- utilitaires
  function el(tag, attrs, kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === 'text') e.textContent = v;
      else if (k === 'on') for (const [ev, fn] of Object.entries(v)) e.addEventListener(ev, fn);
      else if (v !== null && v !== undefined && v !== false) e.setAttribute(k, v === true ? '' : v);
    }
    (kids || []).forEach(k => k && e.appendChild(typeof k === 'string' ? document.createTextNode(k) : k));
    return e;
  }
  function options(sel, list, value, emptyLabel) {
    sel.innerHTML = '';
    const vals = list.slice();
    if (value && !vals.includes(value)) vals.unshift(value);
    vals.forEach(v => sel.appendChild(el('option', {value: v, text: v === '' ? (emptyLabel || '—') : v})));
    sel.value = value || '';
  }
  function datalist(id, items) {
    let d = document.getElementById(id);
    if (!d) { d = el('datalist', {id}); document.body.appendChild(d); }
    d.innerHTML = '';
    [...new Set(items.filter(Boolean))].sort((a, b) => a.localeCompare(b, 'fr')).forEach(v => d.appendChild(el('option', {value: v})));
    return id;
  }
  const minDate = () => S.annee_min + '-01-01';
  const norm = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/-/g, ' ').trim();
  function findKey(obj, name) { const n = norm(name); return Object.keys(obj || {}).find(k => norm(k) === n); }

  // -------------------------------------------------------------- identité
  function field(label, input, wide) {
    return el('div', {style: wide ? 'grid-column: 1 / -1' : null}, [el('label', {class: 'f', text: label}), input]);
  }
  function bindInput(inp, key, kind) {
    inp.addEventListener(kind === 'select' ? 'change' : 'input', () => {
      let v = inp.value;
      if (kind === 'int') v = v === '' ? null : parseInt(v, 10);
      else if (kind === 'float') v = v === '' ? null : parseFloat(String(v).replace(',', '.'));
      else if (kind === 'date') v = v || null;
      C[key] = v; changed();
    });
  }
  function renderIdentity() {
    const p = $('#p-identite'); p.innerHTML = '';
    p.appendChild(el('p', {class: 'hint', text: "Champs marqués * : indispensables au mapping. Une information inconnue reste vide : elle s'affichera « ? »."}));
    const g = el('div', {class: 'grid'});
    const inp = (key, type, extra) => { const i = el('input', Object.assign({type: type || 'text', value: C[key] ?? ''}, extra || {})); bindInput(i, key, type === 'number' ? 'int' : type === 'date' ? 'date' : 'text'); return i; };
    const sel = (key, list, emptyLabel) => { const s = el('select'); options(s, list, C[key] ?? '', emptyLabel); bindInput(s, key, 'select'); return s; };

    g.appendChild(field('Rang du cas * (1er, 2e…)', inp('rang', 'number', {min: 1})));
    const mal = el('input', {value: C.maladie || '', list: datalist('dl-mal', S.choices.diseases)}); bindInput(mal, 'maladie');
    g.appendChild(field('Maladie *', mal));
    g.appendChild(field('Statut', sel('statut', S.choices.status)));
    g.appendChild(field('Sexe *', sel('sexe', S.choices.sexes)));
    g.appendChild(field('Âge *', inp('age', 'number', {min: 0, max: 120, placeholder: 'vide si inconnu'})));
    g.appendChild(field('Unité', sel('age_unite', ['ans', 'mois'])));
    g.appendChild(field('Profession', inp('profession')));

    // Province → ZS → AS (pyramide sanitaire RDC)
    const prov = el('select'), zs = el('select'), as = el('input', {placeholder: 'choisir ou saisir…'});
    const fillZs = () => {
      const pk = findKey(PYR, prov.value);
      const zones = pk ? Object.keys(PYR[pk]) : [];
      options(zs, [''].concat(zones), C.zs || '', '— zone de santé —');
      fillAs();
    };
    const fillAs = () => {
      const pk = findKey(PYR, prov.value), zk = pk ? findKey(PYR[pk], zs.value) : null;
      as.setAttribute('list', datalist('dl-as', zk ? PYR[pk][zk] : []));
    };
    options(prov, [''].concat(Object.keys(PYR)), C.province || '', '— province —');
    prov.addEventListener('change', () => { C.province = prov.value; C.zs = ''; C.aire_sante = ''; as.value = ''; fillZs(); changed(); });
    zs.addEventListener('change', () => { C.zs = zs.value; C.aire_sante = ''; as.value = ''; fillAs(); changed(); });
    as.value = C.aire_sante || '';
    as.addEventListener('input', () => { C.aire_sante = as.value; changed(); });
    fillZs();
    g.appendChild(field('Province *', prov));
    g.appendChild(field('Zone de santé (ZS) *', zs));
    g.appendChild(field('Aire de santé (AS) *', as));
    g.appendChild(field('Village / quartier', inp('village')));
    const lat = el('input', {type: 'number', step: 'any', value: C.lat ?? '', placeholder: 'ex. 2.63'}); bindInput(lat, 'lat', 'float');
    const lon = el('input', {type: 'number', step: 'any', value: C.lon ?? '', placeholder: 'ex. 24.38'}); bindInput(lon, 'lon', 'float');
    g.appendChild(field('Latitude', lat));
    g.appendChild(field('Longitude', lon));
    g.appendChild(field('Date de confirmation *', inp('date_confirmation', 'date', {min: minDate()})));
    g.appendChild(field('Issue *', sel('issue', S.choices.issues)));
    g.appendChild(field('Risque global', sel('risque_global', [''].concat(S.choices.risks), 'Automatique')));
    g.appendChild(field('Investigateur *', inp('investigateur')));
    g.appendChild(field("Date d'investigation", inp('date_investigation', 'date', {min: minDate()})));
    g.appendChild(field('Note de bas de page', inp('note_pied'), true));
    p.appendChild(g);
  }

  // -------------------------------------------------------------- clinique
  function renderClinic() {
    const p = $('#p-clinique'); p.innerHTML = '';
    const g = el('div', {class: 'grid'});
    ['debut_symptomes', 'date_deces'].forEach((k, i) => {
      const inp = el('input', {type: 'date', min: minDate(), value: C[k] || ''}); bindInput(inp, k, 'date');
      g.appendChild(field(i ? 'Date de décès' : 'Début des symptômes (J0) *', inp));
    });
    p.appendChild(g);
    p.appendChild(el('p', {class: 'hint', text: "J0 sert à calculer la fenêtre d'exposition, la période contagieuse et les jours relatifs (J-17, J+9…)."}));
    p.appendChild(el('h2', {text: 'Symptômes'}));
    const box = el('div', {class: 'symptoms'});
    S.choices.symptoms.forEach(s => {
      const cb = el('input', {type: 'checkbox'}); cb.checked = C.symptomes.includes(s);
      cb.addEventListener('change', () => {
        C.symptomes = cb.checked ? C.symptomes.concat([s]) : C.symptomes.filter(x => x !== s); changed();
      });
      box.appendChild(el('label', {}, [cb, s + (S.choices.hemorrhagic.includes(s) ? ' 🩸' : '')]));
    });
    p.appendChild(box);
    const other = el('input', {value: C.symptomes_autres || '', placeholder: 'Autres symptômes (texte libre)', style: 'margin-top:12px'});
    bindInput(other, 'symptomes_autres');
    p.appendChild(other);
  }

  // --------------------------------------------------------------- tableaux
  function placeNames() {
    return C.places.map(p => p.nom).concat(C.events.map(e => e.lieu), C.events.map(e => e.lieu_arrivee)).filter(n => n && !n.includes('→'));
  }
  function blankRow(table) {
    const r = {};
    S.tables[table].forEach(c => {
      if (c.kind === 'computed') return;
      r[c.key] = c.kind === 'bool' ? false : (['int?', 'float?', 'date', 'datetime'].includes(c.kind) ? null : (c.kind === 'choice' ? (c.choices[0] || '') : ''));
    });
    if (table === 'events') r.type = 'Autre';
    if (table === 'contacts') r.risque = 'Haut';
    if (table === 'ipc') r.statut = 'Non';
    if (table === 'actions') { r.priorite = 'Important'; r.statut = 'À faire'; }
    return r;
  }
  function cell(table, row, c, i) {
    const v = row[c.key];
    const set = val => { row[c.key] = val; changed(); };
    const w = Math.max(70, Math.round((c.width || 120) * 0.9)) + 'px';
    let inp;
    switch (c.kind) {
      case 'bool':
        inp = el('input', {type: 'checkbox', title: c.tip || c.label}); inp.checked = !!v;
        inp.addEventListener('change', () => set(inp.checked));
        return el('td', {class: 'chk'}, [inp]);
      case 'choice':
        inp = el('select', {style: 'min-width:' + w}); options(inp, c.choices, v || '', 'Auto');
        inp.addEventListener('change', () => set(inp.value));
        break;
      case 'combo':
        inp = el('input', {value: v || '', list: datalist('dl-' + table + '-' + c.key, c.choices), style: 'min-width:' + w});
        inp.addEventListener('input', () => set(inp.value));
        break;
      case 'date':
        inp = el('input', {type: 'date', min: minDate(), value: v || '', style: 'min-width:150px'});
        inp.addEventListener('input', () => set(inp.value || null));
        break;
      case 'datetime':
        inp = el('input', {type: 'datetime-local', min: minDate() + 'T00:00', value: v ? String(v).slice(0, 16) : '', style: 'min-width:200px'});
        inp.addEventListener('input', () => set(inp.value || null));
        break;
      case 'int?':
        inp = el('input', {inputmode: 'numeric', value: v === null || v === undefined ? '' : v, placeholder: '?', style: 'width:90px'});
        inp.addEventListener('input', () => { const t = inp.value.trim(); set(t === '' || t === '?' ? null : (parseInt(t, 10) || 0)); });
        break;
      case 'float?':
        inp = el('input', {type: 'number', step: 'any', value: v ?? '', style: 'width:110px'});
        inp.addEventListener('input', () => set(inp.value === '' ? null : parseFloat(inp.value)));
        break;
      case 'computed':
        return el('td', {class: 'comp', 'data-comp': table + ':' + i + ':' + c.key});
      default:
        inp = el('input', {value: v || '', style: 'min-width:' + w, list: c.complete ? 'dl-places' : null});
        inp.addEventListener('input', () => set(inp.value));
        if (c.complete) inp.addEventListener('focus', () => datalist('dl-places', placeNames()));
    }
    if (c.tip) inp.title = c.tip;
    return el('td', {}, [inp]);
  }
  function renderTable(table) {
    const t = $('#t-' + table); t.innerHTML = '';
    const cols = S.tables[table];
    const head = el('tr', {}, cols.map(c => el('th', {text: c.label, title: c.tip || ''})).concat([el('th', {text: ''})]));
    t.appendChild(el('thead', {}, [head]));
    const body = el('tbody');
    C[table].forEach((row, i) => {
      const tr = el('tr', {}, cols.map(c => cell(table, row, c, i)));
      const op = (lbl, title, fn) => el('button', {type: 'button', text: lbl, title, on: {click: fn}});
      tr.appendChild(el('td', {class: 'ops'}, [
        op('↑', 'Monter', () => move(table, i, -1)), op('↓', 'Descendre', () => move(table, i, 1)),
        op('⧉', 'Dupliquer', () => { const cp = JSON.parse(JSON.stringify(row)); cp.id = Math.random().toString(16).slice(2, 12); C[table].splice(i + 1, 0, cp); renderTable(table); changed(); }),
        op('✕', 'Supprimer', () => { C[table].splice(i, 1); renderTable(table); changed(); })]));
      body.appendChild(tr);
    });
    if (!C[table].length) body.appendChild(el('tr', {}, [el('td', {colspan: cols.length + 1, class: 'muted', text: 'Aucune ligne — cliquez sur « Ajouter ».', style: 'padding:14px'})]));
    t.appendChild(body);
    updateComputed();
  }
  function move(table, i, d) {
    const j = i + d; if (j < 0 || j >= C[table].length) return;
    [C[table][i], C[table][j]] = [C[table][j], C[table][i]]; renderTable(table); changed();
  }
  function updateComputed() {
    if (!CTRL) return;
    $$('[data-comp]').forEach(td => {
      const [table, i, key] = td.getAttribute('data-comp').split(':');
      const comp = CTRL.computed[table] && CTRL.computed[table][+i];
      if (comp === undefined) { td.textContent = ''; return; }
      if (table === 'events') {
        td.textContent = comp.lvl + (C.events[+i] && !C.events[+i].risque ? ' ✓' : '');
        td.style.color = comp.color; td.title = comp.why;
      } else td.textContent = comp;
    });
  }

  // ---------------------------------------------------- contrôles / actions
  function renderControls() {
    const p = $('#p-controles'); if (!CTRL) return; p.innerHTML = '';
    const fmt = d => d ? new Date(d + 'T00:00').toLocaleDateString('fr-FR') : '?';
    p.appendChild(el('div', {class: 'row'}, [el('b', {text: 'Complétude : ' + CTRL.score + ' %'})]));
    p.appendChild(el('div', {class: 'bar', style: 'margin:6px 0 14px'}, [el('i', {style: 'width:' + CTRL.score + '%'})]));
    const ul = el('ul');
    ul.appendChild(el('li', {}, [el('b', {text: 'Risque global : '}), el('span', {text: CTRL.risk, style: 'color:' + CTRL.risk_color + ';font-weight:800'}), ' — ' + CTRL.risk_why]));
    ul.appendChild(el('li', {}, [el('b', {text: "Fenêtre d'exposition : "}), CTRL.exposure ? fmt(CTRL.exposure[0]) + ' → ' + fmt(CTRL.exposure[1]) + ' (J-' + CTRL.incubation[1] + ' → J-' + CTRL.incubation[0] + ')' : 'renseigner le début des symptômes (onglet Clinique).']));
    if (CTRL.contagious) ul.appendChild(el('li', {}, [el('b', {text: 'Période contagieuse : '}), fmt(CTRL.contagious[0]) + ' → ' + fmt(CTRL.contagious[1])]));
    ul.appendChild(el('li', {}, [el('b', {text: 'Contacts : '}), CTRL.contacts.phrase + (CTRL.contacts.pct !== null ? ' Suivi : ' + CTRL.contacts.suivis + '/' + CTRL.contacts.total + ' (' + Math.round(CTRL.contacts.pct) + ' %).' : '')]));
    if (CTRL.lab_delay !== null) ul.appendChild(el('li', {}, [el('b', {text: 'Délai laboratoire : '}), CTRL.lab_delay + ' h (seuil ' + CTRL.lab_threshold + ' h)']));
    p.appendChild(ul);
    p.appendChild(el('h2', {text: 'Contrôles de cohérence'}));
    if (CTRL.issues.length) p.appendChild(el('ul', {class: 'issues'}, CTRL.issues.map(i => el('li', {}, [el('span', {class: 'lvl-' + i.level, text: i.level.toUpperCase()}), ' — ' + i.msg]))));
    else p.appendChild(el('p', {style: 'color:var(--ok)', text: 'Aucune incohérence détectée.'}));
    p.appendChild(el('h2', {text: 'Informations critiques manquantes'}));
    if (CTRL.missing.length) p.appendChild(el('ul', {}, CTRL.missing.map(m => el('li', {text: m}))));
    else p.appendChild(el('p', {style: 'color:var(--ok)', text: 'Fiche complète.'}));
  }
  function renderSuggestions() {
    const box = $('#suggestions'); if (!CTRL) return; box.innerHTML = '';
    const have = new Set(C.actions.map(a => a.texte));
    const list = CTRL.suggestions.filter(s => !have.has(s.texte));
    if (!list.length) { box.appendChild(el('p', {class: 'muted', text: 'Aucune suggestion en attente.'})); }
    list.forEach(s => {
      box.appendChild(el('div', {class: 'sugg' + (s.priorite === 'Urgent' ? ' urgent' : ''), title: s.raison}, [
        el('span', {}, [el('b', {text: '[' + s.priorite + '] '}), s.texte]),
        el('span', {class: 'row'}, [
          el('button', {class: 'btn small', text: 'Ajouter', on: {click: () => { C.actions.push(Object.assign(blankRow('actions'), {texte: s.texte, priorite: s.priorite, auto: true, id: Math.random().toString(16).slice(2, 12)})); renderTable('actions'); renderSuggestions(); changed(); }}}),
          el('button', {class: 'btn small', text: 'Ignorer', on: {click: () => { C.suggestions_rejetees.push(s.texte); CTRL.suggestions = CTRL.suggestions.filter(x => x !== s); renderSuggestions(); changed(); }}})])]));
    });
    if (C.suggestions_rejetees.length) box.appendChild(el('button', {class: 'btn small', text: 'Rétablir les suggestions ignorées', on: {click: () => { C.suggestions_rejetees = []; changed(); }}}));
  }

  // ---------------------------------------------------------------- aperçu
  function refreshPreview() {
    const f = $('#pv');
    f.src = '/cas/' + ID + '/apercu/' + visual + '?t=' + Date.now();
    updateDownloads();
  }
  function scaleFrame() {
    const fr = $('#frame'); const s = fr.clientWidth / 1280;
    $('#pv').style.transform = 'scale(' + s + ')';
  }
  function updateDownloads() {
    $$('#dl a').forEach(a => {
      const fmt = a.dataset.fmt;
      a.href = '/cas/' + ID + '/telecharger/' + fmt + '?visuel=' + (a.dataset.any ? 'mapping' : visual);
      a.style.display = a.dataset.only && a.dataset.only !== visual ? 'none' : '';
    });
  }

  // ----------------------------------------------------------------- init
  async function init() {
    try {
      const [schema, pyr, data] = await Promise.all([api('/api/schema'), api('/api/pyramide'), api('/api/cas/' + ID)]);
      S = schema; PYR = pyr; C = data.case; CTRL = data.controls;
    } catch (e) { setStatus('Chargement impossible : ' + e.message, true); return; }
    renderIdentity(); renderClinic();
    ['events', 'places', 'contacts', 'ipc', 'labs', 'actions'].forEach(renderTable);
    renderControls(); renderSuggestions(); updateTitle();

    $$('#tabs button').forEach(b => b.addEventListener('click', () => {
      $$('#tabs button').forEach(x => x.classList.toggle('on', x === b));
      $$('.pane').forEach(p => p.classList.toggle('on', p.id === 'p-' + b.dataset.p));
    }));
    $$('#vtabs button').forEach(b => b.addEventListener('click', () => {
      $$('#vtabs button').forEach(x => x.classList.toggle('on', x === b));
      visual = b.dataset.v; refreshPreview();
    }));
    $$('[data-add]').forEach(b => b.addEventListener('click', () => {
      const t = b.dataset.add; const r = blankRow(t); r.id = Math.random().toString(16).slice(2, 12);
      C[t].push(r); renderTable(t); changed();
      const last = $('#t-' + t + ' tbody tr:last-child input, #t-' + t + ' tbody tr:last-child select'); if (last) last.focus();
    }));
    $('#sortEvents').addEventListener('click', () => {
      C.events.sort((a, b) => (a.date_debut || '9999') .localeCompare(b.date_debut || '9999') || (a.heure || '').localeCompare(b.heure || ''));
      renderTable('events'); changed();
    });
    $('#fillGaps').addEventListener('click', async () => {
      await flush();
      const j = await api('/api/cas/' + ID + '/trous', {method: 'POST', body: '{}'});
      if (!j.events.length) { toast('Aucune période non couverte détectée.'); return; }
      C.events = C.events.concat(j.events); renderTable('events'); changed(); toast(j.events.length + ' période(s) à documenter ajoutée(s).');
    });
    $('#prefill').addEventListener('click', async () => {
      await flush();
      const j = await api('/api/cas/' + ID + '/places-depuis-chronologie', {method: 'POST', body: '{}'});
      if (!j.places.length) { toast('Tous les lieux de la chronologie sont déjà listés.'); return; }
      C.places = C.places.concat(j.places); renderTable('places'); changed(); toast(j.places.length + ' lieu(x) ajouté(s).');
    });
    $('#saveVersion').addEventListener('click', async () => {
      const com = prompt('Commentaire de version (facultatif) :', '');
      if (com === null) return;
      clearTimeout(timer); await save(true, com); toast('Version enregistrée dans l\'historique.');
    });
    $$('#dl a').forEach(a => a.addEventListener('click', async ev => {
      ev.preventDefault();
      await flush();
      const slow = ['png', 'png4k', 'pdf', 'pdfa4', 'rapport-pdf', 'rapport-pptx'].includes(a.dataset.fmt);
      if (slow) toast('Génération du fichier… (quelques secondes)', 6000);
      window.location.href = a.href;
    }));
    new ResizeObserver(scaleFrame).observe($('#frame'));
    scaleFrame(); refreshPreview();
  }
  document.addEventListener('DOMContentLoaded', init);
})();
