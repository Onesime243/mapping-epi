# Mapping Épi — parcours épidémiologique des cas

Outil pour saisir l'investigation d'un cas (MVE, Marburg, Mpox, choléra…) et générer automatiquement le
**« Mapping complet – parcours épidémiologique »** : chronologie, lieux & expositions, contacts,
PCI / décontamination, actions immédiates — plus le réseau de contacts, la carte du parcours, la frise
temporelle et un tableau de bord multi-cas.

Deux façons de l'utiliser, **sur les mêmes données locales** :

| | Application de bureau | Version web |
|---|---|---|
| Pour qui | le poste de l'épidémiologiste | les agents de terrain (téléphone, tablette, PC) |
| Accès | directe | identifiant + mot de passe |
| Lancement | `python app.py` | `python serveur_web.py` ou menu « Version web ▾ » |
| Données | dossier local `donnees/` | le même dossier `donnees/` |

---

## 1. Installation (une seule fois)

Prérequis : **Python 3.11+** et **Visual Studio Code** (extension *Python*).

**macOS**
```bash
cd ~/Documents/mapping-epi
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Windows (PowerShell)**
```powershell
cd $HOME\Documents\mapping-epi
py -m venv .venv ; .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Dans VS Code : *Ouvrir le dossier* → `Python: Select Interpreter` → `.venv` → **F5** et choisir
« lancer l'application » ou « serveur web ».

---

## 2. Version web avec comptes utilisateurs

1. Dans l'application de bureau : **Utilisateurs…** → créez votre compte **administrateur**, puis un compte
   par agent (un mot de passe est proposé et copié dans le presse-papiers).
2. **Version web ▾ → Démarrer le serveur web**. Les adresses s'affichent, par exemple
   `http://192.168.1.25:8050`.
3. Les agents connectés au **même réseau (Wi-Fi, partage de connexion)** ouvrent cette adresse dans leur
   navigateur, se connectent, saisissent leurs cas et téléchargent le mapping.

Sans l'application de bureau : `python serveur_web.py` (au premier lancement, l'adresse ouvre la page de
création du compte administrateur).

- **Agent** : crée, modifie et télécharge **ses** cas uniquement.
- **Administrateur** : voit tous les cas, crée / désactive les comptes, réinitialise les mots de passe.
- Mots de passe chiffrés (PBKDF2-SHA256), sessions de 12 h, protection CSRF, blocage après 8 essais ratés.
- Le serveur tourne sur votre ordinateur : **aucune donnée ne part sur internet**. Pour un accès depuis
  l'extérieur du réseau, il faudrait l'héberger sur un serveur (non activé ici).

Téléchargements web : PNG HD / 4K, PDF 16:9 / A4, SVG, PowerPoint modifiable, rapport complet (PDF ou
PowerPoint), Excel, JSON.

---

## 2 bis. Mise en ligne sur internet (Hetzner)

Pour que les zones et aires de santé saisissent leurs cas depuis n'importe où, l'application s'installe
sur un petit serveur Hetzner (≈ 6–7 $/mois) en **une commande** :

```bash
curl -fsSL https://raw.githubusercontent.com/Onesime243/mapping-epi/main/deploy/install.sh | bash
```

Guide pas à pas : [deploy/GUIDE_HETZNER.md](deploy/GUIDE_HETZNER.md) — HTTPS automatique, pare-feu,
sauvegardes quotidiennes, comptes par agent, commande `mapping-epi` pour l'administration.

---

## 3. Où sont les données ?

Tout reste **en local** dans le dossier `donnees/` du projet (bouton « Dossier de données ») :

```
donnees/
  mapping_epi.sqlite     cas, historique des versions, comptes
  cas/<id>.json          copie lisible de chaque fiche (sauvegarde)
  pyramide_perso.csv     aires de santé ajoutées à la saisie
  secret.key             clé de session de la version web
```
- Ce dossier n'est **jamais** envoyé sur GitHub (`.gitignore`).
- Pour le placer ailleurs (disque externe, dossier synchronisé) : variable d'environnement
  `MAPPING_EPI_DONNEES=/chemin/vers/dossier`.
- La base de la version 1.0 (`data/`) est reprise automatiquement au premier lancement.
- Sauvegarde : copier le dossier `donnees/`.

---

## 4. Listes Province → Zone de santé → Aire de santé (RDC)

Les champs Province, ZS et AS sont des **listes en cascade** avec recherche : 26 provinces, 521 zones de santé,
7 098 aires de santé, issues du jeu GRID3 / HDX *DRC Health Zone and Health Area boundaries* (2022),
orthographes harmonisées (`config/rdc_pyramide.csv`). Une aire de santé absente de la liste peut être
saisie : elle est mémorisée et proposée ensuite (`donnees/pyramide_perso.csv`).

---

## 5. Fonctions principales

- Formulaire en 8 onglets ; aperçu en direct ; sauvegarde automatique ; versions (Ctrl/Cmd + S).
- Calendriers à partir de **2026**, ouverts sur le mois en cours ; clic droit pour effacer une date.
- Thèmes **clair**, **sombre** ou **comme le système** (bureau et web).
- Fenêtres automatiques depuis J0 (exposition J-21 → J-2, contagiosité jusqu'à l'inhumation pour la MVE ;
  paramètres dans `config/diseases.yaml`), jours relatifs sur chaque étape.
- Risque suggéré par règles explicites (règle visible en info-bulle), risque global, contrôles de cohérence,
  trous de chronologie, actions suggérées, fin du suivi des contacts, délai laboratoire.
- Les inconnues restent « ? » — jamais 0.
- Exports : PNG HD / 4K, PDF, SVG, **PowerPoint modifiable**, rapport complet, Excel, JSON.

---

## 6. Tests
```bash
python -m pytest -q tests
```

## 7. Architecture
```
app.py                 application de bureau (PySide6)
serveur_web.py         version web (Flask + waitress)
config/                thème, maladies, pyramide sanitaire RDC
core/                  modèles, règles, stockage, comptes, pyramide, dossier de données
render/                mapping HTML, réseau, carte, frise, multi-cas, PowerPoint
ui/                    interface de bureau (thèmes, formulaires, exports, utilisateurs)
web/                   serveur, pages, éditeur JavaScript, rendu PNG/PDF
sample_data/           cas de démonstration fictif (lieux, personnes et dates inventés)
tests/                 pytest
```

Police : Inter (SIL Open Font License). Données géographiques : GRID3 / HDX.
