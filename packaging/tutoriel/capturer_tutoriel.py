"""Régénère le tutoriel cliquable (web/static/tutoriel) à partir de l'interface ACTUELLE de Mapping Épi.

Usage (depuis la racine du projet) :
    QT_QPA_PLATFORM=offscreen .venv/bin/python packaging/tutoriel/capturer_tutoriel.py

Le script lance l'outil sur une base temporaire (cas fictif, aucune donnée réelle), le pilote comme un utilisateur
(saisie champ par champ, ajout des étapes de la chronologie, onglets, plein écran, téléchargements, réimport),
capture chaque écran et écrit : frames/t*.jpg, frames/x*.jpg, frames/r*.jpg, frames/n*.jpg, les données du
parcours (DATA dans index.html), le guide Word et les deux classeurs Excel d'exemple.
"""
from __future__ import annotations

import base64
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TMP = Path(tempfile.mkdtemp(prefix="tuto_"))
os.environ["MAPPING_EPI_DONNEES"] = str(TMP / "donnees")

from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402

from core import storage  # noqa: E402
from core.storage import Store  # noqa: E402
from core.users import Users  # noqa: E402

OUT = ROOT / "web" / "static" / "tutoriel"
FR = OUT / "frames"
W, H = 1920, 1080
PWD = "Tuto2026demo"


def port_libre() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ------------------------------------------------------------------------------------------- serveur et données
PORT = port_libre()
st = Store(TMP / "donnees" / "mapping_epi.sqlite")
Users(st).create("zs.bikoro", PWD, "Équipe ZS Bikoro (exemple)", niveau="zone", province="Équateur", zs="Bikoro")


def serveur():
    from waitress import serve
    from web.server import create_app
    serve(create_app(st), host="127.0.0.1", port=PORT, threads=4, _quiet=True)


threading.Thread(target=serveur, daemon=True).start()
time.sleep(1.5)
BASE = f"http://127.0.0.1:{PORT}"

# fichiers d'exemple (modèle vierge, exemple rempli, narratif libre) à partir du cas fictif
EX = storage.load_json(ROOT / "sample_data" / "cas_exemple_fictif.json")
EX.code_cas = "FICTIF-BIK-26-004"
EX.province, EX.zs, EX.aire_sante = "Équateur", "Bikoro", "PENZELE"
storage.export_excel_template(OUT / "Modele_Mapping_ZS_vierge.xlsx")
storage.export_excel(EX, OUT / "Exemple_Mapping_rempli_FICTIF.xlsx")
XLSX_B64 = base64.b64encode((OUT / "Exemple_Mapping_rempli_FICTIF.xlsx").read_bytes()).decode()


def narratif_docx() -> bytes:
    from docx import Document
    d = Document()
    d.add_heading("Narratif du cas FICTIF-BIK-26-005 (exemple)", 1)
    for p in ["Cas confirmé de MVE, sexe masculin, 34 ans, cultivateur, ZS Bikoro, AS Penzele, province de l'Équateur.",
              "Le 03/08/2026, il a assisté aux funérailles d'un parent à Monzombo.",
              "Le 14/08/2026, début de la maladie : fièvre, fatigue et céphalées ; consultation au CS Penzele.",
              "Le 17/08/2026, référé à l'HGR Bikoro à moto, accompagné de son épouse.",
              "Le 18/08/2026, prélèvement ; résultat positif le 19/08/2026 au laboratoire provincial.",
              "Contacts : famille (8 personnes), prestataires du CS Penzele (4 personnes), motard (1).",
              "Décontamination du CS Penzele faite le 20/08/2026."]:
        d.add_paragraph(p)
    f = TMP / "narratif.docx"
    d.save(str(f))
    return f.read_bytes()


DOCX_B64 = base64.b64encode(narratif_docx()).decode()

