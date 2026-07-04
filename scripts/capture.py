# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — CAPTURE (toutes les 30 min via GitHub Actions).

Déroulé d'un run :
 1. /v4/sports (0 crédit)   -> quelles ligues du périmètre sont en saison
 2. /v4/sports/{s}/events   -> quels matchs entrent en fenêtre T-2 ou clôture
 3. /v4/sports/{s}/odds     -> UN appel par ligue concernée (1 crédit),
    bookmakers=pinnacle,unibet_fr : les deux prix, même seconde.
 4. Dévigage Shin+mult -> règles gelées M1..M5 -> PARI (papier) ou SHADOW.
 5. Clôtures [T-15,T-2] des paris déclenchés (1 crédit / match déclenché).
 6. Dashboard régénéré. Échec = bruyant (alerte + exit 1), jamais silencieux.
"""
import sys
import traceback

import config as C
import utils as U
from devig import deviger, marge

BASE = "https://api.the-odds-api.com/v4"


# --------------------------------------------------------------- appels API
def _cle_api():
    import os
    cle = os.environ.get("ODDS_API_KEY")
    if not cle:
        raise RuntimeError("Secret ODDS_API_KEY absent.")
    return cle


def _maj_credits(etat, entetes):
    restant = entetes.get("x-requests-remaining") or entetes.get("X-Requests-Remaining")
    if restant is not None:
        try:
            etat["credits_restants"] = int(float(restant))
        except ValueError:
            pass
    etat["derniere_capture"] = U.iso(U.maintenant_utc())


def sports_actifs(cle, etat):
    data, entetes = U.http_get_json(f"{BASE}/sports/", params={"apiKey": cle})
    _maj_credits(etat, entetes)
    actifs = {s["key"] for s in data if s.get("active")}
    connus = {s["key"] for s in data}
    for sport_key, _, label in C.LIGUES:
        if sport_key not in connus:
            print(f"[AVERTISSEMENT] sport_key inconnu de l'API : {sport_key} ({label})")
    return actifs


def evenements(cle, sport_key, etat):
    data, entetes = U.http_get_json(
        f"{BASE}/sports/{sport_key}/events", params={"apiKey": cle}
    )
    _maj_credits(etat, entetes)
    return data


def cotes_ligue(cle, sport_key, etat):
    data, entetes = U.http_get_json(
        f"{BASE}/sports/{sport_key}/odds",
        params={
            "apiKey": cle,
            "markets": "h2h",
            "bookmakers": f"{C.BOOKMAKER_SHARP},{C.BOOKMAKER_SOFT}",
            "oddsFormat": "decimal",
        },
    )
    _maj_credits(etat, entetes)
    return data


def cotes_evenement(cle, sport_key, event_id, etat):
    data, entetes = U.http_get_json(
        f"{BASE}/sports/{sport_key}/events/{event_id}/odds",
        params={
            "apiKey": cle,
            "markets": "h2h",
            "bookmakers": C.BOOKMAKER_SHARP,
            "oddsFormat": "decimal",
        },
    )
    _maj_credits(etat, entetes)
    return data


# --------------------------------------------------------------- extraction
def _h2h(ev, bookmaker):
    """Retourne ({'H','D','A'}: cotes, last_update ISO ou None), ou (None, None)."""
    for bk in ev.get("bookmakers", []):
        cle_bk = bk.get("key")
        if cle_bk not in C.BOOKMAKERS_AUTORISES:
            # Assertion dure anti-confusion (audit S2) : un book non demandé
            # dans la réponse = anomalie de pipeline -> échec bruyant.
            raise RuntimeError(f"Bookmaker inattendu dans la réponse : {cle_bk}")
        if cle_bk != bookmaker:
            continue
        for m in bk.get("markets", []):
            if m.get("key") != "h2h":
                continue
            cotes = {}
            for o in m.get("outcomes", []):
                if o["name"] == ev["home_team"]:
                    cotes["H"] = float(o["price"])
                elif o["name"] == ev["away_team"]:
                    cotes["A"] = float(o["price"])
                elif o["name"].lower() == "draw":
                    cotes["D"] = float(o["price"])
            if len(cotes) == 3:
                return cotes, (m.get("last_update") or bk.get("last_update"))
    return None, None


def _age_minutes(ts_iso):
    """Âge d'un horodatage ISO en minutes (None si absent/illisible)."""
    if not ts_iso:
        return None
    try:
        return (U.maintenant_utc() - U.parse_iso(ts_iso)).total_seconds() / 60.0
    except Exception:
        return None


