# Fichiers d'automatisation GitHub

Copies de référence des fichiers `.github/workflows/`. Pour les mettre en place (le jeton d'envoi de l'ordinateur
n'a pas la permission « workflow ») : sur github.com, **Add file > Create new file** (ou le crayon pour modifier
un fichier existant), nom `.github/workflows/<fichier>.yml`, coller le contenu, **Commit changes**.

- `tests.yml` : lance les tests à chaque envoi sur `main`.
- `installateurs.yml` : construit les installateurs Windows et Mac (accents corrigés, tests avant la construction).