# ------------------------------------------------------------------------------------------- aides JS dans la page
AIDES = r"""
window.__T = window.__T || (function () {
  const norm = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  function champ(lib) {
    const l = [...document.querySelectorAll('label.f')].find(x => norm(x.textContent).startsWith(norm(lib)));
    return l ? l.parentElement.querySelector('input, select, textarea') : null;
  }
  function tape(el, v) {
    if (!el) return;
    if (el.tagName === 'SELECT') { el.value = v; el.dispatchEvent(new Event('change', {bubbles: true})); return; }
    if (el.type === 'checkbox') { el.checked = !!v; el.dispatchEvent(new Event('change', {bubbles: true})); return; }
    el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));
  }
  let cols = {};
  fetch('/api/schema').then(r => r.json()).then(s => { for (const t in s.tables) cols[t] = s.tables[t].map(c => c.key); }).catch(() => {});
  function ligne(table, i) {
    const trs = document.querySelectorAll('#t-' + table + ' tbody tr');
    return i === undefined ? trs[trs.length - 1] : trs[i];
  }
  function cellule(table, key, i) {
    const tr = ligne(table, i); const j = (cols[table] || []).indexOf(key);
    return tr && j >= 0 ? tr.children[j].querySelector('input, select') : null;
  }
  function remplir(table, vals, i) { for (const k in vals) tape(cellule(table, k, i), vals[k]); }
  function onglet(p) { const b = document.querySelector('#tabs button[data-p="' + p + '"]'); if (b) b.click(); }
  function ajoute(table) { const b = document.querySelector('[data-add="' + table + '"]'); if (b) b.click(); }
  function boite(el, marge) {
    if (!el) return null;
    const r = el.getBoundingClientRect(), m = marge || 4, w = document.documentElement.clientWidth, h = document.documentElement.clientHeight;
    const x0 = Math.max(0, r.left - m), y0 = Math.max(0, r.top - m), x1 = Math.min(w, r.right + m), y1 = Math.min(h, r.bottom + m);
    return [100 * x0 / w, 100 * y0 / h, 100 * (x1 - x0) / w, 100 * (y1 - y0) / h].map(v => Math.round(v * 100) / 100);
  }
  function voir(el, bloc) { if (el) el.scrollIntoView({block: bloc || 'center', inline: 'nearest'}); }
  function fichier(sel, b64, nom, type) {
    const inp = document.querySelector(sel); if (!inp) return;
    const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    const dt = new DataTransfer(); dt.items.add(new File([u], nom, {type: type}));
    inp.files = dt.files; inp.dispatchEvent(new Event('change', {bubbles: true}));
  }
  return {champ, tape, ligne, cellule, remplir, onglet, ajoute, boite, voir, fichier, cols: () => cols};
})();
"""

# ------------------------------------------------------------------------------------------- étapes
# chaque étape : chapitre, image, titre, texte, valeur affichée, url (facultatif), action JS (avant capture),
# cible JS (élément encadré, évaluée après l'action), attente en ms
CH = {"web": "Saisie dans l'outil", "excel": "Fichier Excel", "fiche": "Corriger avec Word ou Excel", "narr": "Importer un narratif"}
ETAPES = []


def E(partie, titre, texte, valeur=None, url=None, act="", cible="null", attente=700, final=False, bloc="center"):
    ETAPES.append(dict(partie=partie, titre=titre, texte=texte, valeur=valeur, url=url, act=act, cible=cible,
                       attente=attente, final=final, bloc=bloc))


T = "window.__T"
# --- 1. saisie dans l'outil --------------------------------------------------------------------------------------
E("web", "Ouvrir le site et s'identifier", "Ouvrez l'adresse de Mapping Épi. Cliquez dans le champ « Identifiant » et tapez l'identifiant reçu de l'administrateur.",
  "zs.bikoro", url="/connexion", act=f"{T}.tape(document.querySelector('input[name=username]'), 'zs.bikoro');",
  cible="document.querySelector('input[name=username]')")
E("web", "Mot de passe", "Tapez votre mot de passe personnel. Ne le partagez avec personne.", "••••••••",
  act=f"{T}.tape(document.querySelector('input[name=password]'), '{PWD}');", cible="document.querySelector('input[name=password]')")
E("web", "Se connecter", "Cliquez sur « Se connecter ».", cible="document.querySelector('form button')")
E("web", "Créer une fiche", "La page d'accueil propose de créer un nouveau cas ou d'importer une fiche déjà remplie (Word ou Excel). Cliquez sur « Nouveau cas ».",
  act="document.querySelector('form').submit();", url=None, cible="document.querySelector('.tuile.primaire')", attente=1800)
