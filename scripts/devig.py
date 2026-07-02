# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — Dévigage des cotes Pinnacle.
Deux méthodes, toutes deux loggées à vie :
  - multiplicatif : p_i = (1/o_i) / somme(1/o_j)   (simple, ne corrige pas le
    biais favori-outsider)
  - Shin (1992)   : modélise la part d'argent "informé" z ; attribue plus de
    marge aux outsiders -> résiste au biais favori-outsider.
Si Shin ne converge pas (rare), repli multiplicatif + drapeau loggé.
"""
import math


def multiplicatif(cotes):
    """cotes: liste de cotes décimales -> liste de probabilités (somme = 1)."""
    inv = [1.0 / c for c in cotes]
    s = sum(inv)
    return [x / s for x in inv]


def shin(cotes, max_iter=1000, tol=1e-12):
    """
    Méthode de Shin pour n issues.
    p_i = (sqrt(z^2 + 4(1-z) * pi_i^2 / beta) - z) / (2 (1-z))
    avec pi_i = 1/o_i, beta = somme(pi), z résolu par point fixe :
    z <- (somme_i sqrt(z^2 + 4(1-z) pi_i^2 / beta) - 2) / (n - 2)
    Retourne (probas, z, converge: bool). Pour n < 3, repli multiplicatif.
    """
    n = len(cotes)
    pi = [1.0 / c for c in cotes]
    beta = sum(pi)
    if beta <= 1.0 or n < 3:
        return multiplicatif(cotes), 0.0, False
    z = 0.0
    for _ in range(max_iter):
        racines = [math.sqrt(z * z + 4.0 * (1.0 - z) * (p * p) / beta) for p in pi]
        z_new = (sum(racines) - 2.0) / (n - 2)
        z_new = min(max(z_new, 0.0), 0.4)  # borne de sécurité
        if abs(z_new - z) < tol:
            z = z_new
            break
        z = z_new
    else:
        return multiplicatif(cotes), 0.0, False
    if z >= 1.0:
        return multiplicatif(cotes), 0.0, False
    probs = [
        (math.sqrt(z * z + 4.0 * (1.0 - z) * (p * p) / beta) - z) / (2.0 * (1.0 - z))
        for p in pi
    ]
    s = sum(probs)
    probs = [p / s for p in probs]  # renormalisation numérique (écart ~1e-12)
    return probs, z, True


def deviger(cotes, champion="shin"):
    """
    Retourne un dict complet, les DEUX méthodes sont toujours calculées :
    { 'multiplicatif': [...], 'shin': [...], 'z': float,
      'champion': [...], 'methode': 'shin'|'multiplicatif'|'multiplicatif_repli' }
    """
    p_mult = multiplicatif(cotes)
    p_shin, z, ok = shin(cotes)
    if champion == "shin":
        if ok:
            p_champ, methode = p_shin, "shin"
        else:
            p_champ, methode = p_mult, "multiplicatif_repli"
    else:
        p_champ, methode = p_mult, "multiplicatif"
    return {
        "multiplicatif": p_mult,
        "shin": p_shin,
        "z": z,
        "champion": p_champ,
        "methode": methode,
    }


def marge(cotes):
    """Marge (overround) du book : somme(1/o) - 1, en fraction (ex 0.031 = 3,1 %)."""
    return sum(1.0 / c for c in cotes) - 1.0


if __name__ == "__main__":
    # Auto-test : marché 1N2 typique Pinnacle
    cotes = [2.10, 3.60, 3.40]
    d = deviger(cotes)
    assert abs(sum(d["multiplicatif"]) - 1.0) < 1e-9
    assert abs(sum(d["shin"]) - 1.0) < 1e-9
    assert d["methode"] == "shin"
    # Shin doit donner MOINS de proba que le multiplicatif à l'outsider le + long
    i_out = cotes.index(max(cotes))
    assert d["shin"][i_out] < d["multiplicatif"][i_out]
    # et PLUS au favori
    i_fav = cotes.index(min(cotes))
    assert d["shin"][i_fav] > d["multiplicatif"][i_fav]
    print("devig.py OK — mult:", [round(p, 4) for p in d["multiplicatif"]],
          "| shin:", [round(p, 4) for p in d["shin"]], "| z =", round(d["z"], 5),
          "| marge =", round(marge(cotes) * 100, 2), "%")
