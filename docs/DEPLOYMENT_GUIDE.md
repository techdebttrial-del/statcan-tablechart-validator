# Deployment Guide — Local Deployment for Operators / Guide de déploiement — Installation locale pour opérateurs

**EN / FR — Both languages in one file. Each section appears in English first, then in French. / Les deux langues dans un seul fichier. Chaque section paraît d'abord en anglais, puis en français.**

**Audience:** a clerk or non-technical operator who needs to run the Tables & Charts Validator on their own workstation, connect it to their local GitLab, and report problems. No programming experience required.

**Version:** matches repository `main` at release R2. All steps verified on Ubuntu 22.04/24.04 with Python 3.10–3.12.

---

# ENGLISH

## 1. What you are deploying

A deterministic Streamlit application that validates Excel workbooks against Statistics Canada **Tables 101** and **Charts 101** formatting rules, and applies approved corrections as new immutable workbook iterations. It has **no LLM, no cloud calls, and no data leaves your machine.** Everything runs locally from the repository folder.

You will end up with:

| Component | Where | Purpose |
|---|---|---|
| The application | `~/statcan-tablechart-validator/` | Validation + remediation UI |
| Python environment | `.venv/` inside the app folder | Isolated dependencies (safe, removable) |
| Verification gate | `scripts/verify_deployment.sh` | Proof the deployment is healthy |
| Test pipeline | `.gitlab-ci.yml` | Runs the same gates on GitLab after every change |

## 2. Prerequisites (one-time)

Ask IT if any of these are missing:

1. **Python 3.10 or newer** — check with `python3 --version`. (Ubuntu: `sudo apt install python3 python3-venv python3-pip`)
2. **Git** — check with `git --version`. (Ubuntu: `sudo apt install git`)
3. **Access to the repository source.** Either a copy of the project folder given to you directly, or read access to your organisation's GitLab.

No other software, no database, no internet connection is required at runtime.

## 3. Deploy — three commands

```bash
# 1. Get the code (skip if you were given the folder directly)
git clone <YOUR-GITLAB-URL>/statcan-tablechart-validator.git
cd statcan-tablechart-validator

# 2. One-command deploy (creates .venv, installs everything, runs all gates)
bash scripts/deploy_local.sh

# 3. Start the app
.venv/bin/streamlit run app/main.py --server.port 8502
```

Open **http://localhost:8502** in your browser. Done.

`deploy_local.sh` is safe to re-run at any time — it refreshes dependencies and re-runs every verification gate. If it ends with `ALL CHECKS PASSED`, your deployment is verified.

## 4. Verify — prove it works (2 minutes)

```bash
bash scripts/verify_deployment.sh
```

Expected output ends with `ALL CHECKS PASSED` after four gates:

1. Environment — Python environment and core libraries import cleanly.
2. Test suite — the full deterministic test suite passes (172 tests).
3. Fixture gates — the rule engine returns exactly the documented finding counts (0 for perfect workbooks, 13 and 7 for the two failing ones).
4. Determinism guarantee — confirms there is no LLM machinery anywhere in the app or engine.

**If any gate fails, do not present or use the app for production work.** Follow §6 Troubleshooting, or file feedback per `docs/FEEDBACK.md`.

## 5. Keeping it up to date

When your team publishes a new release:

```bash
git pull                      # or re-copy the provided folder
bash scripts/deploy_local.sh  # re-runs the whole gate
```

Your projects, uploaded workbooks, and revision history live in the app's data directory (created on first use) and are **not** touched by updating the code.

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `python3: command not found` | Python not installed | Install Python 3.10+ (see §2), re-run |
| `python3-venv` error during deploy | venv module missing | `sudo apt install python3-venv`, re-run |
| `FAIL` in verify step 2/3 | Incomplete download or edited files | Re-run `bash scripts/deploy_local.sh`; if it still fails, file feedback with the full terminal output |
| Browser can't open `localhost:8502` | App not started, or wrong port | Start it per §3; check the port number printed in the terminal |
| Port already in use | Another app on 8502 | Use another number: `--server.port 8503` |
| App feels slow | Large workbook | Normal for >50k cells; wait for the spinner |