E("web", "La fiche s'ouvre", "La fiche se remplit par étapes : la liste à gauche indique pour chaque étape ce qui est complet (✓ vert) ou ce qui manque (orange). L'aperçu du mapping est à droite.",
  act=f"document.querySelector('.tuile.primaire').click();", cible="document.querySelector('#tabs')", attente=3000, bloc="start")
E("web", "ID du cas", "Tapez l'identifiant du cas (N° EPID). La fiche s'enregistre toute seule : le statut « ✓ Enregistré » s'affiche en haut.",
  "DEMO-BIK-26-003", act=f"{T}.tape(document.querySelector('[data-k=code_cas]'), 'DEMO-BIK-26-003');",
  cible="document.querySelector('[data-k=code_cas]')", attente=1500)
E("web", "Contact connu ou non contact", "Le cas était-il déjà un contact listé ? Cliquez sur le bon bouton : Inconnu, Contact connu, Contact connu suivi ou Non contact.",
  "Contact connu", act="[...document.querySelectorAll('.seg-b')].find(b => b.textContent.trim() === 'Contact connu').click();",
  cible="document.querySelector('.seg')")
E("web", "Cas source et date du dernier contact", "Pour un contact connu, tapez l'ID du cas dont il était le contact et la date du dernier contact avec lui. Tant qu'ils sont vides, les cases restent rouges.",
  "DEMO-BIK-26-001 · 01/07/2026", act=f"{T}.tape(document.querySelector('[data-k=id_cas_source]'), 'DEMO-BIK-26-001'); {T}.tape(document.querySelector('[data-k=date_contact_source]'), '2026-07-01');",
  cible="document.querySelector('[data-k=id_cas_source]').closest('div')")
E("web", "Sexe, âge, profession", "Choisissez le sexe, tapez l'âge et la profession. Âge inconnu : laissez vide (il s'affichera « ? »).",
  "F · 41 ans · Commerçante", act=f"{T}.tape({T}.champ('Sexe'), 'F'); {T}.tape(document.querySelector('[data-k=age]'), '41'); {T}.tape(document.querySelector('[data-k=profession]'), 'Commerçante');",
  cible="document.querySelector('[data-k=age]').closest('div')")
E("web", "Agent de santé et vaccination", "Indiquez si le cas est un agent de santé (PPL) et s'il était vacciné. La date de début de la vaccination en anneau se renseigne dès qu'elle est connue.",
  "Non · Non · 30/07/2026", act=f"{T}.tape({T}.champ('Agent de santé'), 'Non'); {T}.tape({T}.champ('Vacciné'), 'Non'); {T}.tape(document.querySelector('[data-k=date_debut_anneau]'), '2026-07-30');",
  cible="document.querySelector('[data-k=date_debut_anneau]').closest('div')")
E("web", "Province, zone et aire de santé", "Choisissez dans l'ordre la province, puis la zone de santé, puis l'aire de santé : chaque liste se filtre selon la précédente.",
  "Équateur → Bikoro → PENZELE", act=f"{T}.tape({T}.champ('Province'), 'Équateur'); setTimeout(() => {{ {T}.tape({T}.champ('Zone de santé'), 'Bikoro'); {T}.tape({T}.champ('Aire de santé'), 'PENZELE'); }}, 300);",
  cible="window.__T.champ('Province').closest('div')", attente=1500)
E("web", "Notification, confirmation, état", "Indiquez la date de notification, la date de confirmation, l'état du cas et l'équipe d'investigation.",
  "28/07/2026 · 30/07/2026 · Décès · Équipe ZS Bikoro", act=f"{T}.tape(document.querySelector('[data-k=date_notification]'), '2026-07-28'); {T}.tape(document.querySelector('[data-k=date_confirmation]'), '2026-07-30'); {T}.tape({T}.champ('État du cas'), 'Décès'); {T}.tape(document.querySelector('[data-k=investigateur]'), 'Équipe ZS Bikoro');",
  cible="document.querySelector('[data-k=date_notification]').closest('div')", attente=1500)