# ------------------------------------------------------------ cœur du système
def evaluer_evenement(ev, ligue_label, fd_code, etat, compteur_jour):
    """Applique le protocole gelé à UN match. Écrit OBS / SHADOW / PARI."""
    ts = U.iso(U.maintenant_utc())
    phase = U.phase_du_jour()
    pin, lu_pin = _h2h(ev, C.BOOKMAKER_SHARP)
    uni, lu_uni = _h2h(ev, C.BOOKMAKER_SOFT)
    base_obs = {
        "type": "OBS", "ts": ts, "phase": phase, "ligue": ligue_label,
        "event_id": ev["id"], "ko": ev["commence_time"],
        "match": f'{ev["home_team"]} - {ev["away_team"]}',
    }
    if pin is None:
        U.ajouter(U.SHADOW, dict(base_obs, statut="NO_PINNACLE"))
        return 0
    if uni is None:
        U.ajouter(U.SHADOW, dict(base_obs, statut="NO_QUOTE_UNIBET"))
        return 0

    # M19 — fraîcheur : une cote périmée n'est pas un prix réel, on ne parie pas dessus
    age_p, age_u = _age_minutes(lu_pin), _age_minutes(lu_uni)
    if (age_p is not None and age_p > C.STALE_MINUTES) or \
       (age_u is not None and age_u > C.STALE_MINUTES):
        U.ajouter(U.SHADOW, dict(
            base_obs, statut="STALE",
            age_p_min=round(age_p, 1) if age_p is not None else None,
            age_u_min=round(age_u, 1) if age_u is not None else None,
        ))
        return 0

    ordre = ["H", "D", "A"]
    cotes_pin = [pin[m] for m in ordre]
    d = deviger(cotes_pin, C.DEVIG_CHAMPION)
    marge_pin = marge(cotes_pin)

    candidats = []
    for i, m in enumerate(ordre):
        p_vraie = d["champion"][i]
        cote_juste = 1.0 / p_vraie
        edge = uni[m] * p_vraie - 1.0
        obs = dict(
            base_obs, m=m, cu=round(uni[m], 3), cp=round(pin[m], 3),
            pv=round(p_vraie, 5), edge=round(edge, 5),
        )
        # Filtres gelés, dans l'ordre du protocole
        if uni[m] > pin[m] * C.RATIO_SUSPECT:                       # M2
            obs["statut"] = "SUSPECT"
        elif not (C.BANDE_COTES[0] <= uni[m] <= C.BANDE_COTES[1]):  # M1
            obs["statut"] = "HORS_BANDE"
        elif uni[m] >= cote_juste * C.SEUIL_EDGE:                   # déclencheur
            obs["statut"] = "DECLENCHEUR"
            candidats.append((edge, m, obs))
        else:
            obs["statut"] = "SOUS_SEUIL"
        U.ajouter(U.SHADOW, obs)

    if not candidats:
        return 0

    # M4 : un seul pari par match — le plus gros edge
    candidats.sort(reverse=True, key=lambda x: x[0])
    for edge, m, obs in candidats[1:]:
        U.ajouter(U.SHADOW, dict(obs, statut="SECOND_PICK"))

    edge, m, obs = candidats[0]

    # M5 : cap quotidien
    if compteur_jour["n"] >= C.MAX_PARIS_PAR_JOUR:
        U.ajouter(U.SHADOW, dict(obs, statut="CAP_JOURNALIER"))
        if not compteur_jour.get("alerte_cap"):
            U.telegram("⚠️ ROBIN MIROIR — cap journalier atteint (journée anormale ?)")
            compteur_jour["alerte_cap"] = True
        return 0

    bid = U.id_pari(ev["id"], m)
    if bid in etat.get("paris_connus", []):                          # M8
        return 0

    noms = {"H": ev["home_team"], "D": "Match nul", "A": ev["away_team"]}
    pari = {
        "type": "PARI", "id": bid, "phase": phase, "ts_capture": ts,
        "ligue": ligue_label, "fd_code": fd_code, "event_id": ev["id"],
        "ko": ev["commence_time"],
        "home": ev["home_team"], "away": ev["away_team"],
        "marche": m, "selection": noms[m],
        "cote_unibet": round(uni[m], 3),
        "cote_pinnacle": round(pin[m], 3),
        "p_vraie": round(d["champion"][ordre.index(m)], 5),
        "p_shin": round(d["shin"][ordre.index(m)], 5),
        "p_mult": round(d["multiplicatif"][ordre.index(m)], 5),
        "methode": d["methode"],
        "edge": round(edge, 5),
        "marge_pinnacle": round(marge_pin, 5),
        "age_p_min": round(age_p, 1) if age_p is not None else None,
        "age_u_min": round(age_u, 1) if age_u is not None else None,
        "mise": C.MISE_FLAT,
    }
    pari["sport_key"] = ev.get("sport_key", "")
    U.ajouter(U.GRAND_LIVRE, pari)
    etat.setdefault("paris_connus", []).append(bid)
    compteur_jour["n"] += 1
    print(f"[PARI {phase}] {ev['home_team']} - {ev['away_team']} | {noms[m]}"
          f" @ {uni[m]} (juste {round(1 / pari['p_vraie'], 2)}, edge {edge:+.1%})")
    return 1