Nothing here requires administrator rights at runtime — only the two installs in §2.

## 7. Connecting to your local GitLab

The project ships with `.gitlab-ci.yml`. Once the code is in your GitLab:

1. **Push the project** to your GitLab group (your GitLab admin or IT can do this, or: `git remote add gitlab <URL> && git push gitlab main`).
2. **Pipeline runs automatically** on every push and merge request: it builds a clean Python environment and runs the *same* `verify_deployment.sh` gates you ran locally (test suite + fixture counts + determinism check) on Python 3.11 and 3.12.
3. **Read the pipeline:** GitLab → your project → *Build → Pipelines*. A green ✔ means the release is verified; a red ✘ means do not deploy that commit.
4. **If your runner has no internet**, pre-approach: ask IT to allow `pypi.org` for the runner, or pre-build the wheel cache. The pipeline itself needs no secrets — the app has no API keys by design.

That's the entire integration: no runners to configure beyond standard shared runners, no variables, no secrets.

## 8. Reporting feedback and requesting changes

Full process in **`docs/FEEDBACK.md`** (bilingual). Summary:

- **Something broken?** Open a *Bug report* issue in GitLab using the bilingual template (`.gitlab/issue_templates/Bug.md`). Paste the terminal output — it always tells us what failed.
- **Want a change or new rule?** Use the *Change request* template (`.gitlab/issue_templates/Change_Request.md`).
- **Question about a finding?** Use *Question* template (`.gitlab/issue_templates/Question.md`).
- If your GitLab has no issue tracker enabled, email the template text to the project maintainer.

---

# FRANÇAIS

## 1. Ce que vous déployez

Une application Streamlit **déterministe** qui valide les classeurs Excel selon les règles de mise en forme **Tableaux 101** et **Graphiques 101** de Statistique Canada, et applique les corrections approuvées sous forme de nouvelles itérations immuables du classeur. **Aucun LLM, aucun appel infonuagique : aucune donnée ne quitte votre poste.** Tout s'exécute localement à partir du dossier du projet.

Vous obtiendrez :

| Composante | Emplacement | Rôle |
|---|---|---|
| L'application | `~/statcan-tablechart-validator/` | Interface de validation et de correction |
| Environnement Python | `.venv/` dans le dossier | Dépendances isolées (supprimable sans risque) |
| Porte de vérification | `scripts/verify_deployment.sh` | Preuve que le déploiement est sain |
| Pipeline de tests | `.gitlab-ci.yml` | Exécute les mêmes portes sur GitLab après chaque changement |

## 2. Prérequis (une seule fois)

Demandez au soutien TI s'il en manque :

1. **Python 3.10 ou plus récent** — vérifiez avec `python3 --version`. (Ubuntu : `sudo apt install python3 python3-venv python3-pip`)
2. **Git** — vérifiez avec `git --version`. (Ubuntu : `sudo apt install git`)
3. **Accès au code source** : soit une copie du dossier du projet remise directement, soit un accès en lecture au GitLab de votre organisation.

Aucun autre logiciel, aucune base de données, aucune connexion Internet en cours d'exécution.

## 3. Déploiement — trois commandes

```bash
# 1. Obtenir le code (ignorer si le dossier vous a été remis directement)
git clone <URL-DE-VOTRE-GITLAB>/statcan-tablechart-validator.git
cd statcan-tablechart-validator

# 2. Déploiement en une commande (crée .venv, installe tout, exécute les portes)
bash scripts/deploy_local.sh

# 3. Démarrer l'application
.venv/bin/streamlit run app/main.py --server.port 8502
```

Ouvrez **http://localhost:8502** dans votre navigateur. C'est terminé.

`deploy_local.sh` peut être relancé à tout moment — il actualise les dépendances et relance toutes les portes de vérification. S'il se termine par `ALL CHECKS PASSED`, votre déploiement est vérifié.

## 4. Vérification — la preuve que ça fonctionne (2 minutes)

