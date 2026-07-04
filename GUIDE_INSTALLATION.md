# 🪞 ROBIN MIROIR V2 — INSTALLATION PAR FICHIER UNIQUE

**Tu ne crées qu'UN SEUL fichier. La machine installe tout le reste toute seule au premier passage** : scripts, registre, dashboard, rapports. Elle se répare et se met à jour seule ensuite.

Ton dépôt `robin-miroir` existe déjà avec des fichiers dedans ? **Parfait, on le garde** — la V2 remplace proprement l'ancien contenu au premier tour, sans rien te demander.

---

## ÉTAPE 1 — Coller LE fichier (3 min)

1. Ouvre ton dépôt `robin-miroir` sur github.com
2. Bouton **Add file** → **Create new file**
3. Dans la case du nom, tape **exactement** :
   ```
   .github/workflows/robin.yml
   ```
   (en tapant les `/`, GitHub crée les dossiers tout seul — tu verras `.github` puis `workflows` apparaître : c'est normal)
4. Ouvre le fichier **`A_COLLER_robin.yml.txt`** que je t'ai donné → **Ctrl+A** (tout sélectionner) → **Ctrl+C**
5. Clique dans la grande zone de texte GitHub → **Ctrl+V**
6. Bouton vert **Commit changes** → confirme **Commit changes**

## ÉTAPE 2 — Les 2 clés (2 min — saute si déjà fait)

1. **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
2. Secret 1 → Name : `ODDS_API_KEY` · Secret : ta clé The Odds API → **Add secret**
3. Secret 2 → Name : `FOOTBALL_DATA_TOKEN` · Secret : ta clé football-data.org → **Add secret**

## ÉTAPE 3 — Regarder la machine s'installer (0 clic obligatoire)

À partir de là, **tout est automatique** — la machine démarre seule dans les 10 minutes. Impatient ? Onglet **Actions** → **Robin Miroir** (menu de gauche) → **Run workflow** → **Run workflow**.

**Au premier passage, la machine :**
- ✍️ installe ses 20 fichiers (scripts, registre, dashboard)
- 📊 active GitHub Pages toute seule (si GitHub refuse, elle t'ouvre une issue avec les 3 clics à faire)
- ✅ t'ouvre une issue « Robin Miroir est installé » avec le lien de ton dashboard
- 🔑 s'il manque une clé, t'ouvre une issue qui te dit exactement quoi faire — **le run reste vert, rien ne casse**

**Tes vérifications (1 min, juste des yeux) :**
- Onglet **Actions** : le run « Robin Miroir » est ✅
- Onglet **Issues** : l'issue « ✅ Robin Miroir est installé » est là, avec le lien du dashboard
- Le dashboard s'affiche (~2 min après le premier passage)

---

## 🔐 APRÈS (2 min, hygiène) — régénère tes 2 clés

Tes clés ont transité en clair dans nos échanges :
1. **The Odds API** : redemande une clé sur the-odds-api.com → remplace le secret `ODDS_API_KEY` (Settings → Secrets → crayon ✏️)
2. **football-data.org** : profil → régénérer le token → remplace `FOOTBALL_DATA_TOKEN`
La machine prend la nouvelle clé au passage suivant, automatiquement.

## 🔔 BONUS (optionnel, 5 min) — alertes Telegram

Sans ça tout marche : les alertes passent par les issues GitHub et les rapports.
1. Telegram → **@BotFather** → `/newbot` → copie le **token**
2. Écris « salut » à ton nouveau bot
3. Navigateur : `https://api.telegram.org/botTON_TOKEN/getUpdates` → repère `"chat":{"id":123456789` → c'est ton **chat_id**
4. Ajoute 2 secrets : `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`

## 🧨 OPTION B — repartir d'un dépôt 100 % neuf (si tu y tiens)

1. Dans l'ancien dépôt : **Settings** → tout en bas → **Delete this repository** → tape le nom → confirme
2. **New** → nom `robin-miroir` → **Public** → **Create repository**
3. Le nouveau dépôt propose « create a new file » → reprends l'ÉTAPE 1 ci-dessus
(Résultat identique à l'Option A — la V2 nettoie tout de toute façon.)

---

## Ce que tu verras ensuite (rien à faire)

- **Dashboard** : phrase de statut, 4 chiffres, jauge vers N = 200, santé des 5 agents (Guetteur, Greffier, Arbitre, Auditeur, Messager)
- **Chaque nuit** : règlement des paris + contrôle d'intégrité de l'Auditeur
- **Dimanche soir** : rapport hebdo ≤ 10 lignes
- **Jusqu'au 19/07** : bandeau RODAGE (Coupe du Monde = banc d'essai, rien ne compte) · **20/07** : registre officiel, tout seul

*Rappel du protocole : l'issue la plus probable est de prouver qu'il n'y a pas d'edge — proprement, pour 0 €. Ce sera un succès.*
