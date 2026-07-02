# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — LABO : duel des dévigages (multiplicatif vs Shin).

Données : CSV historiques gratuits de Football-Data.co.uk,
colonnes PSCH / PSCD / PSCA = cotes Pinnacle de CLÔTURE, FTR = résultat.
Mesures :
  - log-loss (plus bas = mieux calibré) sur l'issue réelle du match
  - Brier par tranche de cotes de la sélection (où vit le biais favori-outsider)
Verdict écrit dans labo/rapport_devig.md — sert au gel J3 (config.DEVIG_CHAMPION).
Ce script tourne au LABO, jamais sur le flux live.
"""
import csv
import io
import math
import os
import sys

import utils as U
from devig import multiplicatif, shin

SAISONS = ["2324", "2425", "2526"]
LIGUES = ["E0", "E1", "F1", "D1", "I1", "SP1"]   # PL, Championship, L1, BuLi, SA, Liga
URL = "https://www.football-data.co.uk/mmz4281/{saison}/{ligue}.csv"
TRANCHES = [(1.0, 1.5), (1.5, 2.5), (2.5, 4.0), (4.0, 7.0), (7.0, 1e9)]


def telecharger(saison, ligue):
    import requests
    r = requests.get(URL.format(saison=saison, ligue=ligue), timeout=60)
    r.raise_for_status()
    return r.content.decode("latin-1", errors="replace")


def lignes_valides(texte):
    for row in csv.DictReader(io.StringIO(texte)):
        try:
            cotes = [float(row["PSCH"]), float(row["PSCD"]), float(row["PSCA"])]
            ftr = row["FTR"].strip()
            if ftr in ("H", "D", "A") and all(c > 1.0 for c in cotes):
                yield cotes, ftr
        except (KeyError, ValueError, TypeError):
            continue


def executer():
    idx = {"H": 0, "D": 1, "A": 2}
    ll = {"multiplicatif": 0.0, "shin": 0.0}
    brier = {m: {t: [0.0, 0] for t in TRANCHES} for m in ll}
    n, shin_ko = 0, 0

    for saison in SAISONS:
        for ligue in LIGUES:
            try:
                texte = telecharger(saison, ligue)
            except Exception as e:
                print(f"[LABO] {saison}/{ligue} indisponible : {e}")
                continue
            for cotes, ftr in lignes_valides(texte):
                p_m = multiplicatif(cotes)
                p_s, _, ok = shin(cotes)
                if not ok:
                    shin_ko += 1
                i = idx[ftr]
                ll["multiplicatif"] += -math.log(max(p_m[i], 1e-12))
                ll["shin"] += -math.log(max(p_s[i], 1e-12))
                for j, cote in enumerate(cotes):
                    y = 1.0 if j == i else 0.0
                    for t in TRANCHES:
                        if t[0] <= cote < t[1]:
                            for nom, p in (("multiplicatif", p_m), ("shin", p_s)):
                                brier[nom][t][0] += (p[j] - y) ** 2
                                brier[nom][t][1] += 1
                            break
                n += 1

    if n == 0:
        raise RuntimeError("Aucune donnée téléchargée — vérifier l'accès réseau.")

    gagnant = min(ll, key=lambda k: ll[k] / n)
    lignes = [
        "# LABO — Duel des dévigages (clôtures Pinnacle, Football-Data.co.uk)",
        "",
        f"Matchs analysés : **{n}** ({', '.join(LIGUES)} × saisons {', '.join(SAISONS)})",
        f"Replis Shin (non-convergence) : {shin_ko}",
        "",
        "| Méthode | Log-loss moyen (plus bas = mieux) |",
        "|---|---|",
        f"| multiplicatif | {ll['multiplicatif'] / n:.5f} |",
        f"| Shin | {ll['shin'] / n:.5f} |",
        "",
        "## Brier par tranche de cotes de la sélection",
        "",
        "| Tranche | Multiplicatif | Shin | n |",
        "|---|---|---|---|",
    ]
    for t in TRANCHES:
        bm, cnt = brier["multiplicatif"][t]
        bs, _ = brier["shin"][t]
        if cnt:
            lignes.append(
                f"| {t[0]:.1f}–{('∞' if t[1] > 100 else f'{t[1]:.1f}')} "
                f"| {bm / cnt:.5f} | {bs / cnt:.5f} | {cnt} |"
            )
    ecart = abs(ll["multiplicatif"] - ll["shin"]) / n
    lignes += [
        "",
        f"## Verdict : **{gagnant}** (écart de log-loss {ecart:.6f} par match)",
        "",
        "Règle de gel J3 : si l'écart est négligeable, Shin reste champion par défaut "
        "(protection structurelle contre le biais favori-outsider). Les deux méthodes "
        "sont loggées à vie dans le Grand Livre quoi qu'il arrive.",
    ]
    os.makedirs(U.LABO, exist_ok=True)
    with open(os.path.join(U.LABO, "rapport_devig.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    print("\n".join(lignes))


if __name__ == "__main__":
    try:
        executer()
    except Exception as e:
        print(f"ÉCHEC LABO : {e}", file=sys.stderr)
        sys.exit(1)
