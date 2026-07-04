# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — RAPPORT HEBDO (dimanche soir).
10 lignes max, langage simple, AUCUNE décision demandée à David (protocole).
Envoyé sur Telegram si configuré, et archivé dans rapports/.
"""
import os
import sys
import traceback

import config as C
import utils as U
import metriques


def construire():
    m = metriques.calculer()
    off = m["officiel"]
    semaine = metriques.paris_semaine(7)
    sem_off = [e for e in semaine if e["pari"]["phase"] == "OFFICIEL"]
    sem_regles = [e for e in sem_off if e["reglement"] is not None]
    clv_sem = [e["cloture"]["clv"] for e in sem_regles if e["cloture"] is not None]
    pnl_sem = sum(e["reglement"]["pnl"] for e in sem_regles)

    lignes = [m["statut"], ""]
    if m["phase_courante"] == "RODAGE":
        rod = m["rodage"]
        lignes += [
            f"Rodage : {rod['n_declenches']} déclenchement(s) d'essai, "
            f"{rod['matchs_vus']} match(s) vus, "
            f"couverture Unibet {rod['couverture_unibet']:.0%}."
            if rod["couverture_unibet"] is not None else
            f"Rodage : {rod['n_declenches']} déclenchement(s) d'essai, "
            f"{rod['matchs_vus']} match(s) vus.",
        ]
    else:
        clv_s = (sum(clv_sem) / len(clv_sem)) if clv_sem else None
        lignes += [
            f"Semaine : {len(sem_off)} pari(s) papier, {len(sem_regles)} réglé(s), "
            f"P&L {pnl_sem:+.0f} u"
            + (f", CLV semaine {clv_s:+.2%}." if clv_s is not None else "."),
            f"Cumul : N = {off['n_regles']}/{C.N_VERDICT}"
            + (f", CLV {off['clv_moyen']:+.2%}" if off["clv_moyen"] is not None else "")
            + (f", ROI {off['roi']:+.1%}" if off["roi"] is not None else "")
            + f", P&L {off['pnl']:+.0f} u.",
        ]
    if off["clotures_manquantes"]:
        lignes.append(f"⚠️ {off['clotures_manquantes']} clôture(s) manquante(s) — "
                      "fiabilité de capture à surveiller.")
    if off.get("n_void"):
        lignes.append(f"{off['n_void']} match(s) reporté(s) -> VOID, hors test (M18).")
    agents_ko = [a["nom"] for a in m["agents"] if a["statut"] not in ("OK",)]
    if agents_ko:
        lignes.append("🤖 Agents à surveiller : " + ", ".join(agents_ko) + ".")
    else:
        lignes.append("🤖 Les 5 agents sont opérationnels.")
    if m["credits"] is not None:
        lignes.append(f"Crédits API restants : {m['credits']}"
                      + (" (délestage actif)." if m["delestage"] else "."))
    lignes.append("Aucune action attendue de ta part.")
    return "🪞 ROBIN MIROIR — rapport hebdo\n" + "\n".join(lignes)


def executer():
    texte = construire()
    print(texte)
    U.telegram(texte)
    os.makedirs(U.RAPPORTS, exist_ok=True)
    nom = os.path.join(U.RAPPORTS, f"hebdo_{U.maintenant_utc().strftime('%Y-%m-%d')}.md")
    with open(nom, "w", encoding="utf-8") as f:
        f.write(texte + "\n")
    etat = U.charger_etat()
    etat["dernier_rapport"] = U.iso(U.maintenant_utc())
    U.sauver_etat(etat)
    import dashboard
    dashboard.generer()


if __name__ == "__main__":
    try:
        executer()
    except Exception as e:
        traceback.print_exc()
        U.telegram(f"🚨 ROBIN MIROIR — RAPPORT EN ÉCHEC : {e}")
        sys.exit(1)
