# Mapping Épi : parcours épidémiologique des cas

Outil pour saisir l'investigation d'un cas (MVE, Marburg, Mpox, choléra…) et générer automatiquement le
**« Mapping complet – parcours épidémiologique »** : chronologie, lieux & expositions, contacts,
PCI / décontamination, actions immédiates, plus le réseau de contacts, la carte du parcours, la frise
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

Chaque compte a un **niveau** de la pyramide sanitaire (page « Utilisateurs », ou `mapping-epi niveau IDENT` sur le
serveur ; règles dans `core/access.py`) :

| Niveau | Voit | Corrige |
|---|---|---|
| Aire de santé | ses propres cas | ses propres cas |
| Zone de santé | tous les cas de sa ZS (dont ceux de ses AS) | ses cas et ceux des comptes AS / ZS de sa zone |
| Provincial | tous les cas de sa province | ses propres cas (le reste en lecture seule) |
| National | tous les cas | ses propres cas (le reste en lecture seule) |
| **Administrateur** | tout | tout, plus la création / désactivation des comptes et des mots de passe |

Un cas appartient à une ZS / province par sa localisation **ou** par le compte qui l'a créé. Les comptes créés
avant les niveaux restent « Aire de santé » (leurs propres cas), comme avant.
La liste des cas se trie (clic sur un titre de colonne : J0, création, modification, ZS, AS…). Menu **Analyses** :
chaînes de transmission (à partir de l'« ID du cas source » de chaque fiche) et lieux fréquentés / lieux communs
(date de passage de chaque cas, contagieux ou dans sa fenêtre d'exposition), limités au périmètre du compte.
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

Guide pas à pas : [deploy/GUIDE_HETZNER.md](deploy/GUIDE_HETZNER.md) : HTTPS automatique, pare-feu,
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
7 101 aires de santé, issues du jeu GRID3 / HDX *DRC Health Zone and Health Area boundaries* (2022),
orthographes harmonisées (`config/rdc_pyramide.csv`). Une aire de santé absente de la liste peut être
saisie : elle est mémorisée et proposée ensuite (`donnees/pyramide_perso.csv`).

---

## 5. Fonctions principales

- Formulaire en 8 onglets ; aperçu en direct ; sauvegarde automatique ; versions (Ctrl/Cmd + S).
- Calendriers à partir de **2026**, ouverts sur le mois en cours ; clic droit pour effacer une date.
- Thèmes **clair**, **sombre** ou **comme le système** (bureau et web).
- **Phases de la maladie** (MVE / Marburg) datées pour chaque cas : point d'infection estimé (J-21 → J-2),
  incubation, phase sèche (dès J0, date **rapportée** par l'équipe, jamais recalculée) et phase humide
  (détectée dans la chronologie : diarrhée, vomissements, saignements… ; sinon estimée à J+4).
- **ID du cas alphanumérique** (ex. N° EPID) affiché sur tous les visuels.
- Symptômes **groupés par phase** (sèche, humide, hémorragiques, autres) + ajout de symptômes absents de la liste.
- Actions séparées : **à réaliser immédiatement** / **déjà réalisées**.
- **Administrateurs** : tous les cas de tous les comptes (filtres compte / province / ZS / AS) et menu
  **Lieux fréquentés** (par zone ou par aire de santé) : classement des lieux fréquentés par plusieurs cas.
- Statut **Contact connu / Contact connu suivi / Non contact** affiché sur le mapping.
- Fenêtres automatiques depuis J0 (exposition J-21 → J-2, contagiosité jusqu'à l'inhumation pour la MVE ;
  paramètres dans `config/diseases.yaml`), jours relatifs sur chaque étape.
- Risque suggéré par règles explicites (règle visible en info-bulle), risque global, contrôles de cohérence,
  trous de chronologie, actions suggérées, fin du suivi des contacts, délai laboratoire.
- Les inconnues restent « ? », jamais 0.
- Exports : PNG HD / 4K, PDF, SVG, **PowerPoint modifiable**, rapport complet, Excel, JSON.

---

## 5 bis. J0, phases, risque et indicateurs (remarques de la présentation)

- **J0** : on précise la **phase des premiers signes rapportés**. Phase sèche (fièvre, fatigue, douleurs) :
  J0 = date − 3 j ; phase humide (vomissements, diarrhée) : − 7 j ; phase critique (saignements, confusion, choc) :
  − 16 j (`config/diseases.yaml`, `phases_jours`). Phases affichées : sèche J0–J3, humide J4–J7, critique J7–J16.
- **Risque** d'une étape : 1. état du cas (incubation non contagieuse, phase humide +1, phase critique très élevé,
  si la phase est documentée) ; 2. mode de transmission (corps, liquides, sans PCI, sécurisé) ; 3. état des contacts
  dans le risque global (phase humide / critique sans contacts listés : très élevé ; non contact : +1).
- **Contact connu** : pas d'estimation de l'exposition ; date du dernier contact avec le cas source, sinon période
  contagieuse du cas source enregistré, sinon « à rechercher ».
- **Fiche** : date de notification (écart avec le J0 sur le mapping), vacciné, agent de santé (PPL), « État »
  (ancien « Issue », encore accepté à l'import). Les champs indispensables vides sont listés en haut de la fiche.
- **Analyses → Catégories des ZS, délais et incubation** : catégorie de chaque ZS selon les jours depuis le dernier
  cas notifié (`config/categories_zs.yaml`, seuils à valider), alertes « nouveau foyer possible », délais
  début → notification → confirmation, incubation observée et intervalle sériel.
- **Comptes** : le compte `adminone` ne peut être modifié ou supprimé que par lui-même ; il peut supprimer tout compte.
  Les administrateurs et les comptes nationaux peuvent supprimer des comptes ; chaque suppression est conservée dans
  l'historique (page Utilisateurs) et les fiches du compte sont gardées.

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

## Crédits

Système de gestion de l’incident, **SGI-RDC**, avec l’appui de **UMIE-INRB**.
Équipe de développement : Onesime Mbulayi et al.
Pour tout contact : [mbonesime@gmail.com](mailto:mbonesime@gmail.com), [dav.ebengo@umie-inrb.org](mailto:dav.ebengo@umie-inrb.org)

Police : Inter (SIL Open Font License). Données géographiques : GRID3 / HDX.

## Installateurs Windows et Mac (sans connexion)

L'application de bureau s'installe comme un logiciel ordinaire et fonctionne sans internet.

- **Windows** : `MappingEpi-<version>-Windows-Installation.exe` (assistant d'installation, menu Démarrer,
  icône du Bureau, désinstallation ; aucun droit administrateur nécessaire).
- **Mac** : `MappingEpi-<version>-Mac-arm64.dmg` (Apple M1 à M4) ou `Mac-x86_64.dmg` (Intel).

Les données de la version installée sont dans `%LOCALAPPDATA%\Mapping Epi\donnees` (Windows) ou
`~/Library/Application Support/Mapping Epi/donnees` (Mac) ; mises à jour et désinstallation ne les touchent pas.
Mode d'emploi pour les utilisateurs : `packaging/LISEZMOI-installation.txt`.

Construction :
- **sur GitHub** (Windows et Mac) : onglet *Actions* > *Installateurs* > *Run workflow*, ou étiquette
  `git tag v1.0.0 && git push origin v1.0.0` (publie une *Release* avec les installateurs) ;
- **sur un Mac** : `bash packaging/construire_mac.sh` ;
- **sur un PC Windows** : `packaging\construire_windows.bat` (Python et Inno Setup 6 installés).

La version est dans `packaging/VERSION`. Les installateurs ne sont pas signés : Windows (SmartScreen) et macOS
(Gatekeeper) demandent une confirmation au premier lancement, expliquée dans le mode d'emploi.

## Riposte et données (menus « Riposte ▾ » et « Données ▾ »)

Fonctions ajoutées sans toucher au mapping, aux comptes ni aux fiches existantes (calculs en lecture seule).

- **Indicateurs clés et courbe épidémique** (`/riposte/indicateurs`) : nouveaux cas déjà connus comme contacts,
  cas sans lien épidémiologique, délai début des symptômes → isolement (1re hospitalisation de la chronologie),
  décès communautaires, enterrements dignes et sécurisés, contacts suivis, agents de santé, vaccinés, complétude ;
  courbe par semaine du J0 retenu et par ZS. Les valeurs non renseignées sont exclues et comptées à part ;
  les cibles sont indicatives (`core/riposte.py`).
- **Suivi des actions** (`/riposte/actions`) : actions de l'onglet Actions de toutes les fiches, en retard d'abord.
- **Liste des cas (Excel)** et **rapport de situation (Word)** générés à partir des fiches du périmètre du compte.
- **Paquet de fiches** (`/donnees`, et menu Riposte de l'application de bureau) : rassemble les fiches saisies
  sans connexion. Un .zip ne contient que des fiches de cas (jamais de comptes). À l'import : nouvelles fiches
  ajoutées ; une fiche connue n'est remplacée que par une version plus récente (l'ancienne reste dans l'historique) ;
  un N° EPID déjà porté par une autre fiche est signalé sans rien écraser ; les fiches hors droits sont ignorées.

## Version 1.2 : synchronisation, sécurité, carte, réunion

- **Synchronisation automatique** de l'application de bureau avec le serveur : sur le site, *Mon compte* →
  *Créer un jeton* (un par ordinateur, révocable) ; dans l'application, *Riposte ▾ → Synchronisation…* (adresse du
  site + jeton, automatique toutes les 15 minutes si coché). Le bureau envoie ses fiches puis reçoit celles du
  périmètre du compte, avec les règles du paquet de fiches (rien n'est perdu, la plus récente l'emporte).
  API : `POST /api/sync/envoyer`, `GET /api/sync/recevoir` (en-tête `Authorization: Bearer <jeton>`).
- **Sécurité ▾** (bureau) : mot de passe au démarrage ; sauvegarde automatique quotidienne et à la fermeture dans
  un dossier choisi (clé USB), 20 dernières gardées ; reprise des fiches d'une sauvegarde sans rien écraser.
  Le mot de passe ne chiffre pas le disque : activer BitLocker (Windows) ou FileVault (Mac).
- **Nouvelle version** : l'application de bureau compare sa version à `packaging/VERSION` sur GitHub (sans envoyer
  de données) et prévient une fois.
- **Carte des cas** (hors ligne) : GPS de la fiche, sinon coordonnées de l'aire de santé (CSV
  `province;zone_sante;aire_sante;latitude;longitude` importé sur la page Carte, gardé dans le dossier de données),
  sinon centre de la ZS ; les cas sans position sont listés.
- **Mode réunion** : diaporama plein écran (chiffres, courbe, ZS actives, indicateurs en alerte, alertes, actions en
  retard, mapping de chaque nouveau cas).
- **Doublons possibles** : même N° EPID, ou même ZS, sexe, âge ± 1 an et début ± 2 jours (rien n'est fusionné).
- **Vaccination en anneau** (colonne *Vaccinés* des contacts, date de début de l'anneau), **séquençage**,
  **nombre de reproduction observé** (cas secondaires reliés par cas de plus de 42 jours).
- **Téléphone** : menu repliable et pages adaptées aux petits écrans.
- Fichiers d'automatisation GitHub (tests, installateurs) : `packaging/github/`.

## Version 1.3 : champs obligatoires et carte sur les contours réels

- **Champs obligatoires** (`config/champs_obligatoires.yaml`, modifiable) : ID du cas, province, zone et aire de santé,
  sexe, âge, début des symptômes, date de confirmation, état du cas. Sans eux, une fiche n'est **pas enregistrée** :
  la saisie est gardée en **brouillon** (table `brouillons`), hors de la liste des cas, des analyses et de la
  synchronisation, et le formulaire montre les champs manquants en rouge. Une fiche déjà enregistrée qu'on vide d'un
  champ obligatoire garde sa dernière version complète. « Nouveau cas » et les imports incomplets créent un brouillon.
- **Carte** : contours réels des aires de santé et limites des zones de santé, aires touchées colorées selon le
  dernier cas notifié, zoom (molette, pincement) et déplacement. Contours du Nord-Kivu livrés
  (`config/geo/aires_nord-kivu.json`, 661 aires, GRID3 / CIESIN 2025, simplifiés à ≈ 150 m). Autres provinces :
  importer leur GeoPackage (.gpkg, colonnes Province, Zone, Aire) depuis la page Carte ou l'application de bureau
  (Riposte ▾ → Importer les contours) ; conversion par `core/geo.py`, sans bibliothèque externe.

## Licence

**GNU Affero General Public License v3 (AGPL-3.0)** : fichier `LICENSE`, mentions dans `NOTICE`.
Copyright (C) 2026 Onesime Mbulayi et les contributeurs de Mapping Épi.

- Utilisation, copie, étude et modification libres et gratuites, y compris par les ministères, l'OMS et les ONG.
- Toute version modifiée mise à disposition d'autres personnes (installée ou **sur un serveur web**) doit être
  publiée avec son code source, sous la même licence : les améliorations restent disponibles pour toute la riposte.
- Pour une autre licence (intégration dans un produit fermé) ou un appui à la mise en œuvre, contacter
  l'équipe de développement.
- Police Inter : SIL OFL 1.1. Contours des aires de santé : GRID3 / CIESIN (à citer). Les fiches de cas
  saisies ne font pas partie du logiciel et ne sont jamais publiées.

## Version 1.4 : accueil simplifié, brouillons rangés, exemple en mode entraînement

- **Accueil** après la connexion : quatre boutons (Nouveau cas, Voir mes cas, Chaînes de transmission, Exemple fictif),
  sans liste. La liste est dans « Voir mes cas », en onglets **Enregistrés** et **Brouillons** (les siens seulement).
- Le texte rouge n'apparaît que dans une fiche ouverte : « Pas encore enregistrée : il manque … ». Les éléments utiles
  au mapping complet sont repliés, en gris.
- Les brouillons restés **entièrement vides** plus de 24 heures sont supprimés automatiquement.
- **Exemple fictif en mode entraînement** (`Case.entrainement`, ou ID commençant par « FICTIF ») : visible par son
  auteur seulement, jamais compté dans la liste des cas, les analyses, la carte, les exports ni la synchronisation.
  Un seul exemple par compte, recommencé à chaque clic.

## Version 1.5 : langue, thème clair, accueil

- **Langue** (menu FR ▾ / EN ▾ de la barre du haut) : français ou anglais, gardé pour le compte (`web/i18n.py`,
  table `preferences`). Traduits : connexion, accueil, menus, liste des cas, pied de page. Le formulaire de la fiche
  et les visuels produits restent en français pour l'instant.
- **Thème clair par défaut** ; le bouton Thème reste disponible (choix gardé sur le navigateur).
- **Message de bienvenue** sur l'accueil (champs obligatoires, enregistrement) et **pied de page** collé en bas.