E("web", "Étape 2 : Clinique", "L'étape « 1. Identité » est cochée en vert dans la liste. Passez à « 2. Clinique ».", cible="document.querySelector('#tabs button[data-p=clinique]')", bloc="start")
E("web", "Début des symptômes (J0) et phase", "Tapez la date de début des symptômes rapportée par l'équipe et la phase des premiers signes. L'outil retient J0 = date rapportée − 3 jours pour la phase sèche, puis estime l'exposition et les phases.",
  "19/07/2026 · Phase sèche", act=f"{T}.onglet('clinique'); setTimeout(() => {{ {T}.tape(document.querySelector('[data-k=debut_symptomes]'), '2026-07-19'); {T}.tape(document.querySelector('[data-k=phase_dds]'), 'Phase sèche'); {T}.tape(document.querySelector('[data-k=date_deces]'), '2026-07-28'); }}, 300);",
  cible="document.querySelector('[data-k=debut_symptomes]').closest('div')", attente=1500)
E("web", "Symptômes", "Cochez les symptômes rapportés. Ils sont groupés comme sur le schéma des phases : phase sèche, phase humide, signes hémorragiques.",
  "Fièvre, fatigue, céphalées, vomissements, diarrhée, gingivorragie",
  act="['Fièvre', 'Fatigue / asthénie', 'Céphalées (maux de tête)', 'Vomissements', 'Diarrhée', 'Gingivorragie'].forEach(s => { const c = [...document.querySelectorAll('#p-clinique input[type=checkbox]')].find(x => x.parentElement.textContent.trim().startsWith(s)); if (c && !c.checked) c.click(); });",
  cible="document.querySelector('#p-clinique .symptoms') || document.querySelector('#p-clinique input[type=checkbox]').closest('div')", attente=1500)

CHRONO = [
    ("Exposition probable", "Le cas a fréquenté le marché de Penzele pendant la période d'exposition estimée.",
     dict(date_debut="2026-07-02", date_fin="2026-07-15", lieu="Marché de Penzele", type="Exposition", titre="Exposition probable",
          description="Marché fréquenté • contact possible à investiguer", personnes="Commerçants / clients"), "02/07 → 15/07 · Marché de Penzele · Exposition"),
    ("Début de la maladie", "Premiers signes : fièvre, fatigue, céphalées. Consultation au centre de santé.",
     dict(date_debut="2026-07-19", lieu="CS Penzele", type="Début maladie", titre="Début maladie / soins",
          description="Fièvre • asthénie • céphalées", personnes="Prestataires / patients"), "19/07 · CS Penzele · Début maladie"),
    ("Référence à l'hôpital", "Aggravation : le cas est référé du CS vers l'HGR à moto. Remplissez « Lieu d'arrivée » et le transport.",
     dict(date_debut="2026-07-24", lieu="CS Penzele", lieu_arrivee="HGR Bikoro", type="Référence", titre="Référence",
          description="Aggravation • taxi-moto", transport="Moto", personnes="Motard / accompagnant"), "24/07 · CS Penzele → HGR Bikoro · Moto"),
    ("Hospitalisation", "Le cas est hospitalisé : vomissements, diarrhée, saignements des gencives. Cochez « Liquides biologiques ».",
     dict(date_debut="2026-07-24", date_fin="2026-07-27", lieu="HGR Bikoro", type="Hospitalisation", titre="Hospitalisation",
          description="Médecine interne • diarrhée • gingivorragie", personnes="Soignants / co-patients", liquides=True), "24/07 → 27/07 · HGR Bikoro · Hospitalisation"),
    ("Décès et retour du corps", "Décès à l'hôpital, corps ramené au village en véhicule privé. Cochez « Contact corps ».",
     dict(date_debut="2026-07-28", lieu="HGR Bikoro", lieu_arrivee="Monzombo", type="Décès", titre="Décès / transport",
          description="Corps ramené en véhicule privé", transport="Véhicule", personnes="Famille", contact_corps=True), "28/07 · HGR Bikoro → Monzombo · Décès"),
    ("Funérailles et enterrement", "Funérailles au village, puis enterrement sans sécurisation du corps.",
     dict(date_debut="2026-07-29", lieu="Monzombo", type="Enterrement", titre="Funérailles et enterrement",
          description="Sans sécurisation du corps • communauté large", personnes="Famille élargie / communauté", contact_corps=True), "29/07 · Monzombo · Enterrement"),
    ("Résultat du laboratoire", "Le prélèvement post-mortem est positif. Pour une étape sans personnes exposées (laboratoire, riposte), le champ « Personnes présentes » n'est pas exigé.",
     dict(date_debut="2026-07-30", lieu="Laboratoire provincial", type="Laboratoire", titre="Résultat positif",
          description="Analyse et résultat le jour même"), "30/07 · Laboratoire provincial · Positif"),
]
E("web", "Étape 3 : Chronologie", "Passez à « 3. Chronologie » : une ligne par étape du parcours du cas, de l'exposition à la riposte.",
  act=f"{T}.onglet('events');", cible="document.querySelector('#tabs button[data-p=events]')", bloc="start")
