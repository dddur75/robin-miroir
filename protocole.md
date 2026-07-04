# ROBIN MIROIR — PROTOCOLE PRÉ-ENREGISTRÉ V2.0

**Statut : GELÉ au 4 juillet 2026 (J3).**
Toute modification d'un paramètre gelé après cette date **remet le compteur du test à zéro**. C'est la règle qui donne sa valeur au résultat.

---

## 1. Ce que le système est — et n'est pas

Robin Miroir **ne prédit rien**. Il compare deux prix au même instant :
la probabilité implicite de **Pinnacle dévigé** (le marché le plus efficient accessible)
et la cote d'**Unibet FR** (bookmaker grand public, TRJ plafonné).
Si Unibet paie nettement plus que le prix « juste » de Pinnacle, le système enregistre un **pari papier**. Aucun euro réel n'est engagé en phase 1.

**Question unique du test :** les cotes prises battent-elles la clôture Pinnacle (CLV > 0) sur N = 200 paris ? Si non, l'edge n'existe pas — et le prouver proprement est un **succès méthodologique**, pas un échec.

## 2. Paramètres gelés

| Paramètre | Valeur | Réf |
|---|---|---|
| Seuil de déclenchement | cote Unibet ≥ cote juste × **1,06** | — |
| Bande de cotes jouable | Unibet ∈ **[1,50 ; 4,00]**, hors bande = SHADOW | M1 |
| Filtre boost/anomalie | Unibet > Pinnacle brut × **1,15** → SUSPECT | M2 |
| Paris max par match | **1** (plus gros edge, le reste en SHADOW) | M4 |
| Paris max par jour | **10** (au-delà : SHADOW + alerte) | M5 |
| Mise | **10 u flat** (1 % de 1 000 u), jamais modifiée | — |
| Capture principale | fenêtre **[T-2h30 ; T-1h30]** avant coup d'envoi | — |
| Capture de clôture | fenêtre **[T-15 ; T-2 min]**, matchs déclenchés seulement | M6 |
| Dévigage champion | **Shin** (multiplicatif loggé à vie en parallèle) | §5 |
| N du verdict | **200** paris officiels réglés | — |
| Alerte de sécurité | à N ≥ 100 : CLV moyen ≤ **−3 %** → alerte (jamais de kill anticipé) | — |
| **Critère de mort** | à N = 200 : CLV moyen ≤ **0** → **KILL**, clôture propre | — |
| Ouverture du registre officiel | **20 juillet 2026** (avant : RODAGE, rien ne compte) | — |

## 3. Définitions gelées

