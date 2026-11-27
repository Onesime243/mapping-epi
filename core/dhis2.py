"""Rapprochement Mapping Épi × DHIS2 (ezd.snisrdc.com) : retrouver l'ID du mapping (N° EPID) dans la liste linéaire
MVE et compter les contacts enregistrés dans DHIS2 pour ce cas index.

Ce qui est lu (lecture seule, API analytics, mêmes programmes que les scripts extraction_linelist.py et
extraction_suivi_contacts.py) :
- liste linéaire MVE (programme wDFB7FFlYQM) : numéro EPID de l'alerte et classification finale ;
- suivi des contacts (programme wyLS271t8Id) : identifiant DHIS2 du contact et numéro EPID de son cas index.
Aucun nom, téléphone ni adresse n'est lu ni conservé : seulement des EPID et des nombres.

Le jeton personnel DHIS2 n'est jamais écrit dans le code ni dans les données : il vient de la variable
d'environnement DHIS2_TOKEN (sur le serveur : /etc/mapping-epi/dhis2.env, créé par « mapping-epi dhis2-jeton »).
Sans jeton, on peut téléverser les exports CSV / Excel (LINELIST_*.csv, SUIVI_CONTACTS_*.csv).
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from core.paths import data_dir

BASE = os.environ.get("DHIS2_BASE", "https://ezd.snisrdc.com/dhis/api")
PROG_LL = "wDFB7FFlYQM"          # MVE - Notification d'alerte et investigation de cas
PROG_CONTACTS = "wyLS271t8Id"    # MVE - Fiche d'identification et suivi individuel des contacts
EPID_LL = "otfO0yxrBj5"          # MVE-N-Numéro d'identification de l'alerte
CLASSIF_LL = "r7nrCHTBI5P.D6kduc7OZnS"   # MVE - Classification finale du cas (CC, CP, CS, NC)
EPID_CONTACT = "tBvV2SfZxOf"     # Numéro Epid - Alerte MVE (cas index du contact)
PAGE = 10000
PERIODE = "2026-01-01_2027-12-31"
CLASSIF = {"CC": "Confirmé", "CP": "Probable", "CS": "Suspect", "NC": "Non-cas"}

_VERROU = threading.Lock()
ETAT: Dict[str, object] = {"en_cours": False, "message": "", "erreur": ""}


# ------------------------------------------------------------------------------------------------ EPID
def cle_epid(s: Optional[str]) -> str:
    """Clé de rapprochement : majuscules, sans espaces, sans suffixe « -MVE », numéro sans zéros en tête.
    RDC-ITU-RWA-26-001058-MVE et rdc-itu-rwa-26-1058 donnent la même clé."""
    t = re.sub(r"\s+", "", str(s or "")).upper().replace("_", "-")
    t = re.sub(r"-?MVE$", "", t)
    parts = [p for p in t.split("-") if p]
    if not parts:
        return ""
    if parts[-1].isdigit():
        parts[-1] = str(int(parts[-1]))
    return "-".join(parts)


# ------------------------------------------------------------------------------------------------ stockage
def _fichier() -> Path:
    return data_dir() / "dhis2_concordance.json"


_CACHE: Dict[str, object] = {}


def charger() -> Optional[dict]:
    f = _fichier()
    try:
        cle = (str(f), f.stat().st_mtime_ns)
    except OSError:
        return None
    if _CACHE.get("cle") != cle:
        try:
            _CACHE.update(cle=cle, d=json.loads(f.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            return None
    return _CACHE["d"]


def _enregistrer(ll: Dict[str, str], contacts: Dict[str, int], source: str, n_contacts: int) -> dict:
    d = {"maj": datetime.now().isoformat(timespec="minutes"), "source": source, "ll": ll, "contacts": contacts,
         "n_ll": len(ll), "n_contacts": n_contacts, "n_cas_avec_contacts": len(contacts)}
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)
    return d


def _agreger(ll_rows: Iterable[Tuple[str, str]], ct_rows: Iterable[Tuple[str, str]]) -> Tuple[Dict[str, str], Dict[str, int], int]:
    rang = {"": 0, "NC": 1, "CS": 2, "CP": 3, "CC": 4}
    ll: Dict[str, str] = {}
    for epid, classif in ll_rows:
        k = cle_epid(epid)
        if k:
            c = (classif or "").strip().upper()
            c = c if c in CLASSIF else ""
            # une même alerte peut apparaître plusieurs fois : on garde la classification la plus forte
            if rang[c] >= rang.get(ll.get(k, ""), 0):
                ll[k] = c
    vus: Dict[str, set] = {}
    total = set()
    for uid, epid in ct_rows:
        k = cle_epid(epid)
        uid = (uid or "").strip()
        if k and uid:
            vus.setdefault(k, set()).add(uid)
            total.add(uid)
    return ll, {k: len(v) for k, v in vus.items()}, len(total)


# ------------------------------------------------------------------------------------------------ API
def jeton() -> str:
    return os.environ.get("DHIS2_TOKEN", "").strip()


def _get(path: str, params: List[Tuple[str, str]], tok: str) -> dict:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"ApiToken {tok}", "Accept": "application/json"})
    derniere = None
    for essai in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError("Jeton DHIS2 refusé (expiré ou sans droit de lecture).") from None
            derniere = f"erreur {e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            derniere = str(e)
        time.sleep(5 * (essai + 1))
    raise RuntimeError(f"DHIS2 ne répond pas ({derniere}).")


def _pages(prog: str, dims: List[str], headers: str, tok: str, etape: Callable[[str], None]) -> List[list]:
    base = [("dimension", "ou:USER_ORGUNIT")] + [("dimension", d) for d in dims]
    base += [("headers", headers), ("enrollmentDate", PERIODE), ("outputType", "ENROLLMENT"), ("pageSize", str(PAGE))]
    rows, page = [], 1
    while True:
        js = _get(f"/analytics/enrollments/query/{prog}.json", base + [("page", str(page))], tok)
        lot = js.get("rows", [])
        rows.extend(lot)
        etape(f"{len(rows)} lignes lues")
        if len(lot) < PAGE:
            return rows
        page += 1


def synchroniser_api(tok: Optional[str] = None, etape: Callable[[str], None] = lambda m: None) -> dict:
    tok = tok or jeton()
    if not tok:
        raise RuntimeError("Aucun jeton DHIS2 configuré sur ce serveur.")
    etape("Liste linéaire MVE…")
    ll = _pages(PROG_LL, [EPID_LL, CLASSIF_LL], f"{EPID_LL},{CLASSIF_LL}", tok, lambda m: etape("Liste linéaire : " + m))
    etape("Contacts…")
    ct = _pages(PROG_CONTACTS, [EPID_CONTACT], f"tei,{EPID_CONTACT}", tok, lambda m: etape("Contacts : " + m))
    a, b, n = _agreger(((r[0], r[1] if len(r) > 1 else "") for r in ll), ((r[0], r[1]) for r in ct if len(r) > 1))
    return _enregistrer(a, b, "API DHIS2", n)


def lancer_synchronisation() -> bool:
    """Synchronisation en arrière-plan (une à la fois). Renvoie False si une synchronisation tourne déjà."""
    with _VERROU:
        if ETAT["en_cours"]:
            return False
        ETAT.update(en_cours=True, message="Démarrage…", erreur="")

    def run():
        try:
            d = synchroniser_api(etape=lambda m: ETAT.update(message=m))
            ETAT.update(message=f"Terminé : {d['n_ll']} alertes, {d['n_contacts']} contacts.")
        except Exception as exc:                      # message affiché dans la page, jamais le jeton
            ETAT.update(erreur=str(exc), message="")
        finally:
            ETAT["en_cours"] = False
    threading.Thread(target=run, daemon=True).start()
    return True


# ------------------------------------------------------------------------------------------------ fichiers exportés
def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def _lire_tableau(path: Path, garder: Callable[[str], bool]):
    """Lit seulement les colonnes utiles (jamais les noms ni les téléphones)."""
    import csv
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        ws = load_workbook(str(path), read_only=True, data_only=True).worksheets[0]
        it = ws.iter_rows(values_only=True)
        head = [str(h or "") for h in next(it)]
        idx = [i for i, h in enumerate(head) if garder(h)]
        return [head[i] for i in idx], ([("" if r[i] is None else str(r[i])) for i in idx] for r in it)
    f = path.open(encoding="utf-8-sig", newline="")
    rd = csv.reader(f)
    head = next(rd)
    idx = [i for i, h in enumerate(head) if garder(h)]
    return [head[i] for i in idx], ([r[i] if i < len(r) else "" for i in idx] for r in rd)


def type_fichier(path: Path) -> str:
    head, _rows = _lire_tableau(path, lambda h: True)
    n = [_norm(h) for h in head]
    if any("NUMERO EPID ALERTE" in h for h in n) and any("IDENTIFIANT CONTACT" in h or h == "UID CONTACT" for h in n):
        return "contacts"
    if any("IDENTIFICATION DE L ALERTE" in h or "IDENTIFICATION DE LALERTE" in h for h in n):
        return "linelist"
    return ""


def importer_fichiers(chemins: List[Path]) -> dict:
    """LINELIST_*.csv / .xlsx et SUIVI_CONTACTS_*.csv / .xlsx : un des deux suffit, l'autre est repris de la
    dernière synchronisation."""
    prec = charger() or {}
    ll_rows: List[Tuple[str, str]] = []
    ct_rows: List[Tuple[str, str]] = []
    vus = set()
    for p in chemins:
        t = type_fichier(p)
        if t == "linelist":
            head, rows = _lire_tableau(p, lambda h: "IDENTIFICATION DE L" in _norm(h) and "ALERTE" in _norm(h)
                                       or "CLASSIFICATION FINALE" in _norm(h))
            ie = next(i for i, h in enumerate(head) if "ALERTE" in _norm(h))
            ic = next((i for i, h in enumerate(head) if "CLASSIFICATION" in _norm(h)), None)
            ll_rows += [(r[ie], r[ic] if ic is not None else "") for r in rows]
            vus.add("linelist")
        elif t == "contacts":
            head, rows = _lire_tableau(p, lambda h: "NUMERO EPID ALERTE" in _norm(h) or _norm(h) in ("UID CONTACT",)
                                       or "IDENTIFIANT CONTACT" in _norm(h))
            ie = next(i for i, h in enumerate(head) if "NUMERO EPID" in _norm(h))
            iu = next((i for i, h in enumerate(head) if _norm(h) == "UID CONTACT"), None)
            if iu is None:
                iu = next(i for i, h in enumerate(head) if "IDENTIFIANT CONTACT" in _norm(h))
            ct_rows += [(r[iu], r[ie]) for r in rows]
            vus.add("contacts")
        else:
            raise ValueError(f"Fichier non reconnu : {p.name} (attendu : LINELIST ou SUIVI_CONTACTS exporté de DHIS2).")
    ll, ct, n = _agreger(ll_rows, ct_rows)
    if "linelist" not in vus:
        ll = prec.get("ll", {})
    if "contacts" not in vus:
        ct, n = prec.get("contacts", {}), prec.get("n_contacts", 0)
    return _enregistrer(ll, ct, "Fichiers exportés de DHIS2", n)


# ------------------------------------------------------------------------------------------------ rapprochement
def rapprochement(case, d: Optional[dict] = None) -> dict:
    """Pour une fiche : retrouvée dans la linelist DHIS2 ? contacts mapping, contacts DHIS2, différence.
    Sans synchronisation, le nombre DHIS2 saisi à la main dans la fiche est utilisé (source « saisi »)."""
    vals = [g.nombre for g in case.contacts if g.nombre is not None]
    m = sum(vals) if vals else None
    k = cle_epid(case.code_cas)
    d = d if d is not None else charger()
    if d and k:
        trouve = k in d.get("ll", {}) or k in d.get("contacts", {})
        n = d.get("contacts", {}).get(k, 0) if trouve else None
        out = {"trouve": trouve, "classif": CLASSIF.get(d.get("ll", {}).get(k, ""), ""), "mapping": m,
               "dhis2": n, "source": "DHIS2"}
    else:
        n = case.contacts_dhis2_listes
        out = {"trouve": None, "classif": "", "mapping": m, "dhis2": n, "source": "saisi" if n is not None else ""}
    out["difference"] = (m - out["dhis2"]) if m is not None and out["dhis2"] is not None else None
    return out


# ------------------------------------------------------------------------------------------------ export
COLONNES_EXPORT = [("ID du cas (mapping)", 24), ("Province", 14), ("Zone de santé", 16), ("Aire de santé", 16),
                   ("Retrouvé dans la linelist DHIS2", 16), ("Classification DHIS2", 14),
                   ("Contacts déclarés dans le mapping", 16), ("Contacts retrouvés dans DHIS2", 16),
                   ("Différence (mapping − DHIS2)", 16), ("Statut", 30), ("Source du nombre DHIS2", 18)]


def export_xlsx(cases, path, perimetre: str = "") -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from core.coordination import statut_concordance
    from core.langue import tr, trf
    d = charger()
    wb = Workbook()
    ws = wb.active
    ws.title = tr("Concordance DHIS2")
    ws.append([tr("Concordance Mapping Épi × DHIS2 : contacts par cas index") + (f" · {perimetre}" if perimetre else "")
               + (trf(" · données DHIS2 du {date} ({source})", date=d["maj"].replace("T", " "), source=tr(d["source"])) if d else
                  tr(" · nombre DHIS2 saisi dans les fiches"))])
    ws["A1"].font = Font(bold=True, size=12, color="1F3A5F")
    ws.append([tr(n) for n, _w in COLONNES_EXPORT])
    for i, (_n, w) in enumerate(COLONNES_EXPORT, 1):
        cell = ws.cell(row=2, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3A5F")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[2].height = 44
    rouge, ambre = PatternFill("solid", fgColor="F6E1DE"), PatternFill("solid", fgColor="FBEFD5")
    n = 0
    for c in sorted(cases, key=lambda c: (c.province or "", c.zs or "", c.code_cas or "")):
        r = rapprochement(c, d)
        st = tr("Introuvable dans la linelist DHIS2") if r["trouve"] is False else statut_concordance(r["mapping"], r["dhis2"])[0]
        ws.append([c.code_cas, c.province, c.zs, c.aire_sante,
                   "" if r["trouve"] is None else tr("Oui" if r["trouve"] else "Non"), tr(r["classif"]) if r["classif"] else "",
                   r["mapping"], r["dhis2"], r["difference"], st,
                   {"DHIS2": tr("Synchronisation DHIS2"), "saisi": tr("Saisi dans la fiche")}.get(r["source"], "")])
        if r["trouve"] is False:
            ws.cell(row=ws.max_row, column=5).fill = rouge
        if r["difference"] and r["difference"] > 0:
            ws.cell(row=ws.max_row, column=9).fill = ambre
        n += 1
    ws.freeze_panes = "B3"
    ws.auto_filter.ref = f"A2:{get_column_letter(len(COLONNES_EXPORT))}{max(2, ws.max_row)}"
    wb.save(str(path))
    return n