for i, (titre, texte, vals, val) in enumerate(CHRONO, 1):
    js = json.dumps(vals, ensure_ascii=False)
    E("web", f"Chronologie {i}/{len(CHRONO)} : {titre}",
      ("Cliquez sur « + Ajouter une étape », puis remplissez la ligne : date de début (et de fin pour une période), lieu, type, titre, "
       "description et personnes présentes. Laissez « Risque » vide : l'outil le calcule. " if i == 1 else "") + texte
      + " L'aperçu du mapping à droite se met à jour.",
      val, act=f"{T}.onglet('events'); {T}.ajoute('events'); setTimeout(() => {T}.remplir('events', {js}), 200);",
      cible=f"{T}.ligne('events')", attente=4200)
E("web", "Trier par date", "« Trier par date » remet les étapes dans l'ordre. La liste à gauche indique « 7 étapes · complète » quand chaque étape a sa date et ses personnes présentes.",
  cible="document.querySelector('#sortEvents')", act="document.querySelector('#sortEvents').click();", attente=1500)
E("web", "Étape 4 : Lieux", "Passez à « 4. Lieux », puis cliquez sur « Pré-remplir depuis la chronologie » : les lieux des étapes sont ajoutés. Complétez les personnes exposées et leur nombre.",
  act=f"{T}.onglet('places'); setTimeout(() => document.querySelector('#prefill').click(), 300);", cible="document.querySelector('#prefill')", attente=2500, bloc="start")
E("web", "Étape 5 : Contacts", "Passez à « 5. Contacts » et ajoutez une ligne par catégorie : nombre de contacts, nombre suivis, risque, lieu, date du dernier contact et contacts vaccinés. Nombre inconnu : laissez vide (« ? »).",
  "Famille & voisins · 12 · 10 suivis · 29/07 · 8 vaccinés",
  act=f"{T}.onglet('contacts'); {T}.ajoute('contacts'); setTimeout(() => {T}.remplir('contacts', {{categorie: 'Famille & voisins', nombre: '12', suivis: '10', risque: 'Haut', lieu: 'Monzombo', dernier_contact: '2026-07-29', vaccines: '8'}}), 200); setTimeout(() => {{ {T}.ajoute('contacts'); setTimeout(() => {T}.remplir('contacts', {{categorie: 'Prestataires HGR', nombre: '6', suivis: '6', risque: 'Haut', lieu: 'HGR Bikoro', dernier_contact: '2026-07-27', vaccines: '6'}}), 200); }}, 700);",
  cible="document.querySelector('#t-contacts')", attente=3000)
E("web", "Étape 6 : PCI et adresse des sites", "Passez à « 6. PCI ». Pour chaque site : statut de décontamination, date, équipe et adresse (avenue, quartier, repère). L'adresse figure sur la carte du parcours et dans le menu PCI.",
  "HGR Bikoro · Décontaminé · 31/07 · Av. de l'Hôpital",
  act=f"{T}.onglet('ipc'); {T}.ajoute('ipc'); setTimeout(() => {T}.remplir('ipc', {{site: 'HGR Bikoro', statut: 'Décontaminé', date: '2026-07-31', equipe: 'Équipe PCI ZS', produit: 'Chlore 0,5 %', adresse: \"Av. de l'Hôpital, Q. Centre\"}}), 200);",
  cible="document.querySelector('#t-ipc')", attente=2500)
