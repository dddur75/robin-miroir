# 🪞 Robin Miroir

**Détecteur de value bets par miroir de prix — 100 % automatisé, 100 % papier, 0 €.**

Ce système ne prédit rien. Toutes les 10 minutes, il compare le prix « juste » de
**Pinnacle dévigé** (méthode de Shin) à la cote d'**Unibet FR** sur le marché 1N2,
2 heures avant le coup d'envoi. Quand Unibet paie ≥ 1,06 × le prix juste, il
enregistre un **pari papier** dans un Grand Livre en append-only, capture la
clôture Pinnacle, puis mesure le **CLV** (Closing Line Value).

**Test pré-enregistré** (voir [`protocole.md`](protocole.md), gelé) :
- N = **200** paris officiels réglés
- CLV moyen ≤ 0 → **KILL**, clôture propre du projet
- CLV moyen > 0 → conseil GO/NO-GO pour une éventuelle phase réelle

📊 Dashboard : `https://<pseudo>.github.io/robin-miroir/` · 🛠 Installation : [`GUIDE_INSTALLATION.md`](GUIDE_INSTALLATION.md)

| Pièce | Rôle |
|---|---|
| `scripts/capture.py` | cotes T-2h + clôtures, règles gelées M1–M5, paris papier |
| `scripts/reglement.py` | scores officiels, P&L, matching équipes (jamais deviné) |
| `scripts/audit.py` | L'Auditeur : contrôle d'intégrité quotidien (M20) |
| `scripts/chef.py` | Le chef d'orchestre : cron → tâche, secrets gérés proprement (M23) |
| `scripts/rapport.py` | rapport hebdo ≤ 10 lignes |
| `scripts/dashboard.py` | page statique 4 métriques + jauge de verdict |
| `scripts/labo_devig.py` | duel multiplicatif vs Shin sur historiques (labo) |
| `scripts/test_a_blanc.py` | test de bout en bout hors ligne (M13) |
| `data/grand_livre.jsonl` | le registre : PARI / CLOTURE / REGLEMENT, append-only |

*L'issue la plus probable de ce test est de prouver que l'edge n'existe pas.
Le système est construit pour rendre cette réponse fiable, rapide et gratuite.*

---
**V2.0** — installation par fichier unique auto-installant · 5 agents (Guetteur, Greffier, Arbitre, Auditeur, Messager) · M18 match reporté → VOID hors N · M19 cote périmée → jamais pariée · M20 audit d'intégrité quotidien.
