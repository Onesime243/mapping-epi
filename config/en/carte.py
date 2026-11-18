"""Carte des cas : niveaux national, province, zone de santé (voir core/langue.py)."""

EN = {
    "Contours introuvables pour ce niveau.": "No outlines found for this level.",
    "République démocratique du Congo : cas par province": "Democratic Republic of the Congo: cases by province",
    "Province {p} : cas par zone de santé": "{p} province: cases by health zone",
    "Zone de santé {z} ({p}) : cas par aire de santé": "{z} health zone ({p}): cases by health area",
    "{n} cas placés": "{n} cases mapped",
    "couleur : délai depuis le dernier cas notifié": "colour: time since the last notified case",
    "{n} cas": "{n} cases", "aucun cas": "no cases",
    "dernier cas notifié il y a {j} j": "last case notified {j} days ago",
    "{n} cas, {d} décès": "{n} cases, {d} deaths",
    "dernier cas ≤ 7 j": "last case ≤ 7 days", "8 à 21 j": "8 to 21 days", "22 à 42 j": "22 to 42 days",
    "plus de 42 j": "over 42 days",
    "Contours : aires de santé GRID3 / CIESIN, simplifiés ; Mapping Épi":
        "Outlines: GRID3 / CIESIN health areas, simplified; Mapping Épi",
}

EN.update({
    "Niveau de la carte": "Map level", "RDC (nationale)": "DRC (national)", "Province": "Province",
    "Cliquez sur une province, puis sur une zone de santé, pour descendre d'un niveau.":
        "Click a province, then a health zone, to go down one level.",
    "Télécharger la carte (PNG)": "Download the map (PNG)",
    "Chaque cas est placé dans son aire de santé, ou au point GPS de la fiche. Fonctionne sans internet.":
        "Each case is placed in its health area, or at the record's GPS point. Works offline.",
    "Contours livrés avec l'outil : {p} provinces, {z} zones de santé, {a} aires de santé (GRID3 / CIESIN).":
        "Outlines shipped with the tool: {p} provinces, {z} health zones, {a} health areas (GRID3 / CIESIN).",
})
