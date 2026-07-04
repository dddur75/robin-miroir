# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — Métriques. Une seule définition, utilisée partout.
Les 4 métriques gelées (phase OFFICIELLE uniquement) :
  1. CLV moyen        2. N déclenchements (réglés) / 200
  3. ROI flat         4. Écart moyen Unibet vs sharp
"""
import math
from datetime import timedelta

import config as C
import utils as U


def _age_h(ts_iso):
    if not ts_iso:
        return None
    try:
        return (U.maintenant_utc() - U.parse_iso(ts_iso)).total_seconds() / 3600
    except Exception:
        return None


def agents_etat(etat, sante):
    """Santé des 5 agents : OK / RETARD / JAMAIS, avec l'âge de la dernière action.
    Tolérances larges : on signale un agent en retard, on ne crie pas pour 20 min."""
    a_cap = _age_h(etat.get("derniere_capture"))
    a_reg = _age_h(etat.get("dernier_reglement"))
    a_rap = _age_h(etat.get("dernier_rapport"))
    a_aud = _age_h(sante.get("ts"))

    def statut(age, tolerance_h):
        if age is None:
            return "JAMAIS"
        return "OK" if age <= tolerance_h else "RETARD"

    livre_ok = True
    try:
        U.charger_livre()
        U.charger_shadow()
    except Exception:
        livre_ok = False
    return [
        {"nom": "Guetteur", "role": "capture des cotes",
         "statut": statut(a_cap, 2), "age_h": a_cap},
        {"nom": "Greffier", "role": "grand livre",
         "statut": "OK" if livre_ok else "ERREUR", "age_h": a_cap},
        {"nom": "Arbitre", "role": "règlement des paris",
         "statut": statut(a_reg, 30), "age_h": a_reg},
        {"nom": "Auditeur", "role": "contrôle d'intégrité",
         "statut": ("ANOMALIE" if sante and not sante.get("ok", True)
                    else statut(a_aud, 30)), "age_h": a_aud},
        {"nom": "Messager", "role": "rapports et alertes",
         "statut": statut(a_rap, 24 * 8), "age_h": a_rap},
    ]


def calculer(livre=None, shadow=None):
    etats = U.etat_paris(livre)
    shadow = U.charger_shadow() if shadow is None else shadow

    def bloc(phase):
        paris = [e for e in etats.values() if e["pari"]["phase"] == phase]
        finis = [e for e in paris if e["reglement"] is not None]
        # M18 : les VOID (matchs reportés) sont hors test — mise rendue, exclus de N
        regles = [e for e in finis if e["reglement"]["issue"] in ("GAGNE", "PERDU")]
        voids = [e for e in finis if e["reglement"]["issue"] == "VOID"]
        clvs = [e["cloture"]["clv"] for e in regles if e["cloture"] is not None]
        pnl = sum(e["reglement"]["pnl"] for e in regles)
        n = len(regles)
        roi = pnl / (n * C.MISE_FLAT) if n else None
        clv_moyen = sum(clvs) / len(clvs) if clvs else None
        # IC95 sur le CLV moyen (M15)
        ic95 = None
        if len(clvs) >= 2:
            m = clv_moyen
            var = sum((x - m) ** 2 for x in clvs) / (len(clvs) - 1)
            ic95 = 1.96 * math.sqrt(var / len(clvs))
        obs = [r for r in shadow if r.get("type") == "OBS"
               and r.get("phase") == phase and "edge" in r]
        ecart = sum(r["edge"] for r in obs) / len(obs) if obs else None
        no_quote = sum(1 for r in shadow if r.get("type") == "OBS"
                       and r.get("phase") == phase
                       and r.get("statut") == "NO_QUOTE_UNIBET")
        stale = sum(1 for r in shadow if r.get("type") == "OBS"
                    and r.get("phase") == phase and r.get("statut") == "STALE")
        matchs_vus = len({r["event_id"] for r in shadow
                          if r.get("type") == "OBS" and r.get("phase") == phase})
        couverture = (1 - no_quote / matchs_vus) if matchs_vus else None
        clot_manquantes = sum(1 for e in regles if e["cloture"] is None)
        return {
            "n_declenches": len(paris),
            "n_regles": n,
            "n_void": len(voids),
            "n_attente": len(paris) - len(finis),
            "pnl": round(pnl, 2),
            "roi": roi,
            "clv_moyen": clv_moyen,
            "clv_n": len(clvs),
            "ic95": ic95,
            "ecart_moyen": ecart,
            "obs": len(obs),
            "stale": stale,
            "matchs_vus": matchs_vus,
            "couverture_unibet": couverture,
            "clotures_manquantes": clot_manquantes,
        }

    etat = U.charger_etat()
    sante = U.charger_json(getattr(U, "SANTE", U.STATE.replace("state.json", "sante.json")), {})
    m = {
        "officiel": bloc("OFFICIEL"),
        "rodage": bloc("RODAGE"),
        "phase_courante": U.phase_du_jour(),
        "credits": etat.get("credits_restants"),
        "derniere_capture": etat.get("derniere_capture"),
        "dernier_reglement": etat.get("dernier_reglement"),
        "dernier_rapport": etat.get("dernier_rapport"),
        "delestage": bool(etat.get("delestage_mois")),
        "sante": sante,
        "agents": agents_etat(etat, sante),
    }

    # Statut M17 — une phrase, lisible en 3 secondes
    off = m["officiel"]
    n, clv = off["n_regles"], off["clv_moyen"]
    if m["phase_courante"] == "RODAGE":
        m["statut"] = ("🔧 RODAGE — la machine se teste, rien ne compte encore "
                       f"(ouverture officielle le {C.DEBUT_OFFICIEL.strftime('%d/%m/%Y')})")
        m["couleur"] = "rodage"
    elif n >= C.N_VERDICT:
        if clv is not None and clv <= C.CLV_CRITERE_MORT:
            m["statut"] = f"⬛ VERDICT ATTEINT — CLV {clv:+.2%} ≤ 0 : KILL. Clôture propre."
            m["couleur"] = "alerte"
        else:
            m["statut"] = (f"🟩 VERDICT ATTEINT — CLV {clv:+.2%} > 0 : "
                           "convoquer le conseil (GO/NO-GO).")
            m["couleur"] = "ok"
    elif n >= C.N_ALERTE_SECURITE and clv is not None and clv <= C.CLV_SEUIL_ALERTE:
        m["statut"] = f"🚨 SEUIL D'ALERTE — N={n}, CLV {clv:+.2%}. Poursuite jusqu'à N=200."
        m["couleur"] = "alerte"
    elif clv is not None and clv < 0:
        m["statut"] = f"🟠 Tendance négative — N={n}/{C.N_VERDICT}, CLV {clv:+.2%}."
        m["couleur"] = "rodage"
    else:
        detail = f"CLV {clv:+.2%}" if clv is not None else "CLV en attente"
        m["statut"] = f"✅ RAS — N={n}/{C.N_VERDICT}, {detail}. La machine tourne."
        m["couleur"] = "ok"
    return m


def paris_semaine(jours=7):
    """Pour le rapport hebdo : paris (toutes phases) capturés ces N derniers jours."""
    limite = U.maintenant_utc() - timedelta(days=jours)
    out = []
    for e in U.etat_paris().values():
        if U.parse_iso(e["pari"]["ts_capture"]) >= limite:
            out.append(e)
    return out
