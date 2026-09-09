# Feedback & Iteration Guide / Guide des commentaires et de l'itération

**EN / FR — both languages in one file. / Les deux langues dans un seul fichier.**

---

# ENGLISH

## 1. Why feedback matters here

The validator's rules encode Statistics Canada's Tables 101 and Charts 101 guides. When a rule is wrong, too strict, or missing, the fastest fix is a precise report from the person who saw the problem. Every change to rules or behaviour arrives through this process — nothing is changed silently.

## 2. What goes where

| You want to… | Use | Where |
|---|---|---|
| Report something broken | **Bug** template | GitLab → Issues → New issue → *Bug report / Rapport d'anomalie* |
| Ask for a new rule or change | **Change request** template | GitLab → Issues → *Change request / Demande de changement* |
| Ask why a finding appeared | **Question** template | GitLab → Issues → *Question* |
| Suggest an improvement to these guides | **Change request** template, label `docs` | GitLab → Issues |

If Issues are disabled on your GitLab, send the filled template to the project maintainer by email.

## 3. What makes a good bug report

1. **The exact steps** — which buttons you clicked, in order. We reproduce every bug by following your steps exactly.
2. **The terminal output** — if the app was started from a terminal, copy *everything* shown. This is the single most useful item; it names the failing check directly.
3. **The workbook** — attach a **redacted** copy (replace real values with dummy numbers, keep the structure). Structure is what the rules inspect. **Never attach confidential data.**
4. **What you expected** — e.g. "this table should be compliant" or "the symbol `x` should be accepted".

## 4. What happens after you file

| Stage | Who | Timeframe (typical) |
|---|---|---|
| Triage — label, confirm reproduction | Project maintainer | 2 business days |
| Decision — fix now / next release / declined with reason | Maintainer + rule owner | 5 business days |
| Fix implemented + tests added | Developer | Depends on scope |
| Verified release published | Maintainer | You are pinged on your issue |

Your issue is closed only when the fix is **in a release** and you have confirmed it (or explicitly deferred). You are always told the outcome and the reason — "declined" answers include which guide section justifies the current behaviour.

## 5. Release & version discipline

- Every change lands through a merge request reviewed by a second person; the GitLab pipeline (test suite + fixture gates + determinism check) must be green before merge.
- Releases are tagged; the operator guide's expected finding counts are updated **in the same release** as any rule change, so the documentation never drifts.
- You can always see what changed: GitLab → *Repository → Tags*, or ask for the release notes.
- Deploy the update with `git pull && bash scripts/deploy_local.sh` (see `docs/DEPLOYMENT_GUIDE.md` §5). Your projects and revision history are preserved.

## 6. Confidentiality

Uploaded workbooks stay on your machine. When attaching examples to issues, redact real values first. Never paste survey data into an issue.

---

# FRANÇAIS

## 1. Pourquoi vos commentaires comptent

Les règles du validateur reproduisent les guides Tableaux 101 et Graphiques 101 de Statistique Canada. Lorsqu'une règle est erronée, trop stricte ou manquante, le correctif le plus rapide vient d'un rapport précis de la personne qui a vu le problème. Tout changement de règle ou de comportement passe par ce processus — rien n'est modifié en silence.

## 2. Quoi utiliser pour quoi

| Vous voulez… | Gabarit | Endroit |
|---|---|---|
| Signaler un problème | Gabarit **Bug** | GitLab → Tickets → Nouveau → *Bug report / Rapport d'anomalie* |
| Demander une nouvelle règle ou un changement | Gabarit **Demande de changement** | GitLab → Tickets → *Change request / Demande de changement* |
| Comprendre une constatation | Gabarit **Question** | GitLab → Tickets → *Question* |
| Proposer d'améliorer ces guides | Gabarit **Demande de changement**, étiquette `docs` | GitLab → Tickets |

Si les tickets sont désactivés sur votre GitLab, envoyez le gabarit rempli par courriel au responsable du projet.

## 3. Ce qui fait un bon rapport d'anomalie

1. **Les étapes exactes** — les boutons cliqués, dans l'ordre. Nous reproduisons chaque anomalie en suivant vos étapes à la lettre.
2. **La sortie du terminal** — si l'application a été démarrée dans un terminal, copiez *tout* ce qui est affiché. C'est l'élément le plus utile ; il nomme directement la vérification en échec.
3. **Le classeur** — joignez une copie **anonymisée** (remplacez les valeurs réelles par des valeurs factices, conservez la structure). C'est la structure que les règles inspectent. **Ne joignez jamais de données confidentielles.**
4. **Le résultat attendu** — p. ex. « ce tableau devrait être conforme » ou « le symbole `x` devrait être accepté ».

## 4. Ce qui se passe après votre signalement

| Étape | Qui | Délai (typique) |
|---|---|---|
| Tri — étiquetage, confirmation de la reproduction | Responsable du projet | 2 jours ouvrables |
| Décision — corriger maintenant / prochaine version / refusé avec motif | Responsable + propriétaire de la règle | 5 jours ouvrables |
| Correctif implémenté + tests ajoutés | Développeur | Selon l'ampleur |
| Version vérifiée publiée | Responsable | Vous êtes avisé sur votre ticket |

Un ticket n'est fermé que lorsque le correctif est **dans une version publiée** et que vous l'avez confirmé (ou reporté explicitement). Le résultat et le motif vous sont toujours communiqués — un refus indique la section du guide qui justifie le comportement actuel.

## 5. Discipline des versions

- Tout changement passe par une demande de fusion relue par une seconde personne ; le pipeline GitLab (suite de tests + portes des jeux d'essai + vérification du déterminisme) doit être vert avant la fusion.
- Les versions sont étiquetées ; les nombres de constatations attendus du guide de l'opérateur sont mis à jour **dans la même version** que tout changement de règle — la documentation ne dérive jamais.
- Vous pouvez toujours voir ce qui a changé : GitLab → *Dépôt → Étiquettes*, ou demandez les notes de version.
- Déployez la mise à jour avec `git pull && bash scripts/deploy_local.sh` (voir `docs/DEPLOYMENT_GUIDE.md` §5). Vos projets et votre historique de révisions sont préservés.

## 6. Confidentialité

Les classeurs téléversés restent sur votre poste. Lorsque vous joignez des exemples à un ticket, anonymisez d'abord les valeurs réelles. Ne collez jamais de données d'enquête dans un ticket.
