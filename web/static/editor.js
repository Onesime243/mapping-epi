/* Mapping Épi : éditeur web (sans dépendance externe). */
(function () {
  'use strict';
  const ID = window.CASE_ID;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  // langue : textes de la fiche traduits par window.I18N (vide en français) ; les choix restent enregistrés en français
  const T = s => (window.I18N && window.I18N[s]) || s;
  const TF = (s, o) => T(s).replace(/\{(\w+)\}/g, (m, k) => (o && k in o ? o[k] : m));
  const EN = !!(window.I18N && Object.keys(window.I18N).length);
  const LOC = EN ? 'en-GB' : 'fr-FR';
  const SEP = EN ? ': ' : ' : ', PCT = EN ? '%' : ' %';     // « : » et « % » : espace avant en français seulement
  let S = null, PYR = {}, C = null, CTRL = null, dirty = false, saving = null, timer = null, visual = 'mapping';

  // ------------------------------------------------------------------ réseau
  async function api(url, opts) {
    opts = opts || {};
    opts.headers = Object.assign({'X-CSRF': window.CSRF, 'Content-Type': 'application/json'}, opts.headers || {});
    const r = await fetch(url, opts);
    if (r.status === 401) { location.href = '/connexion?next=' + encodeURIComponent(location.pathname); throw new Error('session'); }
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || (T('Erreur') + ' ' + r.status));
    return j;
  }
  function toast(msg, ms) {
    const t = $('#toast'); t.textContent = msg; t.style.display = 'block';
    clearTimeout(t._h); t._h = setTimeout(() => { t.style.display = 'none'; }, ms || 2600);
  }
  const RO = !!window.READONLY;      // lecture seule (fiche d'un autre compte, niveau provincial / national)
  // état de sauvegarde toujours visible : ok (vert), pending (orange), saving (bleu), err (rouge)
  let lastSaved = null;
  function setStatus(txt, kind) {
    const s = $('#status'); if (!s) return;
    const k = kind === true ? 'err' : (kind || 'ok');
    const ic = {ok: '✓ ', pending: '● ', saving: '↻ ', err: '⚠ '}[k] || '';
    s.textContent = ic + txt; s.className = 'status ' + k;
  }
  function depuis(t) {
    const sec = Math.round((Date.now() - t.getTime()) / 1000);
    if (sec < 10) return T("à l'instant");
    if (sec < 60) return TF('il y a {n} s', {n: sec});
    const m = Math.round(sec / 60);
    return m < 60 ? TF('il y a {n} min', {n: m}) : TF('à {heure}', {heure: t.toLocaleTimeString(LOC, {hour: '2-digit', minute: '2-digit'})});
  }
  setInterval(() => {
    const s = $('#status');
    if (s && lastSaved && s.classList.contains('ok') && !dirty) setStatus(T('Enregistré') + ' ' + depuis(lastSaved), 'ok');
  }, 15000);

  function changed() {
    if (RO) return;
    markRequired(); renderObligatoires(); renderEtapes();
    dirty = true; setStatus(T('Modifications non enregistrées…'), 'pending');
    clearTimeout(timer); timer = setTimeout(() => save(false), 900);
  }
  async function save(version, comment) {
    if (saving) await saving.catch(() => {});
    if (!dirty && !version) return;
    dirty = false; setStatus(T('Enregistrement…'), 'saving');
    const q = version ? ('?version=1&commentaire=' + encodeURIComponent(comment || '')) : '';
    saving = api('/api/cas/' + ID + q, {method: 'PUT', body: JSON.stringify(C)}).then(j => {
      CTRL = j.controls; updateComputed(); renderControls(); renderSuggestions(); refreshPreview();
      const t = new Date(j.saved_at);
      OBLIG = j.obligatoires || []; renderObligatoires();
      if (j.brouillon) {
        setStatus(TF('Brouillon : {n} champ(s) obligatoire(s) manquant(s)', {n: OBLIG.length}), 'pending');
        if (version) toast(j.message, 6000);
      } else {
        lastSaved = isNaN(t.getTime()) ? new Date() : t;
        setStatus(T(version ? 'Version enregistrée' : 'Enregistré') + ' ' + depuis(lastSaved), 'ok');
      }
      updateTitle();
    }).catch(e => {
      dirty = true;
      setStatus(navigator.onLine === false ? T('Hors connexion : non enregistré, nouvel essai automatique')
                                           : T("Échec de l'enregistrement : ") + e.message, 'err');
      clearTimeout(timer); timer = setTimeout(() => save(false), 15000);
    });
    return saving;
  }
  async function flush() { clearTimeout(timer); if (dirty) await save(false); else if (saving) await saving.catch(() => {}); }
  window.addEventListener('beforeunload', e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });

  function updateTitle() {
    const rang = (C.code_cas || '').trim() || TF('Cas {n}', {n: C.rang || ''}).trim();
    $('#caseTitle').textContent = rang + ' – ' + T(C.maladie) + ' – ' + TF('ZS {zs}', {zs: C.zs || '?'}) + ' (' + (C.aire_sante || '?') + ')';
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
    vals.forEach(v => sel.appendChild(el('option', {value: v, text: v === '' ? T(emptyLabel || 'Choisir…') : T(v)})));
    sel.value = value || '';
  }
  function datalist(id, items) {
    let d = document.getElementById(id);
    if (!d) { d = el('datalist', {id}); document.body.appendChild(d); }
    d.innerHTML = '';
    // la valeur proposée reste en français (enregistrée) ; la traduction s'affiche à côté (label)
    [...new Set(items.filter(Boolean))].sort((a, b) => a.localeCompare(b, 'fr')).forEach(v => d.appendChild(el('option', {value: v, label: T(v) !== v ? T(v) : null})));
    return id;
  }
  const minDate = () => S.annee_min + '-01-01';
  const norm = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/-/g, ' ').trim();
  function findKey(obj, name) { const n = norm(name); return Object.keys(obj || {}).find(k => norm(k) === n); }

  // -------------------------------------------------------------- identité
  function field(label, input, wide) {
    return el('div', {style: wide ? 'grid-column: 1 / -1' : null}, [el('label', {class: 'f', text: T(label)}), input]);
  }
  function bindInput(inp, key, kind) {
    inp.dataset.k = key;
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
    p.appendChild(el('p', {class: 'hint', text: T("Champs marqués * : indispensables au mapping. Une information inconnue reste vide : elle s'affichera « ? ».")}));
    const g = el('div', {class: 'grid'});
    const inp = (key, type, extra) => { const i = el('input', Object.assign({type: type || 'text', value: C[key] ?? ''}, extra || {})); bindInput(i, key, type === 'number' ? 'int' : type === 'date' ? 'date' : 'text'); return i; };
    const sel = (key, list, emptyLabel) => { const s = el('select'); options(s, list, C[key] ?? '', emptyLabel); bindInput(s, key, 'select'); return s; };

    g.appendChild(field('ID du cas * (alphanumérique)', inp('code_cas', 'text', {placeholder: T('ex.') + ' RDC-HUE-WAM-26-001', maxlength: 40})));
    const mal = el('input', {value: C.maladie || '', list: datalist('dl-mal', S.choices.diseases)}); bindInput(mal, 'maladie');
    g.appendChild(field('Maladie *', mal));
    g.appendChild(field('Statut', sel('statut', S.choices.status)));
    // Lien épidémiologique : le cas était-il déjà un contact connu (listé) ?
    const cbox = el('div', {class: 'seg'});
    (S.choices.contact_status || ['Inconnu', 'Contact connu', 'Contact connu suivi', 'Non contact']).forEach(v => {
      const b = el('button', {type: 'button', class: 'seg-b' + (v === 'Inconnu' ? ' unk' : '') + ((C.contact_connu || 'Inconnu') === v ? ' on' : ''), text: T(v)});
      b.addEventListener('click', () => {
        C.contact_connu = v; cbox.querySelectorAll('.seg-b').forEach(x => x.classList.toggle('on', x === b)); changed();
      });
      cbox.appendChild(b);
    });
    g.appendChild(field('Contact connu ou non contact ? *', cbox, true));
    // si le cas était un contact connu, l'ID du cas source est obligatoire
    const src = inp('id_cas_source', 'text', {placeholder: T('À compléter : ID du cas dont il est le contact'), maxlength: 40});
    const srcField = field('ID du cas source (contact de…) *', src);
    const majSrc = () => {
      const req = ['Contact connu', 'Contact connu suivi'].includes(C.contact_connu || '');
      srcField.style.display = req ? '' : 'none';
      src.classList.toggle('req-missing', req && !src.value.trim());
    };
    const dcs = inp('date_contact_source', 'date', {min: minDate()});
    const dcsField = field('Date du dernier contact avec le cas source *', dcs);
    const srcInfo = el('div', {class: 'hint', id: 'srcInfo', style: 'grid-column: 1 / -1; margin:0'});
    const majSrc2 = () => {
      const req = ['Contact connu', 'Contact connu suivi'].includes(C.contact_connu || '');
      dcsField.style.display = req ? '' : 'none'; srcInfo.style.display = req ? '' : 'none';
      dcs.classList.toggle('req-missing', req && !dcs.value);
    };
    src.addEventListener('input', majSrc);
    cbox.addEventListener('click', () => { majSrc(); majSrc2(); });
    dcs.addEventListener('input', majSrc2);
    g.appendChild(srcField); majSrc();
    g.appendChild(dcsField); g.appendChild(srcInfo); majSrc2();
    g.appendChild(field('Sexe *', sel('sexe', S.choices.sexes)));
    g.appendChild(field('Âge *', inp('age', 'number', {min: 0, max: 120, placeholder: T('vide si inconnu')})));
    g.appendChild(field('Unité', sel('age_unite', ['ans', 'mois'])));
    g.appendChild(field('Profession', inp('profession')));
    const ouiNon = S.choices.oui_non || ['Inconnu', 'Oui', 'Non'];
    const ppl = req(sel('agent_sante', ouiNon), 'agent_sante');
    const pplS = inp('agent_sante_structure', 'text', {placeholder: T('ex. Infirmier, CS Nzala')});
    const pplF = field("Catégorie et structure de l'agent de santé", pplS);
    const vac = req(sel('vaccine', ouiNon), 'vaccine');
    const vacD = inp('date_vaccination', 'date', {min: minDate()});
    const vacF = field('Date de vaccination', vacD);
    const majPV = () => { pplF.style.display = C.agent_sante === 'Oui' ? '' : 'none'; vacF.style.display = C.vaccine === 'Oui' ? '' : 'none'; };
    ppl.addEventListener('change', majPV); vac.addEventListener('change', majPV);
    g.appendChild(field('Agent de santé / prestataire (PPL) *', ppl)); g.appendChild(pplF);
    g.appendChild(field('Vacciné *', vac)); g.appendChild(vacF); majPV();
    g.appendChild(field("Début de la vaccination de l'anneau", inp('date_debut_anneau', 'date', {min: minDate()})));

    // Province → ZS → AS (pyramide sanitaire RDC)
    const prov = el('select'), zs = el('select'), as = el('input', {placeholder: T('choisir ou saisir…')});
    const fillZs = () => {
      const pk = findKey(PYR, prov.value);
      const zones = pk ? Object.keys(PYR[pk]) : [];
      options(zs, [''].concat(zones), C.zs || '', 'Choisir la zone de santé…');
      fillAs();
    };
    const fillAs = () => {
      const pk = findKey(PYR, prov.value), zk = pk ? findKey(PYR[pk], zs.value) : null;
      as.setAttribute('list', datalist('dl-as', zk ? PYR[pk][zk] : []));
    };
    options(prov, [''].concat(Object.keys(PYR)), C.province || '', 'Choisir la province…');
    prov.addEventListener('change', () => { C.province = prov.value; C.zs = ''; C.aire_sante = ''; as.value = ''; fillZs(); changed(); });
    zs.addEventListener('change', () => { C.zs = zs.value; C.aire_sante = ''; as.value = ''; fillAs(); changed(); });
    as.value = C.aire_sante || '';
    as.addEventListener('input', () => { C.aire_sante = as.value; changed(); });
    fillZs();
    g.appendChild(field('Province *', prov));
    g.appendChild(field('Zone de santé (ZS) *', zs));
    g.appendChild(field('Aire de santé (AS) *', as));
    g.appendChild(field('Village / quartier', inp('village')));
    const lat = el('input', {type: 'number', step: 'any', value: C.lat ?? '', placeholder: T('ex.') + ' 2.63'}); bindInput(lat, 'lat', 'float');
    const lon = el('input', {type: 'number', step: 'any', value: C.lon ?? '', placeholder: T('ex.') + ' 24.38'}); bindInput(lon, 'lon', 'float');
    g.appendChild(field('Latitude', lat));
    g.appendChild(field('Longitude', lon));
    g.appendChild(field('Date de notification *', req(inp('date_notification', 'date', {min: minDate()}), 'date_notification')));
    g.appendChild(field('Date de confirmation *', inp('date_confirmation', 'date', {min: minDate()})));
    g.appendChild(field('Séquençage (clade, lignée)', inp('sequencage', 'text', {placeholder: T('ex. lignée 2026-A, lié au cas …')})));
    g.appendChild(field('État du cas *', req(sel('issue', S.choices.issues), 'issue')));
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
    [['debut_symptomes', 'Début des symptômes rapporté par l\'équipe *'], ['debut_phase_humide', 'Début phase humide (vide = auto)'],
     ['date_deces', 'Date de décès']].forEach(([k, lbl]) => {
      const inp = el('input', {type: 'date', min: minDate(), value: C[k] || ''}); bindInput(inp, k, 'date');
      g.appendChild(field(lbl, inp));
    });
    const pd = el('select'); options(pd, S.choices.phase_dds || ['Inconnue'], C.phase_dds || 'Inconnue'); bindInput(pd, 'phase_dds', 'select');
    req(pd, 'phase_dds');
    g.appendChild(field('Phase des premiers signes rapportés *', pd));
    p.appendChild(g);
    p.appendChild(el('p', {class: 'hint', text: T("À quelle phase se trouvait le cas à la date rapportée ? Phase sèche (fièvre, fatigue, céphalées, douleurs) : J0 = date − 3 j. Phase humide (vomissements, diarrhée, yeux rouges) : J0 = date − 7 j. Phase critique (saignements, confusion, choc) : J0 = date − 16 j. Le J0 retenu sert au point d'infection (J-21 → J-2) et aux phases. Pour un contact connu, l'exposition vient du cas source (onglet Identité).")}));
    const j0i = el('p', {class: 'hint', id: 'j0Info'}); p.appendChild(j0i);
    p.appendChild(el('h2', {text: T('Symptômes')}));
    const toggle = (s, on) => {
      C.symptomes = on ? C.symptomes.filter(x => x !== s).concat([s]) : C.symptomes.filter(x => x !== s); changed();
    };
    const groups = S.choices.symptom_groups || [['Symptômes', S.choices.symptoms]];
    const known = [].concat(...groups.map(g => g[1]));
    const custom = C.symptomes.filter(s => !known.includes(s));
    groups.forEach(([gname, items]) => {
      p.appendChild(el('h3', {class: 'symgroup', text: T(gname)}));
      const box = el('div', {class: 'symptoms'});
      items.forEach(s => {
        const cb = el('input', {type: 'checkbox'}); cb.checked = C.symptomes.includes(s);
        cb.addEventListener('change', () => toggle(s, cb.checked));
        box.appendChild(el('label', {}, [cb, T(s) + (S.choices.hemorrhagic.includes(s) ? ' 🩸' : '')]));
      });
      p.appendChild(box);
    });
    p.appendChild(el('h3', {class: 'symgroup', text: T('Symptômes ajoutés')}));
    const cbox = el('div', {class: 'symptoms'});
    const addCustom = (s, checked) => {
      const cb = el('input', {type: 'checkbox'}); cb.checked = checked;
      cb.addEventListener('change', () => toggle(s, cb.checked));
      cbox.appendChild(el('label', {}, [cb, s]));
    };
    custom.forEach(s => addCustom(s, true));
    p.appendChild(cbox);
    const nw = el('input', {placeholder: T('Symptôme absent de la liste (ex. douleur thoracique)')});
    const add = el('button', {type: 'button', class: 'btn small', text: T('+ Ajouter le symptôme')});
    const doAdd = () => {
      let s = nw.value.trim(); if (!s) return;
      s = s.charAt(0).toUpperCase() + s.slice(1);
      if (!C.symptomes.includes(s)) { C.symptomes = C.symptomes.concat([s]); if (!known.includes(s)) addCustom(s, true); changed(); }
      nw.value = '';
    };
    add.addEventListener('click', doAdd);
    nw.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); doAdd(); } });
    p.appendChild(el('div', {class: 'row', style: 'margin-top:8px'}, [nw, add]));
    const other = el('input', {value: C.symptomes_autres || '', placeholder: T('Autres symptômes (texte libre)'), style: 'margin-top:12px'});
    bindInput(other, 'symptomes_autres');
    p.appendChild(other);
  }

  // --------------------------------------------------------------- tableaux
  // ---------------------------------------------------------- lieux : propositions, harmonisation, nom proche
  const SIGLES_LIEUX = new Set(['HGR', 'CS', 'CM', 'PS', 'CSR', 'CSDT', 'CTE', 'CTI', 'CH', 'CHU', 'HGRB', 'HGRK', 'CBCA',
    'CEBCE', 'CEPAC', 'CBCE', 'CECA', 'ZS', 'AS', 'CRS', 'PMI', 'BCZ', 'MSF', 'ALIMA', 'IRC', 'ONG', 'RN', 'RN2', 'RN4', 'EP',
    'ITM', 'IT', 'DPS', 'UPC', 'UNIKIN', 'MONUSCO', 'FARDC', 'PNC', 'CTA', 'ECC', '8E', '55E']);
  const PETITS_MOTS = new Set(['de', 'du', 'des', 'la', 'le', 'les', 'et', 'à', 'a', 'au', 'aux', 'en', 'sur', 'sous', 'pour', 'par']);
  const lettres = m => m.replace(/[^A-Za-zÀ-ÿ0-9]/g, '');
  function harmoniser(nom) {          // même règle que core/lieux.py : harmoniser()
    const mots = (nom || '').trim().split(/\s+/).filter(Boolean);
    const reste = mots.filter(m => !SIGLES_LIEUX.has(lettres(m).toUpperCase())).join(' ');
    const uniforme = reste && (reste === reste.toLowerCase() || reste === reste.toUpperCase());
    return mots.map((m, i) => {
      if (SIGLES_LIEUX.has(lettres(m).toUpperCase())) return m.toUpperCase();
      if (i > 0 && PETITS_MOTS.has(m.toLowerCase())) return m.toLowerCase();
      if (/\d/.test(m)) return m;
      if (!uniforme) return i === 0 ? m.charAt(0).toUpperCase() + m.slice(1) : m;
      let pre = '';
      if (m.length > 2 && "'’".includes(m[1]) && 'dl'.includes(m[0].toLowerCase())) { pre = m.slice(0, 2).toLowerCase(); m = m.slice(2); }
      return pre + m.charAt(0).toUpperCase() + m.slice(1).toLowerCase();
    }).join(' ');
  }
  const cleLieu = s => norm(s).replace(/\([^)]*\)/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim();
  function distance(a, b) {           // Levenshtein
    const d = Array.from({length: a.length + 1}, (_, i) => [i]);
    for (let j = 1; j <= b.length; j++) d[0][j] = j;
    for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    return d[a.length][b.length];
  }
  let ZONE = {zs: null, lieux: []};
  async function chargerZone() {
    const zs = C.zs || '';
    if (ZONE.zs === zs) return;
    ZONE = {zs, lieux: []};
    if (!zs || !ID) return;
    try {
      const j = await api('/api/cas/' + ID + '/lieux?zs=' + encodeURIComponent(zs) + '&province=' + encodeURIComponent(C.province || ''));
      if (ZONE.zs === zs) ZONE.lieux = j.lieux || [];
    } catch (e) { /* hors ligne ou application de bureau : seulement les lieux de la fiche */ }
  }
  function lieuxConnus() {             // [{nom, n, fiche}] : ceux de la fiche d'abord, puis ceux de la zone
    const vus = new Map();
    placeNames().forEach(n => { const k = cleLieu(n); if (k && !vus.has(k)) vus.set(k, {nom: harmoniser(n), n: 0, fiche: true}); });
    ZONE.lieux.forEach(l => { const k = cleLieu(l.nom); if (k && !vus.has(k)) vus.set(k, {nom: l.nom, n: l.n, fiche: false}); });
    return [...vus.values()];
  }
  function remplirListeLieux() {
    let d = document.getElementById('dl-places');
    if (!d) { d = el('datalist', {id: 'dl-places'}); document.body.appendChild(d); }
    d.innerHTML = '';
    lieuxConnus().forEach(l => d.appendChild(el('option', {value: l.nom,
      label: l.fiche ? T('dans cette fiche') : (pl(l.n, 'fiche') + ' · ' + TF('ZS {zs}', {zs: ZONE.zs || '?'}))})));
  }
  function attachLieu(inp, set) {
    inp.addEventListener('focus', async () => { remplirListeLieux(); await chargerZone(); remplirListeLieux(); });
    inp.addEventListener('change', () => {
      const td = inp.parentNode;
      const ancien = td && td.querySelector('.lieu-hint'); if (ancien) ancien.parentNode.removeChild(ancien);
      const brut = inp.value.trim();
      if (!brut) return;
      const h = harmoniser(brut);
      if (h !== inp.value) { inp.value = h; set(h); if (h !== brut) toast(TF('Écriture harmonisée : « {avant} » → « {apres} »', {avant: brut, apres: h}), 3500); }
      const k = cleLieu(h);
      // déjà connu : ailleurs dans la fiche (ce champ compte une fois) ou dans les fiches de la zone
      const dansFiche = placeNames().filter(n => cleLieu(n) === k).length;
      if (dansFiche > 1 || ZONE.lieux.some(l => cleLieu(l.nom) === k)) return;
      const connus = lieuxConnus().filter(l => cleLieu(l.nom) !== k);
      let best = null;
      connus.forEach(l => {
        const kl = cleLieu(l.nom);
        if (kl.length < 5 || k.length < 5) return;
        const dmax = Math.max(k.length, kl.length) >= 9 ? 2 : 1;
        const dd = distance(k, kl);
        if (dd > 0 && dd <= dmax && (!best || dd < best.d || (dd === best.d && l.n > best.l.n))) best = {l, d: dd};
      });
      if (!best || !td) return;
      const b = best.l;
      const hint = el('div', {class: 'lieu-hint'}, [
        el('span', {text: T('Nom proche : ')}), el('b', {text: b.nom}),
        el('span', {text: b.fiche ? ' (' + T('dans cette fiche') + ')' : ' (' + pl(b.n, 'fiche') + ')'}),
        el('button', {type: 'button', class: 'btn small primary', text: T('Remplacer'), on: {click: () => {
          inp.value = b.nom; set(b.nom); hint.parentNode.removeChild(hint); }}}),
        el('button', {type: 'button', class: 'btn small', text: T('Garder'), on: {click: () => hint.parentNode.removeChild(hint)}})]);
      td.appendChild(hint);
    });
  }

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
        inp = el('select', {style: 'min-width:' + w}); options(inp, c.choices, v || '', c.key === 'risque' ? 'Auto' : 'Choisir…');
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
        if (c.key === 'personnes') {   // obligatoire : rouge tant que vide
          inp.placeholder = T('À compléter');
          // étapes sans personnes exposées (investigation, laboratoire, riposte) : pas à compléter (même règle que le mapping)
          const mark = () => inp.classList.toggle('req-missing', !inp.value.trim() && !SANS_PERSONNES.has(row.type));
          inp.addEventListener('input', mark); mark();
        }
        if (c.complete) attachLieu(inp, set);
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
        op('↑', T('Monter'), () => move(table, i, -1)), op('↓', T('Descendre'), () => move(table, i, 1)),
        op('⧉', T('Dupliquer'), () => { const cp = JSON.parse(JSON.stringify(row)); cp.id = Math.random().toString(16).slice(2, 12); C[table].splice(i + 1, 0, cp); renderTable(table); changed(); }),
        op('✕', T('Supprimer'), () => { C[table].splice(i, 1); renderTable(table); changed(); })]));
      body.appendChild(tr);
    });
    if (!C[table].length) body.appendChild(el('tr', {}, [el('td', {colspan: cols.length + 1, class: 'muted', text: T('Aucune ligne. Cliquez sur « Ajouter ».'), style: 'padding:14px'})]));
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
        td.textContent = T(comp.lvl) + (C.events[+i] && !C.events[+i].risque ? ' ✓' : '');
        td.style.color = comp.color; td.title = comp.why;
      } else td.textContent = table === 'places' ? T(comp) : comp;
    });
  }

  // ---------------------------------------------------- contrôles / actions
  // champs indispensables vides : case rouge (marquée par req) + bandeau « À compléter » en haut de la fiche
  function req(input, key) { input.dataset.req = key; return input; }
  function markRequired() {
    $$('[data-req]').forEach(x => {
      const v = C[x.dataset.req];
      x.classList.toggle('req-missing', v === null || v === undefined || v === '' || v === 'Inconnu' || v === 'Inconnue');
    });
  }
  // champs obligatoires : sans eux, la fiche reste en brouillon (enregistrement refusé par le serveur)
  let OBLIG = null;
  function obligManquants() {
    return (S.obligatoires || []).filter(o => { const v = C[o.key]; return v === null || v === undefined || String(v).trim() === '' || v === 'Inconnu' || v === 'Inconnue'; });
  }
  function renderObligatoires() {
    const box = $('#obligatoires'); if (!box || RO) return;
    const m = obligManquants();
    $$('[data-k]').forEach(x => x.classList.toggle('obl-missing', m.some(o => o.key === x.dataset.k)));
    box.hidden = !m.length;
    if (!m.length) return;
    if (!dirty && !saving) setStatus(T('Brouillon : non enregistré'), 'pending');
    box.innerHTML = '';
    const noms = m.map(o => o.label.replace(/ \(.*\)$/, '').toLowerCase().replace(/^id /, 'ID '));
    const liste = noms.length > 1 ? noms.slice(0, -1).join(', ') + ' ' + T('et') + ' ' + noms[noms.length - 1] : noms[0];
    box.appendChild(el('b', {text: T('Pas encore enregistrée : ')}));
    box.appendChild(document.createTextNode(TF('il manque {liste}.', {liste})));
  }

  function renderMissing() {
    const box = $('#missing'); if (!box || !CTRL) return;
    box.innerHTML = '';
    box.hidden = !CTRL.missing.length || RO;
    if (box.hidden) return;
    // éléments utiles au mapping complet : discret et replié (seuls les champs obligatoires sont en rouge)
    box.classList.add('neutre');
    const d = el('details');
    d.appendChild(el('summary', {text: TF('{n} élément(s) à compléter pour un mapping complet', {n: CTRL.missing.length})}));
    d.appendChild(el('div', {text: CTRL.missing.join(' • '), style: 'margin-top:6px'}));
    box.appendChild(d);
  }
  function renderSourceInfo() {
    const s = $('#srcInfo'), j = $('#j0Info'), fmt = d => d ? new Date(d + 'T00:00').toLocaleDateString('fr-FR') : '?';
    if (s && CTRL) {
      const x = CTRL.source;
      s.textContent = x ? (TF('Cas source trouvé : {code} (ZS {zs}, état {etat}) : J0 {j0}', {code: x.code, zs: x.zs || '?', etat: T(x.etat), j0: fmt(x.j0)}) +
        (x.contagieux ? TF(', contagieux du {debut} au {fin}', {debut: fmt(x.contagieux[0]), fin: fmt(x.contagieux[1])}) : '') +
        T('. Sans date de dernier contact, l\'exposition du mapping est cette période.'))
        : (C.id_cas_source ? T('Cas source non trouvé dans l\'outil : renseignez la date du dernier contact.') : '');
    }
    if (j && CTRL) {
      j.textContent = CTRL.j0_retenu ? (TF('J0 retenu : {date} (date rapportée − {n} j)', {date: fmt(CTRL.j0_retenu), n: CTRL.recul}) +
        (CTRL.notif_delai !== null ? TF(' • notification {n} j après le début des symptômes rapporté', {n: CTRL.notif_delai}) : '')) : '';
    }
  }

  function renderControls() {
    markRequired(); renderMissing(); renderSourceInfo(); renderObligatoires();
    const p = $('#p-controles'); if (!CTRL) return; p.innerHTML = '';
    const fmt = d => d ? new Date(d + 'T00:00').toLocaleDateString('fr-FR') : '?';
    p.appendChild(el('div', {class: 'row'}, [el('b', {text: T('Complétude : ') + CTRL.score + PCT})]));
    p.appendChild(el('div', {class: 'bar', style: 'margin:6px 0 14px'}, [el('i', {style: 'width:' + CTRL.score + '%'})]));
    const ul = el('ul');
    ul.appendChild(el('li', {}, [el('b', {text: T('Risque global : ')}), el('span', {text: T(CTRL.risk), style: 'color:' + CTRL.risk_color + ';font-weight:800'}), SEP + CTRL.risk_why]));
    ul.appendChild(el('li', {}, [el('b', {text: T("Fenêtre d'exposition : ")}), CTRL.exposure ? fmt(CTRL.exposure[0]) + ' → ' + fmt(CTRL.exposure[1]) + ' (' + TF('J-{max} → J-{min}', {max: CTRL.incubation[1], min: CTRL.incubation[0]}) + ')' : T('renseigner le début des symptômes (onglet Clinique).')]));
    if (CTRL.contagious) ul.appendChild(el('li', {}, [el('b', {text: T('Période contagieuse : ')}), fmt(CTRL.contagious[0]) + ' → ' + fmt(CTRL.contagious[1])]));
    ul.appendChild(el('li', {}, [el('b', {text: T('Contacts : ')}), CTRL.contacts.phrase + (CTRL.contacts.pct !== null ? T(' Suivi : ') + CTRL.contacts.suivis + '/' + CTRL.contacts.total + ' (' + Math.round(CTRL.contacts.pct) + PCT + ').' : '')]));
    if (CTRL.lab_delay !== null) ul.appendChild(el('li', {}, [el('b', {text: T('Délai laboratoire : ')}), TF('{n} h (seuil {seuil} h)', {n: CTRL.lab_delay, seuil: CTRL.lab_threshold})]));
    p.appendChild(ul);
    p.appendChild(el('h2', {text: T('Contrôles de cohérence')}));
    if (CTRL.issues.length) p.appendChild(el('ul', {class: 'issues'}, CTRL.issues.map(i => el('li', {}, [el('span', {class: 'lvl-' + i.level, text: T(i.level).toUpperCase()}), SEP + i.msg]))));
    else p.appendChild(el('p', {style: 'color:var(--ok)', text: T('Aucune incohérence détectée.')}));
    p.appendChild(el('h2', {text: T('Informations critiques manquantes')}));
    if (CTRL.missing.length) p.appendChild(el('ul', {}, CTRL.missing.map(m => el('li', {text: m}))));
    else p.appendChild(el('p', {style: 'color:var(--ok)', text: T('Fiche complète.')}));
    renderEtapes();
  }

  // ------------------------------------------------------------- fiche par étapes
  const SANS_PERSONNES = new Set(['Investigation', 'Laboratoire', 'Riposte']);     // config/theme.py SANS_PERSONNES
  const ETAPES = [['identite', '1. Identité'], ['clinique', '2. Clinique'], ['events', '3. Chronologie'], ['places', '4. Lieux'],
    ['contacts', '5. Contacts'], ['ipc', '6. PCI'], ['labs', '7. Laboratoire'], ['actions', '8. Actions']].map(([k, v]) => [k, T(v)]);
  // pluriel : le mot (singulier ou pluriel français) est traduit tel quel
  const pl = (n, s, p) => n + ' ' + T(n > 1 ? (p || s + 's') : s);
  function etatEtape(p) {
    const pane = $('#p-' + p);
    const rouges = pane ? $$('.req-missing, .obl-missing', pane).length : 0;
    const rows = C[p];
    switch (p) {
      case 'identite': case 'clinique':
        return rouges ? {e: 'todo', t: pl(rouges, 'champ') + T(' à compléter')} : {e: 'ok', t: T('complète')};
      case 'events': {
        if (!rows.length) return {e: 'no', t: T('aucune étape saisie')};
        const sansDate = rows.filter(r => !r.date_debut).length;
        const bits = [];
        const sansPers = rows.filter(r => !SANS_PERSONNES.has(r.type) && !(r.personnes || '').trim()).length;
        if (sansPers) bits.push(pl(sansPers, 'étape') + T(' sans personnes présentes'));
        if (sansDate) bits.push(pl(sansDate, 'date') + T(sansDate > 1 ? ' manquantes' : ' manquante'));
        return bits.length ? {e: 'todo', t: bits.join(' · ')} : {e: 'ok', t: pl(rows.length, 'étape') + ' · ' + T('complète')};
      }
      case 'places': return rows.length ? {e: 'ok', t: pl(rows.length, 'lieu', 'lieux')} : {e: 'no', t: T('aucun lieu saisi')};
      case 'contacts': {
        if (!rows.length) return {e: 'no', t: T('aucune catégorie')};
        const q = rows.filter(r => r.nombre === null || r.nombre === undefined || r.nombre === '').length;
        return q ? {e: 'todo', t: pl(q, 'groupe') + T(' à dénombrer')} : {e: 'ok', t: T('complète')};
      }
      case 'ipc': return rows.length ? {e: 'ok', t: pl(rows.length, 'site')} : {e: 'no', t: T('aucun site saisi')};
      case 'labs': return rows.length ? {e: 'ok', t: pl(rows.length, 'prélèvement')} : {e: 'no', t: T('aucun prélèvement')};
      case 'actions': {
        if (rows.length) return {e: 'ok', t: pl(rows.length, 'action')};
        const n = CTRL && CTRL.suggestions ? CTRL.suggestions.length : 0;
        return {e: 'no', t: T('facultatif') + (n ? ' · ' + pl(n, 'suggestion') : '')};
      }
    }
    return {e: 'no', t: ''};
  }
  function allerA(p) {
    const b = $('#tabs button[data-p="' + p + '"]'); if (b) b.click();
    const c = $('.editor > section.card'); if (c) c.scrollIntoView({behavior: 'smooth', block: 'start'});
  }
  function renderEtapes() {
    if (!$('#tabs')) return;
    let ok = 0;
    const manques = [];
    ETAPES.forEach(([p, nom], i) => {
      const s = etatEtape(p);
      if (s.e === 'ok') ok++;
      if (s.e === 'todo') manques.push([p, nom.replace(/^\d+\. /, '') + SEP + s.t]);
      const b = $('#tabs button[data-p="' + p + '"]'); if (!b) return;
      b.className = s.e + (b.classList.contains('on') ? ' on' : '');
      b.innerHTML = '';
      b.appendChild(el('span', {class: 'n', text: s.e === 'ok' ? '✓' : String(i + 1)}));
      b.appendChild(el('span', {class: 'lb'}, [el('span', {text: nom.replace(/^\d+\. /, (i + 1) + '. ')}), el('small', {text: s.t})]));
      const pane = $('#p-' + p);
      let tete = pane && $('.etape-tete', pane);
      if (pane && !tete) {
        tete = el('div', {class: 'etape-tete'});
        pane.insertBefore(tete, pane.firstChild);
        const nav = el('div', {class: 'etape-nav'});
        nav.appendChild(i > 0 ? el('button', {type: 'button', class: 'btn small', text: '← ' + ETAPES[i - 1][1], on: {click: () => allerA(ETAPES[i - 1][0])}}) : el('span'));
        nav.appendChild(i < ETAPES.length - 1
          ? el('button', {type: 'button', class: 'btn small primary', text: ETAPES[i + 1][1] + ' →', on: {click: () => allerA(ETAPES[i + 1][0])}})
          : el('button', {type: 'button', class: 'btn small primary', text: T('Contrôles') + ' →', on: {click: () => allerA('controles')}}));
        pane.appendChild(nav);
      }
      if (tete) {
        tete.innerHTML = '';
        tete.appendChild(el('b', {text: nom}));
        tete.appendChild(el('span', {text: TF('Étape {i} sur {n}', {i: i + 1, n: ETAPES.length})}));
        let m = $('.etape-manque', pane);
        if (s.e === 'todo') {
          if (!m) { m = el('div', {class: 'etape-manque'}); tete.after(m); }
          m.textContent = T('À compléter ici : ') + s.t + '.';
        } else if (m) { m.parentNode.removeChild(m); }
      }
    });
    const cb = $('#tabs button[data-p="controles"]');
    if (cb && CTRL) {
      const al = CTRL.issues.filter(x => x.level === 'erreur' || x.level === 'alerte').length;
      const inf = CTRL.issues.length - al;
      cb.className = 'ctl' + (al ? ' todo' : ' ok') + (cb.classList.contains('on') ? ' on' : '');
      cb.innerHTML = '';
      cb.appendChild(el('span', {class: 'n', text: '✔'}));
      cb.appendChild(el('span', {class: 'lb'}, [el('span', {text: T('Contrôles')}),
        el('small', {text: (al ? pl(al, 'alerte') : T('aucune alerte')) + (inf ? ' · ' + pl(inf, 'information') : '')})]));
    }
    const box = $('#progression');
    if (box) {
      box.hidden = false; box.innerHTML = '';
      box.appendChild(el('b', {text: TF(ok > 1 ? '{ok} étapes sur {n} complètes' : '{ok} étape sur {n} complète', {ok, n: ETAPES.length})}));
      box.appendChild(el('span', {class: 'pb'}, [el('i', {style: 'width:' + Math.round(100 * ok / ETAPES.length) + '%'})]));
      if (CTRL) box.appendChild(el('b', {text: T('Complétude') + ' ' + CTRL.score + PCT}));
      if (manques.length) {
        const m = el('span', {class: 'manque'}, [el('span', {text: T('Il manque :')})]);
        manques.forEach(([p, t], j) => {
          m.appendChild(el('a', {text: t, on: {click: () => allerA(p)}}));
          if (j < manques.length - 1) m.appendChild(document.createTextNode('·'));
        });
        box.appendChild(m);
      }
    }
    const mis = $('#missing'); if (mis) mis.hidden = true;      // remplacé par la barre de progression
  }
  function renderSuggestions() {
    const box = $('#suggestions'); if (!CTRL) return; box.innerHTML = '';
    const have = new Set(C.actions.map(a => a.texte));
    const list = CTRL.suggestions.filter(s => !have.has(s.texte));
    if (!list.length) { box.appendChild(el('p', {class: 'muted', text: T('Aucune suggestion en attente.')})); }
    list.forEach(s => {
      box.appendChild(el('div', {class: 'sugg' + (s.priorite === 'Urgent' ? ' urgent' : ''), title: s.raison}, [
        el('span', {}, [el('b', {text: '[' + T(s.priorite) + '] '}), s.affiche || s.texte]),
        el('span', {class: 'row'}, [
          el('button', {class: 'btn small', text: T('Ajouter'), on: {click: () => { C.actions.push(Object.assign(blankRow('actions'), {texte: s.texte, priorite: s.priorite, auto: true, id: Math.random().toString(16).slice(2, 12)})); renderTable('actions'); renderSuggestions(); changed(); }}}),
          el('button', {class: 'btn small', text: T('Ignorer'), on: {click: () => { C.suggestions_rejetees.push(s.texte); CTRL.suggestions = CTRL.suggestions.filter(x => x !== s); renderSuggestions(); changed(); }}})])]));
    });
    if (C.suggestions_rejetees.length) box.appendChild(el('button', {class: 'btn small', text: T('Rétablir les suggestions ignorées'), on: {click: () => { C.suggestions_rejetees = []; changed(); }}}));
  }

  // ---------------------------------------------------------------- aperçu
  function refreshPreview() {
    const f = $('#pv');
    f.src = '/cas/' + ID + '/apercu/' + visual + '?t=' + Date.now();
    updateDownloads();
  }
  function scaleFrame() {
    const fr = $('#frame'), pv = $('#pv');
    if (enPleinEcran()) {          // plein écran : le visuel entier, centré, sans déformation
      const s = Math.min(fr.clientWidth / 1280, fr.clientHeight / 720);
      pv.style.left = Math.max(0, (fr.clientWidth - 1280 * s) / 2) + 'px';
      pv.style.top = Math.max(0, (fr.clientHeight - 720 * s) / 2) + 'px';
      pv.style.transform = 'scale(' + s + ')';
      return;
    }
    pv.style.left = '0px';
    pv.style.top = '0px';
    pv.style.transform = 'scale(' + (fr.clientWidth / 1280) + ')';
  }

  // ------------------------------------------------- plein écran (sans téléchargement)
  const zonePreview = () => document.querySelector('section.preview');
  const enPleinEcran = () => !!(zonePreview() && zonePreview().classList.contains('plein'));
  function pleinEcran(oui) {
    const z = zonePreview(); if (!z) return;
    z.classList.toggle('plein', oui);
    document.body.classList.toggle('apercu-plein', oui);
    if (oui && z.requestFullscreen && !document.fullscreenElement) {
      z.requestFullscreen().catch(() => {});          // sans plein écran du navigateur : la vue couvre la fenêtre
    } else if (!oui && document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    setTimeout(scaleFrame, 60);
  }
  document.addEventListener('fullscreenchange', () => { if (!document.fullscreenElement && enPleinEcran()) pleinEcran(false); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && enPleinEcran()) pleinEcran(false); });
  window.addEventListener('resize', () => { if (enPleinEcran()) scaleFrame(); });
  function updateDownloads() {
    $$('#dl a').forEach(a => {
      const fmt = a.dataset.fmt;
      a.href = '/cas/' + ID + '/telecharger/' + fmt + '?visuel=' + (a.dataset.any ? 'mapping' : visual);
      a.style.display = a.dataset.only && a.dataset.only !== visual ? 'none' : '';
    });
  }

  // ----------------------------------------------------------------- init
  function lockEditor() {
    $$('.editor > section.card .pane').forEach(p => $$('input, select, textarea, button', p).forEach(x => { x.disabled = true; }));
    $$('[data-add], #sortEvents, #fillGaps, #prefill').forEach(b => { b.style.display = 'none'; });
  }

  async function init() {
    try {
      const [schema, pyr, data] = await Promise.all([api('/api/schema'), api('/api/pyramide'), api('/api/cas/' + ID)]);
      S = schema; PYR = pyr; C = data.case; CTRL = data.controls;
    } catch (e) { setStatus(T('Chargement impossible : ') + e.message, true); return; }
    renderIdentity(); renderClinic();
    ['events', 'places', 'contacts', 'ipc', 'labs', 'actions'].forEach(renderTable);
    renderControls(); renderSuggestions(); updateTitle();

    $$('#tabs button').forEach(b => b.addEventListener('click', () => {
      $$('#tabs button').forEach(x => x.classList.toggle('on', x === b));
      $$('.pane').forEach(p => p.classList.toggle('on', p.id === 'p-' + b.dataset.p));
    }));
    $$('#vtabs button[data-v]').forEach(b => b.addEventListener('click', () => {
      $$('#vtabs button[data-v]').forEach(x => x.classList.toggle('on', x === b));
      visual = b.dataset.v; refreshPreview();
    }));
    const bp = $('#pleinEcran'), br = $('#reduireEcran');
    if (bp) bp.addEventListener('click', () => pleinEcran(true));
    if (br) br.addEventListener('click', () => pleinEcran(false));
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
      if (!j.events.length) { toast(T('Aucune période non couverte détectée.')); return; }
      C.events = C.events.concat(j.events); renderTable('events'); changed(); toast(TF('{n} période(s) à documenter ajoutée(s).', {n: j.events.length}));
    });
    $('#prefill').addEventListener('click', async () => {
      await flush();
      const j = await api('/api/cas/' + ID + '/places-depuis-chronologie', {method: 'POST', body: '{}'});
      if (!j.places.length) { toast(T('Tous les lieux de la chronologie sont déjà listés.')); return; }
      C.places = C.places.concat(j.places); renderTable('places'); changed(); toast(TF('{n} lieu(x) ajouté(s).', {n: j.places.length}));
    });
    if (RO) lockEditor();
    if ($('#saveVersion')) $('#saveVersion').addEventListener('click', async () => {
      const com = prompt(T('Commentaire de version (facultatif) :'), '');
      if (com === null) return;
      clearTimeout(timer); await save(true, com); toast(T('Version enregistrée dans l\'historique.'));
    });
    // téléchargement : le bouton affiche « Génération… » jusqu'à ce que le fichier soit prêt, ou dit pourquoi il a échoué
    $$('#dl a').forEach(a => a.addEventListener('click', async ev => {
      ev.preventDefault();
      if (a.classList.contains('busy')) return;
      await flush();
      const label = a.textContent;
      a.classList.add('busy'); a.textContent = ' ' + T('Génération…');
      try {
        const r = await fetch(a.href, {credentials: 'same-origin'});
        if (!r.ok) {
          const txt = (await r.text().catch(() => '')).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
          throw new Error(r.status === 403 ? T('réservé aux administrateurs') : (txt.slice(0, 160) || (T('erreur') + ' ' + r.status)));
        }
        const blob = await r.blob();
        const cd = r.headers.get('Content-Disposition') || '';
        const m = cd.match(/filename\*=UTF-8''([^;]+)/i) || cd.match(/filename="?([^";]+)"?/i);
        const nom = m ? decodeURIComponent(m[1]) : ('mapping.' + a.dataset.fmt);
        const url = URL.createObjectURL(blob);
        const lien = document.createElement('a');
        lien.href = url; lien.download = nom; lien.style.display = 'none';
        document.body.appendChild(lien); lien.click(); document.body.removeChild(lien);
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        toast(T('Fichier prêt : ') + nom, 3500);
      } catch (e) {
        toast(T('Téléchargement impossible : ') + e.message, 7000);
      } finally {
        a.classList.remove('busy'); a.textContent = label;
      }
    }));
    new ResizeObserver(scaleFrame).observe($('#frame'));
    scaleFrame(); refreshPreview();
  }
  document.addEventListener('DOMContentLoaded', init);
})();