E("web", "Étape 7 : Laboratoire", "Passez à « 7. Laboratoire » : type d'échantillon, laboratoire, dates et heures du prélèvement et du résultat. Le délai est calculé.",
  "Swab · Laboratoire provincial · Positif",
  act=f"{T}.onglet('labs'); {T}.ajoute('labs'); setTimeout(() => {T}.remplir('labs', {{type: 'Swab', laboratoire: 'Laboratoire provincial', prelevement: '2026-07-28T17:00', resultat_le: '2026-07-30T19:00', resultat: 'Positif'}}), 200);",
  cible="document.querySelector('#t-labs')", attente=2500)
E("web", "Étape 8 : Actions", "Passez à « 8. Actions ». Les actions suggérées apparaissent en bas : cliquez sur « Ajouter » ou décrivez la vôtre, avec priorité, responsable, échéance, pilier et statut (« Fait » quand elle est réalisée).",
  "Lister tous les contacts · Urgent",
  act=f"{T}.onglet('actions'); {T}.ajoute('actions'); setTimeout(() => {T}.remplir('actions', {{texte: 'Lister tous les contacts', priorite: 'Urgent', responsable: 'Surveillance ZS', echeance: '2026-08-01', pilier: 'Suivi des contacts'}}), 200);",
  cible="document.querySelector('#t-actions')", attente=2500)
E("web", "Contrôles", "« Contrôles » liste les alertes et les informations à vérifier avant de diffuser le mapping (dates incohérentes, champs manquants, noms de personnes à retirer).",
  act=f"{T}.onglet('controles');", cible="document.querySelector('#tabs button[data-p=controles]')", attente=1500, bloc="start")
E("web", "Voir le mapping en plein écran", "Cliquez sur « ⛶ Plein écran » : le visuel occupe tout l'écran, sans téléchargement, pour la lecture ou la projection.",
  cible="document.querySelector('#pleinEcran')", attente=800, bloc="start")
E("web", "Changer de visuel ou réduire", "En plein écran, les onglets permettent de passer au réseau de contacts, à la carte du parcours… Cliquez sur « ✕ Réduire » ou appuyez sur Échap pour revenir.",
  act="document.querySelector('#pleinEcran').click();", cible="document.querySelector('#reduireEcran')", attente=3500)
E("web", "Télécharger le mapping", "De retour sur la fiche, choisissez le format : PNG HD pour partager, PDF pour imprimer, PowerPoint pour une présentation modifiable.",
  "PNG HD", act="document.querySelector('#reduireEcran').click();", cible="document.querySelector('#dl')", attente=1500)
E("web", "Résultat : le mapping du cas", "Voici le mapping produit à partir de la saisie. Complétez la fiche quand de nouvelles informations arrivent : le mapping se met à jour.",
  act="document.querySelector('#pleinEcran').click();", cible="null", attente=3500, final=True)

# --- 2. corriger avec Word ou Excel (fiche modifiable) -----------------------------------------------------------
E("fiche", "Télécharger la fiche remplie", "Sous l'aperçu, « Fiche Word » et « Fiche Excel » téléchargent la fiche remplie avec tout ce qui est saisi. Vous pouvez la corriger tranquillement, même sans connexion.",
  act="if (document.querySelector('#reduireEcran').offsetParent) document.querySelector('#reduireEcran').click();",
  cible="document.querySelector('.fiche-modif .row')", attente=1500)
E("fiche", "Réimporter le fichier corrigé", "Choisissez le fichier corrigé puis cliquez sur « Réimporter dans cette fiche » : le même mapping est mis à jour (même cas, sans doublon). L'état précédent reste dans l'historique des versions.",
  "Fiche_DEMO-BIK-26-003.xlsx", act=f"{T}.fichier('.fiche-modif input[type=file]', '{XLSX_B64}', 'Fiche_DEMO-BIK-26-003.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');",
  cible="document.querySelector('.fiche-modif form')", attente=1000, final=True)