```bash
bash scripts/verify_deployment.sh
```

La sortie attendue se termine par `ALL CHECKS PASSED` après quatre portes :

1. Environnement — l'environnement Python et les bibliothèques se chargent proprement.
2. Suite de tests — la suite déterministe complète passe (172 tests).
3. Portes des jeux d'essai — le moteur renvoie exactement les nombres documentés (0 pour les classeurs parfaits, 13 et 7 pour les deux défaillants).
4. Garantie de déterminisme — confirme l'absence de toute composante LLM dans l'application ou le moteur.

**Si une porte échoue, n'utilisez pas l'application pour un travail de production.** Suivez la section 6 (Dépannage) ou soumettez un commentaire selon `docs/FEEDBACK.md`.

## 5. Mise à jour

À chaque nouvelle version publiée par l'équipe :

```bash
git pull                      # ou re-copier le dossier fourni
bash scripts/deploy_local.sh  # relance toutes les portes
```

Vos projets, classeurs téléversés et historique de révisions résident dans le répertoire de données de l'application (créé à la première utilisation) et **ne sont pas touchés** par la mise à jour du code.

## 6. Dépannage

| Symptôme | Cause | Correctif |
|---|---|---|
| `python3: command not found` | Python absent | Installer Python 3.10+ (voir §2), relancer |
| Erreur `python3-venv` au déploiement | Module venv manquant | `sudo apt install python3-venv`, relancer |
| `FAIL` à la vérification 2/3 | Téléchargement incomplet ou fichiers modifiés | Relancer `bash scripts/deploy_local.sh` ; si l'échec persiste, soumettre un commentaire avec la sortie complète du terminal |
| Le navigateur n'ouvre pas `localhost:8502` | Application non démarrée ou mauvais port | Démarrer selon §3 ; vérifier le port affiché dans le terminal |
| Port déjà utilisé | Une autre application sur 8502 | Choisir un autre numéro : `--server.port 8503` |
| Application lente | Classeur volumineux | Normal au-delà de 50 000 cellules ; attendre la fin du chargement |

Rien ne requiert de droits d'administrateur en cours d'exécution — seulement les deux installations de la §2.

## 7. Raccordement à votre GitLab local

Le projet inclut `.gitlab-ci.yml`. Une fois le code dans votre GitLab :

1. **Pousser le projet** dans votre groupe GitLab (l'administrateur peut le faire, ou : `git remote add gitlab <URL> && git push gitlab main`).
2. **Le pipeline s'exécute automatiquement** à chaque poussée et demande de fusion : il construit un environnement Python propre et exécute les *mêmes* portes `verify_deployment.sh` (suite de tests + comptes des jeux d'essai + vérification du déterminisme) sur Python 3.11 et 3.12.
3. **Lire le pipeline** : GitLab → votre projet → *Build → Pipelines*. Un ✔ vert signifie version vérifiée ; un ✘ rouge signifie de ne pas déployer ce commit.
4. **Si votre runner n'a pas Internet**, demandez au TI d'autoriser `pypi.org` pour le runner, ou de pré-construire le cache de paquets. Le pipeline n'exige aucun secret — l'application n'a, par conception, aucune clé d'API.

C'est toute l'intégration : aucun runner particulier, aucune variable, aucun secret.

## 8. Commentaires et demandes de changement

Processus complet dans **`docs/FEEDBACK.md`** (bilingue). Résumé :

- **Quelque chose ne fonctionne pas ?** Ouvrez un ticket *Rapport d'anomalie* dans GitLab avec le gabarit bilingue (`.gitlab/issue_templates/Bug.md`). Collez la sortie du terminal — elle indique toujours ce qui a échoué.
- **Changement ou nouvelle règle ?** Utilisez le gabarit *Demande de changement* (`.gitlab/issue_templates/Change_Request.md`).
- **Question sur une constatation ?** Utilisez le gabarit *Question* (`.gitlab/issue_templates/Question.md`).
- Si le suivi des tickets est désactivé sur votre GitLab, envoyez le texte du gabarit par courriel au responsable du projet.
