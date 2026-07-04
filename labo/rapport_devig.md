# LABO — Duel des dévigages (clôtures Pinnacle, Football-Data.co.uk)

Matchs analysés : **5777** (E0, E1, F1, D1, I1, SP1 × saisons 2324, 2425, 2526)
Replis Shin (non-convergence) : 7

| Méthode | Log-loss moyen (plus bas = mieux) |
|---|---|
| multiplicatif | 0.97382 |
| Shin | 0.97334 |

## Brier par tranche de cotes de la sélection

| Tranche | Multiplicatif | Shin | n |
|---|---|---|---|
| 1.0–1.5 | 0.17538 | 0.17475 | 952 |
| 1.5–2.5 | 0.24583 | 0.24579 | 3999 |
| 2.5–4.0 | 0.20621 | 0.20620 | 7448 |
| 4.0–7.0 | 0.15569 | 0.15568 | 3804 |
| 7.0–∞ | 0.06492 | 0.06459 | 1128 |

## Verdict : **shin** (écart de log-loss 0.000483 par match)

Règle de gel J3 : si l'écart est négligeable, Shin reste champion par défaut (protection structurelle contre le biais favori-outsider). Les deux méthodes sont loggées à vie dans le Grand Livre quoi qu'il arrive.
