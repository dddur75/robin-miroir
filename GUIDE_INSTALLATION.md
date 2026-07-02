# 🪞 ROBIN MIROIR — INSTALLATION EN 5 ÉTAPES (~10 minutes, que des clics)

Tu n'écris **aucune ligne de code**. Tu cliques, la machine fait le reste.
Prérequis : ton compte GitHub, et le zip `robin-miroir.zip` **décompressé** sur ton ordinateur.

---

## ÉTAPE 1 — Créer le dépôt et déposer les fichiers (3 min)

1. Va sur **github.com** → bouton vert **New** (nouveau dépôt).
2. Nom du dépôt : `robin-miroir` · Visibilité : **Public** (obligatoire : minutes d'automatisation illimitées + dashboard gratuit).
3. Ne coche rien d'autre → **Create repository**.
4. Sur la page qui s'ouvre, clique le lien **uploading an existing file**.
5. Ouvre le dossier décompressé `robin-miroir` sur ton ordinateur, sélectionne **tout son contenu** et glisse-le dans la page GitHub.
   - ⚠️ Tu dois voir passer le dossier **`.github`** dans la liste. Sur Mac il est caché : fais `Cmd + Maj + .` pour l'afficher avant de glisser. Sur Windows il est visible normalement.
6. En bas : **Commit changes**.

## ÉTAPE 2 — Mettre les 2 clés en coffre-fort (2 min)

1. Dans ton dépôt : **Settings** → menu de gauche **Secrets and variables** → **Actions**.
2. **New repository secret** :
   - Name : `ODDS_API_KEY` · Secret : *ta clé The Odds API* → **Add secret**
3. **New repository secret** à nouveau :
   - Name : `FOOTBALL_DATA_TOKEN` · Secret : *ta clé football-data.org* → **Add secret**

## ÉTAPE 3 — Allumer le dashboard (1 min)

1. **Settings** → menu de gauche **Pages**.
2. Source : **Deploy from a branch** · Branch : **main** · Dossier : **/docs** → **Save**.
3. Ton tableau de bord vivra à : `https://TON-PSEUDO.github.io/robin-miroir/` (compte ~2 min après le premier lancement pour la première publication).

## ÉTAPE 4 — Réveiller la machine (1 min)

1. Onglet **Actions** → si un bandeau le demande, clique **I understand my workflows, go ahead and enable them**.
2. Menu de gauche : **Capture** → bouton **Run workflow** → **Run workflow** (vert).
3. Attends ~1 min, la ligne passe au ✅. La machine tournera ensuite **toute seule, toutes les 10 minutes, pour toujours**.

## ÉTAPE 5 — Lancer le duel des dévigages (1 min, une seule fois)

1. Onglet **Actions** → menu de gauche : **Labo - Duel des devigages** → **Run workflow**.
2. À la fin (~2 min), le verdict est écrit dans le fichier `labo/rapport_devig.md` du dépôt. On le lit ensemble à J3 pour geler le champion.

---

## 🔐 APRÈS L'INSTALLATION — régénère tes 2 clés (M16, 2 min)

Tes clés ont transité en clair dans nos échanges. Par hygiène, une fois les secrets en place :
1. **The Odds API** : ouvre l'email « your API key » → lien de régénération (ou redemande une clé sur the-odds-api.com) → remplace le secret `ODDS_API_KEY` (Settings → Secrets → crayon).
2. **football-data.org** : connecte-toi → ton profil → régénère le token → remplace `FOOTBALL_DATA_TOKEN`.

## 🔔 BONUS (optionnel, 5 min) — alertes Telegram sur ton téléphone

Sans ça, tout marche quand même : les alertes restent visibles dans l'onglet Actions (runs rouges + issues) et dans les rapports.
1. Dans Telegram, cherche **@BotFather** → `/newbot` → suis les 2 questions → copie le **token**.
2. Écris n'importe quoi à ton nouveau bot (un « salut » suffit).
3. Ouvre dans ton navigateur : `https://api.telegram.org/botTON_TOKEN/getUpdates` → repère `"chat":{"id": 123456789` → ce nombre est ton **chat_id**.
4. Ajoute 2 secrets (comme à l'étape 2) : `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`.

---

## Ce que tu verras ensuite (rien à faire)

- **Dashboard** : phrase de statut + 4 chiffres + jauge vers le verdict N = 200.
- **Dimanche 21h** : rapport hebdo (≤ 10 lignes) sur Telegram et dans `rapports/`.
- **Jusqu'au 19 juillet** : bandeau **RODAGE** — la machine s'entraîne sur la fin de Coupe du Monde, rien ne compte.
- **20 juillet** : le registre officiel s'ouvre tout seul.

*Rappel du protocole : l'issue la plus probable est de prouver qu'il n'y a pas d'edge — proprement, pour 0 €. Ce sera un succès.*
