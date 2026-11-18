"""Limites des aires de santé (GeoPackage GRID3 / CIESIN) pour la carte des cas, sans internet.

Un fichier .gpkg (couche de polygones, colonnes Province, Zone, Aire, en WGS 84) est converti une fois en un
fichier léger : contours simplifiés (≈ 150 m), centre de chaque aire, limites des zones de santé reconstituées
(bords entre aires de zones différentes). Seuls les noms et les contours sont gardés.

Fichiers lus : config/geo/*.json (livrés avec l'outil) puis <données>/geo/*.json (importés depuis la page Carte
ou l'application de bureau). Aucune bibliothèque externe : lecture directe du GeoPackage (SQLite + WKB).
"""
from __future__ import annotations

import json
import sqlite3
import struct
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
TOLERANCE = 0.0014           # degrés ≈ 150 m
Ring = List[Tuple[float, float]]
_CACHE: Optional[dict] = None


# ---------------------------------------------------------------------------
# lecture du GeoPackage
# ---------------------------------------------------------------------------
def _wkb_polygones(w: bytes) -> List[List[Ring]]:
    """WKB (Polygon / MultiPolygon, 2D ou 3D) → liste de polygones (liste d'anneaux (lon, lat))."""
    pos = 0

    def u32(o):
        return struct.unpack_from(o + "I", w, pos)[0]

    def geom():
        nonlocal pos
        o = "<" if w[pos] == 1 else ">"
        pos += 1
        t = struct.unpack_from(o + "I", w, pos)[0]
        pos += 4
        dims = 3 if (t & 0x80000000 or (t % 10000) // 1000 in (1, 2)) else 2
        if (t % 10000) // 1000 == 3:
            dims = 4
        base = (t & 0x0FFFFFFF) % 1000
        if base == 3:
            n = struct.unpack_from(o + "I", w, pos)[0]
            pos += 4
            rings = []
            for _ in range(n):
                k = struct.unpack_from(o + "I", w, pos)[0]
                pos += 4
                vals = struct.unpack_from(o + "d" * (k * dims), w, pos)
                pos += 8 * k * dims
                rings.append([(vals[i], vals[i + 1]) for i in range(0, len(vals), dims)])
            return [rings]
        if base == 6:
            n = struct.unpack_from(o + "I", w, pos)[0]
            pos += 4
            out = []
            for _ in range(n):
                out += geom()
            return out
        raise ValueError(f"géométrie non prise en charge (type WKB {t})")
    return geom()


def _gpkg_geom(blob: bytes) -> List[List[Ring]]:
    if blob[:2] != b"GP":
        return _wkb_polygones(blob)
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((blob[3] >> 1) & 7, 0)
    return _wkb_polygones(blob[8 + env:])


def _colonne(cols: Iterable[str], *noms: str) -> Optional[str]:
    low = {c.lower(): c for c in cols}
    for n in noms:
        if n in low:
            return low[n]
    return None


def lire_gpkg(path: Path | str) -> List[dict]:
    db = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)
    try:
        couches = db.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'").fetchall()
        if not couches:
            raise ValueError("aucune couche de polygones dans ce GeoPackage")
        out = []
        for (t,) in couches:
            gcol = db.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name=?", (t,)).fetchone()[0]
            cols = [r[1] for r in db.execute(f'PRAGMA table_info("{t}")')]
            cp = _colonne(cols, "province", "prov", "nom_prov")
            cz = _colonne(cols, "zone", "zone_sante", "zs", "nom_zs", "zonesante")
            ca = _colonne(cols, "aire", "aire_sante", "as", "nom_as", "airesante")
            if not (cz and ca):
                continue
            sel = ", ".join(f'"{c}"' for c in (cp or cz, cz, ca, gcol))
            for prov, zs, aire, blob in db.execute(f'SELECT {sel} FROM "{t}"'):
                if blob and zs and aire:
                    out.append({"p": (prov if cp else "") or "", "z": zs, "a": aire, "polys": _gpkg_geom(blob)})
        if not out:
            raise ValueError("colonnes Zone et Aire introuvables (noms attendus : Province, Zone, Aire)")
        return out
    finally:
        db.close()