# --- 3. fichier Excel (modèle vierge, import) --------------------------------------------------------------------
E("excel", "Importer une fiche déjà remplie", "Sans connexion internet sur le terrain ? Remplissez le modèle Excel puis importez-le. Sur l'accueil, cliquez sur « Importer une fiche ».",
  url="/", cible="document.querySelector('a.tuile[href*=importer]')", attente=1500)
E("excel", "Télécharger le modèle", "La page d'import propose les modèles vierges : Excel, Word ou PowerPoint. Ils contiennent tous les champs de la fiche, y compris les plus récents (adresse des sites PCI, contacts vaccinés, pilier des actions…).",
  url="/cas/importer", cible="document.querySelector('.import-modeles')", attente=1500)
E("excel", "Choisir le fichier rempli", "Ouvrez le modèle dans Excel, remplissez la feuille « Cas » (colonne B) puis une ligne par étape, lieu, contact, site PCI, prélèvement et action. Enregistrez, puis choisissez le fichier ici.",
  "Exemple_Mapping_rempli_FICTIF.xlsx", act=f"{T}.fichier('#fichier', '{XLSX_B64}', 'Exemple_Mapping_rempli_FICTIF.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');",
  cible="document.querySelector('#fichier')", attente=1000)
E("excel", "Importer", "Cliquez sur « Importer et ouvrir la fiche ».", cible="document.querySelector('.import-page button.primary')")
E("excel", "La fiche est créée", "L'import crée la fiche complète et affiche son mapping. Vérifiez chaque étape (cases rouges), puis téléchargez le mapping.",
  act="document.querySelector('.import-page form').submit();", cible="null", attente=4500, final=True)

# --- 4. importer un ancien narratif ------------------------------------------------------------------------------
E("narr", "Choisir le narratif", "Vous avez déjà un narratif Word ou PowerPoint ? Sur la page « Importer une fiche », choisissez-le (.docx, .pptx ou .ppt).",
  "Narratif_cas_FICTIF.docx", url="/cas/importer",
  act=f"{T}.fichier('#fichier', '{DOCX_B64}', 'Narratif_cas_FICTIF.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');",
  cible="document.querySelector('#fichier')", attente=1500)
E("narr", "Importer", "Cliquez sur « Importer et ouvrir la fiche ». L'outil lit le récit et remplit la fiche : identité, dates, chronologie, symptômes, contacts…",
  cible="document.querySelector('.import-page button.primary')")
E("narr", "Lire le message", "Le message liste ce qui a été trouvé et ce qui reste à compléter. Rien n'est inventé : une information absente du narratif reste vide.",
  act="document.querySelector('.import-page form').submit();", cible="document.querySelector('.flash, .alert, .flashes')", attente=4500, bloc="start")
E("narr", "Vérifier la chronologie", "Ouvrez « 3. Chronologie » : chaque phrase datée du récit est devenue une étape. Complétez les cases rouges (personnes présentes…).",
  act=f"{T}.onglet('events');", cible="document.querySelector('#t-events')", attente=2000)
E("narr", "Résultat : le mapping du narratif", "Le mapping est produit directement à partir du narratif. Les informations manquantes apparaissent « à compléter » en rouge.",
  act="document.querySelector('#pleinEcran').click();", cible="null", attente=3500, final=True)

# ------------------------------------------------------------------------------------------- moteur de capture
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface  # noqa: E402
QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)    # capture possible sans écran
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --lang=fr")
from PySide6.QtCore import QLocale  # noqa: E402
QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.France))
app = QApplication(sys.argv[:1])
view = QWebEngineView()
view.resize(W, H)
view.show()
page = view.page()
donnees = {k: [] for k in CH}
compteur = {"web": 0, "fiche": 0, "excel": 0, "narr": 0}
PREFIXE = {"web": "t", "fiche": "r", "excel": "x", "narr": "n"}
i_etape = [0]
FR.mkdir(parents=True, exist_ok=True)
for f in FR.glob("*.jpg"):
    if f.name[0] in "trxnw" and f.name[0] != "e":
        f.unlink()


def js(code, cb=None):
    page.runJavaScript(AIDES + "\n" + code, 0, cb or (lambda _r: None))


def suivante():
    if i_etape[0] >= min(len(ETAPES), int(os.environ.get("TUTO_MAX", "999"))):
        fin()
        return
    e = ETAPES[i_etape[0]]
    if e["url"]:
        page.loadFinished.connect(apres_chargement)
        view.load(QUrl(BASE + e["url"]))
    else:
        action(e)