def capturer_clotures(cle, etats_paris, etat):
    """M6 : cote Pinnacle de clôture pour les paris déclenchés, [T-15, T-2]."""
    maintenant = U.maintenant_utc()
    n = 0
    for bid, e in etats_paris.items():
        if e["cloture"] is not None or e["reglement"] is not None:
            continue
        pari = e["pari"]
        try:
            ko = U.parse_iso(pari["ko"])
        except Exception:
            continue
        minutes = (ko - maintenant).total_seconds() / 60.0
        if not (C.FENETRE_CLOTURE[1] <= minutes <= C.FENETRE_CLOTURE[0]):
            continue
        ev = cotes_evenement(cle, pari.get("sport_key") or _sport_de(pari), pari["event_id"], etat)
        pin, lu_pin = _h2h(ev, C.BOOKMAKER_SHARP) if ev else (None, None)
        if pin is None:
            print(f"[CLOTURE] Pinnacle indisponible pour {pari['event_id']}")
            continue
        age_p = _age_minutes(lu_pin)
        ordre = ["H", "D", "A"]
        d = deviger([pin[m] for m in ordre], C.DEVIG_CHAMPION)
        i = ordre.index(pari["marche"])
        p_close = d["champion"][i]
        clv = pari["cote_unibet"] * p_close - 1.0
        U.ajouter(U.GRAND_LIVRE, {
            "type": "CLOTURE", "id": bid, "ts": U.iso(maintenant),
            "cote_pinnacle_cloture": round(pin[pari["marche"]], 3),
            "p_close": round(p_close, 5),
            "p_close_shin": round(d["shin"][i], 5),
            "p_close_mult": round(d["multiplicatif"][i], 5),
            "age_p_min": round(age_p, 1) if age_p is not None else None,
            "clv": round(clv, 5),
        })
        n += 1
        print(f"[CLOTURE] {pari['home']} - {pari['away']} | CLV {clv:+.2%}")
    return n


def _sport_de(pari):
    for sk, fd, label in C.LIGUES:
        if label == pari.get("ligue"):
            return sk
    raise RuntimeError(f"Ligue inconnue dans le pari : {pari.get('ligue')}")


# ---------------------------------------------------------------------- main
def executer():
    cle = _cle_api()
    etat = U.charger_etat()
    maintenant = U.maintenant_utc()
    aujourd_hui = maintenant.strftime("%Y-%m-%d")
    mois = maintenant.strftime("%Y-%m")

    # Délestage pré-enregistré : crédits bas => 5 ligues prioritaires ce mois-ci
    ligues = C.LIGUES
    if etat.get("delestage_mois") == mois:
        ligues = C.LIGUES[: C.LIGUES_DELESTAGE]

    actifs = sports_actifs(cle, etat)
    en_saison = [(sk, fd, lb) for sk, fd, lb in ligues if sk in actifs]
    print(f"[INFO] Ligues en saison : {[lb for _, _, lb in en_saison] or 'aucune'}")

    # Compteur M5 du jour (paris déjà pris aujourd'hui, toutes phases)
    etats = U.etat_paris()
    n_jour = sum(
        1 for e in etats.values()
        if e["pari"]["ts_capture"].startswith(aujourd_hui)
    )
    compteur_jour = {"n": n_jour}

    # Fenêtre T-2 : quelles ligues ont des matchs à capturer ?
    traites = etat.setdefault("events_traites", {})
    nouveaux = 0
    for sk, fd, label in en_saison:
        evs = evenements(cle, sk, etat)
        en_fenetre = []
        for ev in evs:
            try:
                ko = U.parse_iso(ev["commence_time"])
            except Exception:
                continue
            minutes = (ko - maintenant).total_seconds() / 60.0
            if C.FENETRE_T2[1] <= minutes <= C.FENETRE_T2[0] and ev["id"] not in traites:
                en_fenetre.append(ev["id"])
        if not en_fenetre:
            continue
        for ev in cotes_ligue(cle, sk, etat):
            if ev["id"] not in en_fenetre:
                continue
            ev.setdefault("sport_key", sk)
            nouveaux += evaluer_evenement(ev, label, fd, etat, compteur_jour)
            traites[ev["id"]] = U.iso(maintenant)

    # Fenêtre clôture des paris déclenchés
    clotures = capturer_clotures(cle, U.etat_paris(), etat)

    # Ménage de l'état (events > 3 jours) + alerte crédits / délestage
    limite = maintenant.timestamp() - 3 * 86400
    etat["events_traites"] = {
        k: v for k, v in traites.items() if U.parse_iso(v).timestamp() > limite
    }
    credits = etat.get("credits_restants")
    if credits is not None and credits < C.CREDITS_ALERTE and etat.get("delestage_mois") != mois:
        etat["delestage_mois"] = mois
        U.telegram(
            f"⚠️ ROBIN MIROIR — crédits bas ({credits}). Délestage activé : "
            f"seules les {C.LIGUES_DELESTAGE} ligues prioritaires tournent jusqu'à la fin du mois."
        )

    U.sauver_etat(etat)

    import dashboard
    dashboard.generer()
    print(f"[FIN] {nouveaux} pari(s), {clotures} clôture(s), crédits restants : {credits}")


if __name__ == "__main__":
    try:
        executer()
    except Exception as e:
        traceback.print_exc()
        U.telegram(f"🚨 ROBIN MIROIR — CAPTURE EN ÉCHEC : {e}")
        sys.exit(1)
