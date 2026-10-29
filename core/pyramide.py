"""Pyramide sanitaire de la RDC : Province → Zone de santé → Aire de santé.

Référence : config/rdc_pyramide.csv (26 provinces, ~520 zones de santé,
~7 100 aires de santé) construite à partir du jeu GRID3 / HDX
« DRC Health Zone and Health Area boundaries » (mise à jour 2022),
orthographes harmonisées.

Les aires de santé saisies à la main et absentes de la référence sont
mémorisées dans <données>/pyramide_perso.csv et proposées ensuite.
"""
from __future__ import annotations

import csv
import threading
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "config" / "rdc_pyramide.csv"
_lock = threading.Lock()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").replace("-", " ").split())


class Pyramide:
    def __init__(self, ref: Path = REF, perso: Optional[Path] = None):
        if perso is None:
            from core.paths import data_dir
            perso = data_dir() / "pyramide_perso.csv"
        self.perso = Path(perso)
        self.tree: Dict[str, Dict[str, set]] = defaultdict(lambda: defaultdict(set))
        self._load(ref)
        if self.perso.exists():
            self._load(self.perso)

    def _load(self, path: Path):
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f, delimiter=";"):
                p, z, a = r["province"].strip(), r["zone_sante"].strip(), r["aire_sante"].strip()
                if not p:
                    continue
                zs = self.tree[p]
                if z:
                    zs[z]
                    if a:
                        zs[z].add(a)

    # -- lecture ------------------------------------------------------------
    def provinces(self) -> List[str]:
        return sorted(self.tree, key=norm)

    def _match(self, keys, value: str) -> Optional[str]:
        n = norm(value)
        for k in keys:
            if norm(k) == n:
                return k
        return None

    def zones(self, province: str = "") -> List[str]:
        if province:
            p = self._match(self.tree, province)
            return sorted(self.tree[p], key=norm) if p else []
        return sorted({z for p in self.tree.values() for z in p}, key=norm)

    def aires(self, province: str = "", zone: str = "") -> List[str]:
        out = set()
        for p, zs in self.tree.items():
            if province and norm(p) != norm(province):
                continue
            for z, aa in zs.items():
                if zone and norm(z) != norm(zone):
                    continue
                out |= aa
        return sorted(out, key=norm)

    def province_of(self, zone: str) -> Optional[str]:
        hits = [p for p, zs in self.tree.items() if self._match(zs, zone)]
        return hits[0] if len(hits) == 1 else None

    def canonical(self, province: str, zone: str = "", aire: str = "") -> tuple:
        """Retourne l'orthographe de référence (ou la saisie si inconnue)."""
        p = self._match(self.tree, province) or province
        z = self._match(self.tree.get(p, {}), zone) or zone if zone else zone
        a = aire
        if aire and p in self.tree and z in self.tree[p]:
            a = self._match(self.tree[p][z], aire) or aire
        return p, z, a

    def as_dict(self) -> dict:
        """Structure compacte pour la version web : {province: {zs: [as…]}}."""
        return {p: {z: sorted(a, key=norm) for z, a in sorted(zs.items(), key=lambda kv: norm(kv[0]))}
                for p, zs in sorted(self.tree.items(), key=lambda kv: norm(kv[0]))}

    # -- ajout ---------------------------------------------------------------
    def remember(self, province: str, zone: str, aire: str = "") -> bool:
        """Mémorise une ZS / AS saisie absente de la référence. Retourne True si ajoutée."""
        province, zone, aire = province.strip(), zone.strip(), aire.strip()
        if not province or not zone:
            return False
        p = self._match(self.tree, province)
        if not p:
            return False                     # les provinces sont fixes
        z = self._match(self.tree[p], zone)
        if z and (not aire or self._match(self.tree[p][z], aire)):
            return False
        with _lock:
            new = not self.perso.exists()
            self.perso.parent.mkdir(parents=True, exist_ok=True)
            with open(self.perso, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f, delimiter=";")
                if new:
                    w.writerow(["province", "zone_sante", "aire_sante"])
                w.writerow([p, z or zone, aire])
        self.tree[p][z or zone]
        if aire:
            self.tree[p][z or zone].add(aire)
        return True


_SINGLETON: Optional[Pyramide] = None


def get() -> Pyramide:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = Pyramide()
    return _SINGLETON