# ---------------------------------------------------------------------------
# simplification
# ---------------------------------------------------------------------------
def _dp(pts: Ring, tol: float) -> Ring:
    """Douglas-Peucker itératif."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    pile = [(0, len(pts) - 1)]
    t2 = tol * tol
    while pile:
        a, b = pile.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        n2 = dx * dx + dy * dy
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if n2 == 0:
                d = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / n2))
                d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d > best:
                best, idx = d, i
        if best > t2:
            keep[idx] = True
            pile += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def _aire_et_centre(ring: Ring) -> Tuple[float, float, float]:
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        f = x1 * y2 - x2 * y1
        a += f
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    if abs(a) < 1e-12:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return a / 2, cx / (3 * a), cy / (3 * a)


def _r(v: float) -> float:
    return round(v, 4)


def convertir(features: List[dict], tol: float = TOLERANCE) -> dict:
    aires = []
    aretes: Dict[Tuple, set] = defaultdict(set)
    for f in features:
        polys, surf, sx, sy = [], 0.0, 0.0, 0.0
        for poly in f["polys"]:
            anneaux = []
            for k, ring in enumerate(poly):
                pts = [(round(x, 6), round(y, 6)) for x, y in ring]
                if k == 0:
                    a, cx, cy = _aire_et_centre(pts)
                    surf += abs(a)
                    sx += abs(a) * cx
                    sy += abs(a) * cy
                    for p, q in zip(pts, pts[1:]):
                        if p != q:
                            aretes[(p, q) if p < q else (q, p)].add(f["z"])
                s = _dp(pts, tol)
                if len(s) < 4 and k == 0:         # petite aire (ville) : moins simplifiée
                    s = _dp(pts, tol / 20)
                    if len(s) < 4:
                        s = pts
                if len(s) >= 4:
                    anneaux.append([[_r(x), _r(y)] for x, y in s])
            if anneaux:
                polys.append(anneaux)
        if not polys:
            continue
        allx = [p[0] for poly in polys for p in poly[0]]
        ally = [p[1] for poly in polys for p in poly[0]]
        centre = [_r(sx / surf), _r(sy / surf)] if surf else [_r(sum(allx) / len(allx)), _r(sum(ally) / len(ally))]
        aires.append({"p": f["p"], "z": f["z"], "a": f["a"], "c": centre, "polys": polys,
                      "bb": [min(allx), min(ally), max(allx), max(ally)]})
    # limites de zones : arêtes partagées par deux zones différentes, ou bord extérieur (une seule aire)
    compte = defaultdict(int)
    for f in features:
        for poly in f["polys"]:
            pts = [(round(x, 6), round(y, 6)) for x, y in poly[0]]
            for p, q in zip(pts, pts[1:]):
                if p != q:
                    compte[(p, q) if p < q else (q, p)] += 1
    bord = [e for e, zs in aretes.items() if len(zs) > 1 or compte[e] == 1]
    lignes = [[[_r(x), _r(y)] for x, y in _dp(l, tol)] for l in _chainer(bord)]
    provinces = sorted({a["p"] for a in aires if a["p"]})
    return {"format": "mapping-epi-geo", "version": 1, "provinces": provinces, "aires": aires,
            "limites_zs": [l for l in lignes if len(l) >= 2],
            "source": "contours des aires de santé (GeoPackage importé), simplifiés à ≈ 150 m"}


def _chainer(aretes: List[Tuple]) -> List[Ring]:
    voisins: Dict[Tuple, List[Tuple]] = defaultdict(list)
    for p, q in aretes:
        voisins[p].append(q)
        voisins[q].append(p)
    vues = set()
    lignes = []

    def cle(p, q):
        return (p, q) if p < q else (q, p)
    for p, q in aretes:
        if cle(p, q) in vues:
            continue
        vues.add(cle(p, q))
        ligne = [p, q]
        for sens in (0, 1):
            while True:
                bout = ligne[-1] if sens == 0 else ligne[0]
                suite = [n for n in voisins[bout] if cle(bout, n) not in vues]
                if len(voisins[bout]) != 2 or not suite:
                    break
                n = suite[0]
                vues.add(cle(bout, n))
                if sens == 0:
                    ligne.append(n)
                else:
                    ligne.insert(0, n)
        lignes.append(ligne)
    return lignes


# ---------------------------------------------------------------------------
# niveaux : contours des provinces et des zones de santé reconstitués à partir des aires
# ---------------------------------------------------------------------------
TOL_PROVINCE = 0.01          # ≈ 1 km : carte nationale
TOL_ZONE = 0.003             # ≈ 300 m : carte d'une province


def _anneaux_groupe(features: List[dict], tol: float) -> List[Ring]:
    """Contour d'un groupe d'aires (province ou zone) : arêtes qui n'appartiennent qu'à une aire du groupe,
    chaînées en anneaux fermés puis simplifiées. Un trou (zone enclavée) donne un anneau de plus (règle evenodd)."""
    cpt: Dict[Tuple, int] = defaultdict(int)
    for f in features:
        for poly in f["polys"]:
            pts = [(round(x, 6), round(y, 6)) for x, y in poly[0]]
            for a, b in zip(pts, pts[1:]):
                if a != b:
                    cpt[(a, b) if a < b else (b, a)] += 1
    voisins: Dict[Tuple, List[Tuple]] = defaultdict(list)
    for (a, b), n in cpt.items():
        if n == 1:
            voisins[a].append(b)
            voisins[b].append(a)
    vues = set()
    anneaux: List[Ring] = []
    for a0 in list(voisins):
        for b0 in voisins[a0]:
            e0 = (a0, b0) if a0 < b0 else (b0, a0)
            if e0 in vues:
                continue
            vues.add(e0)
            ring, prec, cour = [a0, b0], a0, b0
            while cour != a0:
                suite = None
                for n in voisins[cour]:
                    e = (cour, n) if cour < n else (n, cour)
                    if e not in vues:
                        suite = n
                        vues.add(e)
                        break
                if suite is None:
                    break
                prec, cour = cour, suite
                ring.append(cour)
            if len(ring) >= 4 and abs(_aire_et_centre(ring)[0]) > 1e-7:
                s = _dp(ring, tol)
                if len(s) < 4:
                    s = _dp(ring, tol / 10)
                if len(s) >= 4:
                    anneaux.append([[_r(x), _r(y)] for x, y in s])
    return anneaux


def _resume(features: List[dict]) -> Tuple[List[float], List[float]]:
    """Centre (pondéré par la surface) et emprise d'un groupe d'aires."""
    surf = sx = sy = 0.0
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for f in features:
        for poly in f["polys"]:
            a, cx, cy = _aire_et_centre(poly[0])
            surf += abs(a)
            sx += abs(a) * cx
            sy += abs(a) * cy
            for x, y in poly[0]:
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    return [_r(sx / surf), _r(sy / surf)] if surf else [_r((x0 + x1) / 2), _r((y0 + y1) / 2)], \
        [_r(x0), _r(y0), _r(x1), _r(y1)]


def construire_niveaux(features: List[dict], dest: Path, journal=print) -> dict:
    """Écrit dans `dest` : rdc_niveaux.json (contours des provinces et des zones de santé) et un fichier
    aires_<province>.json par province (contours des aires, format habituel). Retourne un bilan."""
    from core.lieux import cle
    dest.mkdir(parents=True, exist_ok=True)
    par_prov: Dict[str, List[dict]] = defaultdict(list)
    for f in features:
        par_prov[f["p"] or "?"].append(f)
    provinces, zones, n_aires = [], [], 0
    for p in sorted(par_prov):
        fs = par_prov[p]
        c, bb = _resume(fs)
        provinces.append({"p": p, "c": c, "bb": bb, "r": _anneaux_groupe(fs, TOL_PROVINCE),
                          "fichier": f"aires_{cle(p).replace(' ', '-')}.json"})
        par_zs: Dict[str, List[dict]] = defaultdict(list)
        for f in fs:
            par_zs[f["z"]].append(f)
        for z in sorted(par_zs):
            cz, bbz = _resume(par_zs[z])
            zones.append({"p": p, "z": z, "c": cz, "bb": bbz, "r": _anneaux_groupe(par_zs[z], TOL_ZONE),
                          "n_aires": len(par_zs[z])})
        data = convertir(fs)
        data["limites_zs"] = []          # remplacées par les contours des zones (rdc_niveaux.json)
        (dest / provinces[-1]["fichier"]).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                                                      encoding="utf-8")
        n_aires += len(data["aires"])
        journal(f"{p} : {len(par_zs)} zones, {len(data['aires'])} aires")
    niveaux = {"format": "mapping-epi-niveaux", "version": 1, "provinces": provinces, "zones": zones,
               "source": "aires de santé GRID3 / CIESIN ; provinces et zones reconstituées à partir des aires"}
    (dest / "rdc_niveaux.json").write_text(json.dumps(niveaux, ensure_ascii=False, separators=(",", ":")),
                                           encoding="utf-8")
    vider_cache()
    return {"provinces": len(provinces), "zones": len(zones), "aires": n_aires}


# ---------------------------------------------------------------------------
# fichiers et chargement
# ---------------------------------------------------------------------------
def dossier_donnees() -> Path:
    from core.paths import data_dir
    d = data_dir() / "geo"
    d.mkdir(exist_ok=True)
    return d


def importer_gpkg(path: Path | str, dest: Optional[Path] = None) -> Tuple[Path, int]:
    """Convertit un GeoPackage et l'enregistre (dossier de données par défaut). (fichier, nombre d'aires)."""
    from core.lieux import cle
    data = convertir(lire_gpkg(path))
    nom = "_".join(cle(p).replace(" ", "-") for p in data["provinces"]) or Path(path).stem
    out = (dest or dossier_donnees()) / f"aires_{nom}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    vider_cache()
    return out, len(data["aires"])


def vider_cache() -> None:
    global _CACHE, _NIVEAUX, _IMPORTES
    _CACHE = _NIVEAUX = _IMPORTES = None
    _PAR_PROVINCE.clear()


def charger() -> dict:
    """Toutes les aires connues : {'aires': [...], 'limites_zs': [...], 'provinces': [...]}."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    aires, limites, provinces = {}, [], set()
    fichiers = sorted((ROOT / "config" / "geo").glob("*.json"))
    try:
        fichiers += sorted(dossier_donnees().glob("*.json"))
    except Exception:
        pass
    from core.lieux import cle
    for f in fichiers:          # un fichier importé remplace les aires de même nom d'un fichier livré
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("format") != "mapping-epi-geo":
            continue
        for a in d.get("aires", []):
            aires[(cle(a["p"]), cle(a["z"]), cle(a["a"]))] = a
        limites += d.get("limites_zs", [])
        provinces |= set(d.get("provinces", []))
    _CACHE = {"aires": list(aires.values()), "limites_zs": limites, "provinces": sorted(provinces),
              "index": aires}
    return _CACHE