- **CLV d'un pari** = (cote prise × p_vraie_clôture) − 1, où p_vraie_clôture = Pinnacle de clôture dévigé (méthode champion).
- **N** = nombre de paris **OFFICIELS réglés** (phase RODAGE exclue).
- **CLV moyen** = moyenne des CLV **disponibles** ; le taux de clôtures manquantes est publié et surveillé (> 10 % = problème de fiabilité de capture, pas de conclusion sur l'edge).
- **No-peeking** : aucune lecture de sous-segments (par ligue, par tranche) avant N = 100 ; aucune décision sur segments avant N = 200. Les segments servent au rapport de verdict, pas au pilotage.

## 4. Périmètre

Règle David : **« si on a les datas → on joue »**. Éligible = résultats gratuits (football-data.org, tier gratuit) **et** cotes (The Odds API). Soit 11 compétitions : Ligue 1, Premier League, Bundesliga, Serie A, La Liga, Champions League, Championship, Brasileirão, Eredivisie, Primeira Liga, Coupe du Monde. L'ordre ci-dessus est l'**ordre de priorité du délestage** (on coupe par la fin).

**Délestage pré-enregistré** : si les crédits API restants passent sous **60**, seules les **5 premières** compétitions tournent jusqu'à la fin du mois. Alerte envoyée, aucune décision à prendre.

Une 13ᵉ compétition qui deviendrait disponible plus tard entre d'abord en **ombre** (shadow, non comptée) une saison avant intégration éventuelle — jamais en cours de test.

## 5. Dévigage

Champion par défaut : **Shin** (corrige structurellement le biais favori-outsider). Le **duel** multiplicatif vs Shin (labo, CSV Football-Data.co.uk, clôtures Pinnacle PSCH/PSCD/PSCA, log-loss + Brier par tranches) confirme ou inverse le champion **avant le gel J3**. Quoi qu'il arrive, **les deux probabilités sont loggées à vie** dans le Grand Livre : le verdict pourra être recalculé sous l'autre méthode, à titre informatif uniquement.

## 6. Chaîne de mesure (résumé technique)

1. **Capture** (cron 10 min) : `/sports` (0 crédit) → `/events` (fenêtres) → `/odds` 1 crédit/ligue, `bookmakers=pinnacle,unibet_fr` (les deux prix dans la même réponse : simultanéité parfaite, zéro biais de séquence).
2. **Règles gelées** appliquées dans l'ordre : M2 (suspect) → M1 (bande) → seuil 1,06 → M4 (1/match) → M5 (cap jour). Chaque sélection évaluée laisse une trace (OBS/SHADOW) : la couverture Unibet et l'écart moyen vs sharp sont mesurés en continu.
3. **Clôture** [T-15 ; T-2] : Pinnacle seul, matchs déclenchés uniquement (1 crédit/match).
4. **Règlement** nocturne : football-data.org. Matching équipes (M11) : correspondance mémorisée → sinon EXACT (noms normalisés identiques + KO ± 40 min) → sinon FORT (similarité ≥ 0,85 + KO ± 40 min) → sinon **UNSETTLED, on ne devine jamais** (alerte à 48 h).
5. **Fiabilité** : Grand Livre append-only (PARI/CLOTURE/REGLEMENT liés par id), ID déterministes (M8), un seul code toutes phases (M7), horodatage 100 % UTC (M10), échec bruyant Telegram + issue GitHub (M9), verrou de concurrence sur l'écriture (M12).

## 6bis. Amendements V2.0 (adoptés avant le gel — conseil élargi)

| # | Règle | Effet |
|---|-------|-------|
| M18 | **Match reporté = VOID** | Après 72 h, si le match existe sous les mêmes noms exacts à un autre horaire : mise rendue, pari **exclu de N**. On ne devine jamais un score. |
| M19 | **Cote périmée = STALE** | Cote Pinnacle ou Unibet mise à jour il y a > 30 min à la capture : loggée en shadow, **jamais pariée**. Une cote figée n'est pas un prix réel. Âges des cotes loggés sur chaque pari et clôture. |
| M20 | **L'Auditeur** | Contrôle d'intégrité automatique chaque nuit (11 vérifications : unicité des IDs, orphelins, clôtures manquantes, paris en souffrance, fichiers d'état…). Anomalie ⇒ alerte + issue. Ne modifie jamais le Grand Livre. |
| M21 | **Installation monofichier** | Un seul fichier à créer à la main. Tout le système est embarqué dedans, s'auto-installe au premier passage, se met à jour par numéro de version, **n'écrase jamais les données**. |
| M22 | **Issues automatiques** | Installation réussie, clé manquante, Pages à activer, anomalie d'audit : la machine ouvre elle-même une issue GitHub qui explique quoi faire. |
| M23 | **Chef d'orchestre** | Un seul workflow, trois horloges. Le chef route cron → tâche et gère les secrets manquants proprement (run vert + issue d'aide, jamais de crash silencieux). |
| M24 | **Recette formelle** | L'installateur lui-même est testé : reconstruction vérifiée bit à bit par empreinte SHA-256, idempotence, préservation des données, test à blanc rejoué dans la copie installée. |

**Définition de N (précision V2)** : N compte uniquement les paris réglés **GAGNÉ ou PERDU**. Les VOID (reportés) sont hors test.

**Les 5 agents** : Guetteur (capture) · Greffier (grand livre) · Arbitre (règlement) · Auditeur (intégrité) · Messager (rapports/alertes). Rôles logiciels spécialisés et surveillés — leur santé est affichée sur le dashboard.

## 7. Calendrier et checkpoints

| Date | Événement |
|---|---|
| 4 juil. 2026 | **Gel J3** (ce document) + verdict du duel de dévigage |
| 4 → 19 juil. | **RODAGE** sur la fin de Coupe du Monde : la machine se teste, rien ne compte |
| **20 juil. 2026** | **Ouverture du registre officiel** (Brasileirão d'abord, Top 5 mi-août) |
| N = 100 | Alerte de sécurité éventuelle (CLV ≤ −3 %) — poursuite quoi qu'il arrive |
| + 6 mois | Checkpoint volume : si le rythme réel rend N = 200 inatteignable en ~14 mois, le conseil se réunit (constat de volume, pas retouche du seuil) |
| N = 200 | **Verdict.** CLV ≤ 0 → KILL et clôture propre. CLV > 0 → conseil GO/NO-GO phase 2, avec IC95 (M15) et section « viabilité réelle » — limitations de compte incluses (M14) |

## 8. Hypothèses honnêtes (à mesurer, pas à croire)

- Fréquence de déclenchement : **10–30 paris/mois** [HYPOTHÈSE] → N = 200 ≈ une saison.
- Couverture Unibet FR dans le flux The Odds API : à mesurer au rodage.
- Budget crédits : **350–480/mois** estimés pour 500 gratuits [HYPOTHÈSE] — le délestage protège.
- 30 à 50 % des « edges » vus à T-2h s'évaporeront à la clôture (avis des pros consultés). C'est exactement ce que le CLV mesure.
- **L'issue la plus probable du test est : pas d'edge.** Le système est construit pour rendre cette réponse fiable et bon marché.

## 9. Gouvernance

- Zéro décision en cours de route : tout est pré-enregistré ici.
- Rapport hebdo ≤ 10 lignes, phrase de statut en tête (M17). Aucune action attendue de David en régime normal.
- Zéro euro réel avant un GO explicite du conseil **après** le verdict N = 200.

---

## AVENANT V2.0 — adopté avant gel (le gel reste fixé au 4 juillet 2026)

| Règle | Contenu |
|---|---|
| **M18** | Match reporté (mêmes équipes, horaire écarté > 40 min, constaté après 72 h) → pari **VOID** : mise rendue, **exclu de N** |
| **M19** | Cote périmée (dernière mise à jour > 30 min, Pinnacle **ou** Unibet, au moment de la capture) → **STALE** : loggée en shadow, **jamais pariée** |
| **M20** | **L'Auditeur** : contrôle d'intégrité quotidien (11 vérifications) après le règlement ; anomalie → alerte + issue. Il ne modifie jamais le Grand Livre |
| **M21** | Installation par **fichier unique** auto-installant, idempotent, versionné ; les données ne sont **jamais** écrasées |
| **M22** | Issues GitHub automatiques : « installé ✅ », « clé manquante 🔑 » (marche à suivre incluse), « active Pages 📊 » si l'activation auto échoue |
| **M23** | **Un seul workflow** : le chef d'orchestre route les 3 crons (capture / règlement+audit / rapport) et le lancement manuel |
| **M24** | Recette formelle de l'installateur : extraction du payload, exécution à vide, empreintes SHA-256, idempotence, préservation des données, test à blanc dans la copie installée |

**Les 5 agents** (rôles logiciels automatisés, pilotés par le chef) : Guetteur (capture) · Greffier (grand livre) · Arbitre (règlement) · Auditeur (intégrité) · Messager (rapports/alertes).

**Paramètres inchangés** : seuil 1,06 · N = 200 · critère de mort CLV ≤ 0 · mise flat 10 u · bankroll fictive 1 000 u · fenêtre de clôture T-15 → T-2. **N ne compte que les paris GAGNÉ/PERDU** (VOID exclus).