def apres_chargement(_ok):
    try:
        page.loadFinished.disconnect(apres_chargement)
    except Exception:
        pass
    QTimer.singleShot(900, lambda: action(ETAPES[i_etape[0]]))


def action(e):
    js(e["act"] or "0", lambda _r: QTimer.singleShot(e["attente"], lambda: cadrer(e)))


def cadrer(e):
    code = f"(function () {{ const el = ({e['cible']}); {T}.voir(el, '{e['bloc']}'); return null; }})()"
    js(code, lambda _r: QTimer.singleShot(350, lambda: mesurer(e)))


def mesurer(e):
    js(f"(function () {{ try {{ const el = ({e['cible']}); return JSON.stringify({T}.boite(el, 5)); }} catch (err) {{ return 'ERR ' + err; }} }})()",
       lambda b: capturer(e, _boite(b)))


def _boite(b):
    try:
        v = json.loads(b) if isinstance(b, str) and not b.startswith("ERR") else b
    except ValueError:
        v = None
    if not isinstance(v, list):
        print("   boîte :", b)
        return None
    return v


def capturer(e, boite):
    p = e["partie"]
    compteur[p] += 1
    nom = f"{PREFIXE[p]}{compteur[p]:02d}.jpg" if not e["final"] else f"{PREFIXE[p]}_fin.jpg"
    view.grab().save(str(FR / nom), "JPG", 84)
    donnees[p].append({"chapter": CH[p], "img": f"frames/{nom}", "title": e["titre"], "text": e["texte"],
                       "value": e["valeur"], "box": None if e["final"] else boite, **({"final": True} if e["final"] else {})})
    print(f"{nom:10} {e['titre']}  {boite}")
    i_etape[0] += 1
    QTimer.singleShot(100, suivante)


def fin():
    ecrire_index()
    ecrire_guide()
    app.quit()


def ecrire_index():
    f = OUT / "index.html"
    s = f.read_text(encoding="utf-8")
    # captures du classeur ouvert dans Excel (e02 à e09) : gardées, insérées après « Télécharger le modèle »
    ancien = json.loads(re.search(r"const DATA = (\{.*?\});\n", s, flags=re.S).group(1))
    classeur = [x for x in ancien.get("excel", []) if re.search(r"frames/e0[2-9]\.jpg$", x.get("img", ""))]
    for x in classeur:
        x["text"] = x["text"].replace("Dans « Mes cas »", "Sur la page « Importer une fiche »")
    excel = donnees["excel"][:2] + classeur + donnees["excel"][2:]
    data = {"web": donnees["web"], "fiche": donnees["fiche"], "excel": excel, "narr": donnees["narr"]}
    s = re.sub(r"const DATA = \{.*?\};\n", lambda m: "const DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", s, count=1, flags=re.S)
    f.write_text(s, encoding="utf-8")


def ecrire_guide():
    from docx import Document
    from docx.shared import Cm, Pt
    d = Document()
    d.add_heading("Mapping Épi : guide pas à pas (cas fictif)", 0)
    d.add_paragraph("Captures de l'interface actuelle. Cas fictif d'exercice : aucune donnée réelle.")
    for p, titre in (("web", "1. Saisie dans l'outil"), ("fiche", "2. Corriger avec Word ou Excel"),
                     ("excel", "3. Importer un fichier Excel"), ("narr", "4. Importer un ancien narratif")):
        d.add_heading(titre, 1)
        for k, e in enumerate(donnees[p], 1):
            d.add_heading(f"{k}. {e['title']}", 2)
            d.add_paragraph(e["text"])
            if e.get("value"):
                r = d.add_paragraph().add_run("À saisir / choisir : " + e["value"])
                r.font.size = Pt(10)
                r.bold = True
            d.add_picture(str(OUT / e["img"]), width=Cm(16))
    d.save(str(OUT / "Tutoriel_Mapping_Epi.docx"))


QTimer.singleShot(500, suivante)
app.exec()
print("Terminé :", {k: len(v) for k, v in donnees.items()})
