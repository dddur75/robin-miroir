# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — L'AUDITEUR (M20).
Contrôle d'intégrité automatique, exécuté chaque nuit après le règlement.
Il ne corrige RIEN (le Grand Livre est append-only) : il vérifie, il signale.
Résultat écrit dans data/sante.json (lu par le dashboard et le rapport).
Anomalie => alerte Telegram + issue GitHub.
"""
import json
import sys

import config as C
import utils as U


def executer(silencieux=False):
    checks = []
    ok_global = True

    def check(nom, ok, detail=""):
        nonlocal ok_global
        checks.append({"nom": nom, "ok": bool(ok), "detail": detail})
        if not ok:
            ok_global = False

    # 1-2. Les journaux se lisent (append-only intact)
    try:
        livre = U.charger_livre()
        check("Grand Livre lisible", True, f"{len(livre)} enregistrements")
    except Exception as e:
        livre = []
        check("Grand Livre lisible", False, str(e))
    try:
        shadow = U.charger_shadow()
        check("Journal shadow lisible", True, f"{len(shadow)} enregistrements")
    except Exception as e:
        shadow = []
        check("Journal shadow lisible", False, str(e))

    # 3. Pas de PARI dupliqué (M8)
    ids_pari = [r["id"] for r in livre if r.get("type") == "PARI"]
    check("IDs de paris uniques", len(ids_pari) == len(set(ids_pari)),
          f"{len(ids_pari) - len(set(ids_pari))} doublon(s)")

    # 4-5. Pas de CLOTURE/REGLEMENT orphelin
    ids = set(ids_pari)
    orph_c = [r for r in livre if r.get("type") == "CLOTURE" and r["id"] not in ids]
    orph_r = [r for r in livre if r.get("type") == "REGLEMENT" and r["id"] not in ids]
    check("Aucune clôture orpheline", not orph_c, f"{len(orph_c)}")
    check("Aucun règlement orphelin", not orph_r, f"{len(orph_r)}")

    # 6. Chaque pari a au plus 1 règlement (le pliage l'impose, on vérifie le brut)
    regs = [r["id"] for r in livre if r.get("type") == "REGLEMENT"]
    check("Un seul règlement par pari", len(regs) == len(set(regs)),
          f"{len(regs) - len(set(regs))} doublon(s) bruts")

    # 7. Clôtures manquantes (officiel) sous contrôle
    import metriques
    m = metriques.calculer(livre, shadow)
    off = m["officiel"]
    if off["n_regles"] >= 10:
        ratio = off["clotures_manquantes"] / off["n_regles"]
        check("Clôtures manquantes ≤ 10 %", ratio <= 0.10, f"{ratio:.0%}")
    else:
        check("Clôtures manquantes ≤ 10 %", True, "n < 10, pas encore évaluable")

    # 8. Paris en souffrance (> 48 h sans règlement)
    from datetime import timezone
    n_tard = 0
    for e in U.etat_paris(livre).values():
        if e["reglement"] is None:
            age = (U.maintenant_utc() - U.parse_iso(e["pari"]["ko"])).total_seconds() / 3600
            if age > C.ALERTE_UNSETTLED_H:
                n_tard += 1
    check("Paris en souffrance (> 48 h)", n_tard == 0, f"{n_tard}")

    # 9-10. Fichiers d'état valides
    try:
        U.charger_etat()
        check("state.json valide", True)
    except Exception as e:
        check("state.json valide", False, str(e))
    try:
        U.charger_json(U.TEAM_MAPPING, {})
        check("team_mapping.json valide", True)
    except Exception as e:
        check("team_mapping.json valide", False, str(e))

    # 11. Crédits API connus
    etat = U.charger_etat()
    credits = etat.get("credits_restants")
    check("Crédits API connus", credits is not None, str(credits))

    sante = {"ts": U.iso(U.maintenant_utc()), "ok": ok_global, "checks": checks}
    U.sauver_json(U.SANTE, sante)

    n_ok = sum(1 for c in checks if c["ok"])
    print(f"[AUDITEUR] {n_ok}/{len(checks)} contrôles verts.")
    for c in checks:
        print(f"   {'✔' if c['ok'] else '✘'} {c['nom']}"
              + (f" — {c['detail']}" if c["detail"] else ""))

    if not ok_global and not silencieux:
        rates = ", ".join(c["nom"] for c in checks if not c["ok"])
        U.telegram(f"🔎 ROBIN MIROIR — l'Auditeur a trouvé une anomalie : {rates}")
        U.creer_issue(
            f"🔎 Auditeur — anomalie détectée ({U.maintenant_utc().strftime('%Y-%m-%d')})",
            "Contrôles en échec : " + rates
            + "\n\nDétail complet dans `data/sante.json`. "
              "Le Grand Livre n'est jamais modifié par l'Auditeur.",
        )
    return ok_global


if __name__ == "__main__":
    try:
        executer()
    except Exception as e:
        U.telegram(f"🚨 ROBIN MIROIR — AUDITEUR EN ÉCHEC : {e}")
        sys.exit(1)