# ---------------------------------------------------------------------------
# chargement par niveau (léger : une province à la fois)
# ---------------------------------------------------------------------------
_NIVEAUX: Optional[dict] = None
_PAR_PROVINCE: Dict[str, List[dict]] = {}
_IMPORTES: Optional[Dict[str, List[dict]]] = None


def niveaux() -> dict:
    """Contours des provinces et des zones de santé (rdc_niveaux.json) ; vide si absent."""
    global _NIVEAUX
    if _NIVEAUX is None:
        d = {"provinces": [], "zones": []}
        for f in [ROOT / "config" / "geo" / "rdc_niveaux.json"] + _fichiers_donnees("rdc_niveaux.json"):
            try:
                x = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if x.get("format") == "mapping-epi-niveaux":
                d = x
        _NIVEAUX = d
    return _NIVEAUX


def _fichiers_donnees(motif: str) -> List[Path]:
    try:
        return sorted(dossier_donnees().glob(motif))
    except Exception:
        return []


def _importes() -> Dict[str, List[dict]]:
    """Aires des fichiers importés depuis la page Carte (dossier de données), par province."""
    global _IMPORTES
    if _IMPORTES is None:
        from core.lieux import cle
        out: Dict[str, List[dict]] = defaultdict(list)
        for f in _fichiers_donnees("aires_*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if d.get("format") == "mapping-epi-geo":
                for a in d.get("aires", []):
                    out[cle(a["p"])].append(a)
        _IMPORTES = dict(out)
    return _IMPORTES


def aires_province(province: str) -> List[dict]:
    """Contours des aires de santé d'une province (fichier livré, remplacé aire par aire par un import)."""
    from core.lieux import cle
    k = cle(province or "")
    if not k:
        return []
    if k not in _PAR_PROVINCE:
        aires: Dict[Tuple, dict] = {}
        f = ROOT / "config" / "geo" / f"aires_{k.replace(' ', '-')}.json"
        if f.exists():
            try:
                for a in json.loads(f.read_text(encoding="utf-8")).get("aires", []):
                    aires[(cle(a["z"]), cle(a["a"]))] = a
            except Exception:
                pass
        for a in _importes().get(k, []):
            aires[(cle(a["z"]), cle(a["a"]))] = a
        _PAR_PROVINCE[k] = list(aires.values())
    return _PAR_PROVINCE[k]


def provinces_de_zone(zs: str) -> List[str]:
    from core.lieux import cle
    cz = cle(zs or "")
    return [z["p"] for z in niveaux()["zones"] if cle(z["z"]) == cz]


def trouver_zone(province: str, zs: str) -> Optional[dict]:
    from core.lieux import cle
    cp, cz = cle(province or ""), cle(zs or "")
    hits = [z for z in niveaux()["zones"] if cle(z["z"]) == cz and (not cp or cle(z["p"]) == cp)]
    return hits[0] if len(hits) == 1 else None


def trouver_aire(province: str, zs: str, aire: str) -> Optional[dict]:
    from core.lieux import cle
    cz, ca = cle(zs or ""), cle(aire or "")
    provs = [province] if province else []
    provs += [p for p in provinces_de_zone(zs) if cle(p) != cle(province or "")]
    if not provs:          # anciens fichiers importés sans contours de niveaux
        provs = list(_importes())
    for p in provs:
        for a in aires_province(p):
            if cle(a["z"]) == cz and cle(a["a"]) == ca:
                return a
    return None
