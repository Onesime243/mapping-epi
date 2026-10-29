# Mettre Mapping Épi en ligne sur Hetzner (≈ 6–7 $/mois)

Résultat : une adresse **https://…** que les équipes des zones et aires de santé ouvrent sur
téléphone, tablette ou ordinateur. Chacun se connecte avec **son identifiant et son mot de passe**,
saisit ses cas et télécharge son mapping (PNG, PDF, PowerPoint…). Toutes les fiches sont
centralisées sur le serveur et sauvegardées chaque nuit.

Durée : 20 à 30 minutes, une seule fois.

---

## Étape 1 — Créer le serveur (sur le site Hetzner)

1. Créez un compte sur **console.hetzner.cloud** (carte bancaire ou PayPal ; une vérification
   d'identité peut être demandée).
2. **Nouveau projet** → « Mapping Epi » → **Ajouter un serveur** :
   - **Emplacement** : Falkenstein ou Nuremberg (Allemagne) ou Helsinki.
   - **Image** : **Ubuntu 24.04**.
   - **Type** : *Shared vCPU* → **x86 (Intel/AMD)** → **CX23** (2 vCPU, 4 Go de RAM).
     ⚠ Ne prenez pas une machine **Arm** (CAX) : le moteur d'export PNG/PDF n'y est pas disponible.
   - **Réseau** : laissez **IPv4 public** coché.
   - **Clé SSH** : facultative. Sans clé, Hetzner vous envoie le mot de passe **root** par e-mail.
   - **Sauvegardes Hetzner** (option +20 %) : facultatif, l'outil fait déjà ses propres sauvegardes.
   - Nom : `mapping-epi` → **Créer et acheter**.
3. Notez l'**adresse IPv4** du serveur (ex. `91.98.12.34`).

## Étape 2 — Installer l'application (une commande)

Sur votre Mac, ouvrez **Terminal** :

```bash
ssh root@91.98.12.34          # remplacez par votre adresse IP ; tapez « yes » puis le mot de passe reçu
```

À la première connexion, Hetzner peut demander de changer le mot de passe root : choisissez-en un solide.
Puis, toujours dans cette fenêtre :

```bash
curl -fsSL https://raw.githubusercontent.com/Onesime243/mapping-epi/main/deploy/install.sh | bash
```

L'installation dure 5 à 10 minutes. À la fin, l'adresse s'affiche, par exemple :

```
Mapping Épi est en ligne :  https://mapping-epi.91-98-12-34.sslip.io
```

*Vous avez un nom de domaine ?* Faites pointer un sous-domaine (ex. `mapping.mondomaine.org`) vers l'IP
du serveur, puis lancez :
`DOMAINE=mapping.mondomaine.org EMAIL=vous@exemple.org bash /opt/mapping-epi/deploy/install.sh`

## Étape 3 — Créer votre compte administrateur

```bash
mapping-epi creer-admin
```

Répondez aux questions (identifiant, nom, mot de passe). C'est fait : ouvrez l'adresse https dans votre
navigateur et connectez-vous.

## Étape 4 — Créer les comptes des ZS / AS

Dans le site, menu **Utilisateurs** → *Nouveau compte* :
- identifiant (ex. `zs.tumba`, `as.nzala`), nom, zone de santé, rôle **Agent** ;
- un mot de passe est proposé : notez-le et transmettez-le à la personne (il ne sera plus affiché).

Envoyez à chaque équipe : **l'adresse**, **son identifiant**, **son mot de passe**.
Chaque agent ne voit que ses propres fiches ; vous (administrateur) voyez tout.

---

## Au quotidien (sur le serveur, après `ssh root@IP`)

| Commande | Effet |
|---|---|
| `mapping-epi utilisateurs` | liste des comptes |
| `mapping-epi mot-de-passe zs.tumba` | nouveau mot de passe pour un compte |
| `mapping-epi desactiver zs.tumba` | bloquer un compte (`activer` pour rétablir) |
| `mapping-epi sauvegarde` | sauvegarde immédiate (automatique chaque nuit à 2 h 30, 14 jours gardés) |
| `mapping-epi restaurer /var/backups/mapping-epi/mapping_epi_….tar.gz` | revenir à une sauvegarde |
| `mapping-epi mise-a-jour` | installer la dernière version publiée sur GitHub |
| `mapping-epi etat` / `mapping-epi journal` | vérifier que tout tourne / voir les erreurs |

**Récupérer toutes les fiches sur votre Mac** (copie de sauvegarde) :
```bash
scp root@91.98.12.34:/var/backups/mapping-epi/*.tar.gz ~/Documents/mapping-epi/sauvegardes_serveur/
```
Chaque fiche peut aussi être téléchargée en JSON depuis le site, puis importée dans l'application de bureau.

## Sécurité mise en place

- HTTPS automatique (certificat Let's Encrypt renouvelé tout seul).
- Pare-feu : seuls SSH, HTTP et HTTPS sont ouverts ; protection contre les essais de mot de passe SSH (fail2ban).
- Mises à jour de sécurité Ubuntu automatiques.
- Mots de passe chiffrés (PBKDF2), sessions de 12 h, protection CSRF, blocage après plusieurs échecs de connexion.
- L'application tourne avec un utilisateur sans privilèges ; les données sont dans `/var/lib/mapping-epi`,
  jamais dans le dépôt GitHub.
- La page de création du premier administrateur est désactivée sur internet (création uniquement en ligne de commande).

Ce sont des données de santé : créez un compte par personne, désactivez les comptes des personnes qui
quittent l'équipe, et ne partagez jamais le mot de passe administrateur.

## Coût

CX23 : environ 5,49 € / mois + adresse IPv4 (≈ 0,60 €), soit ≈ 6–7 $ / mois. Facturé à l'heure :
supprimer le serveur arrête la facturation.
