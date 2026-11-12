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
    global _CACHE
    _CACHE = None


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


def trouver_aire(province: str, zs: str, aire: str) -> Optional[dict]:
    from core.lieux import cle
    idx = charger()["index"]
    a = idx.get((cle(province), cle(zs), cle(aire)))
    if a:
        return a
    cz, ca = cle(zs), cle(aire)
    hits = [v for (p, z, x), v in idx.items() if z == cz and x == ca]
    return hits[0] if len(hits) == 1 else None
