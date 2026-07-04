# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — RÈGLEMENT NOCTURNE (03:30 environ, heure de Paris).

 1. Paris sans REGLEMENT et coup d'envoi passé depuis >= 3 h.
 2. Scores via football-data.org (gratuit, 10 req/min -> pause 6.5 s).
 3. Matching équipes (M11) :
      EXACT (noms normalisés identiques + KO à ±40 min)  -> apparié, mémorisé
      FORT  (similarité >= 0.85 + KO à ±40 min)          -> apparié, mémorisé, loggé
      FAIBLE                                             -> UNSETTLED, ON NE DEVINE JAMAIS
 4. Alerte Telegram si un pari reste UNSETTLED > 48 h.
"""
import sys
import time
import traceback

import config as C
import utils as U

BASE_FD = "https://api.football-data.org/v4"


def _jeton():
    import os
    jeton = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not jeton:
        raise RuntimeError("Secret FOOTBALL_DATA_TOKEN absent.")
    return jeton


def matchs_de_competition(jeton, code, date_de, date_a):
    data, _ = U.http_get_json(
        f"{BASE_FD}/competitions/{code}/matches",
        headers={"X-Auth-Token": jeton},
        params={"dateFrom": date_de, "dateTo": date_a},
    )
    return data.get("matches", [])


def apparier(pari, matchs, mapping):
    """Retourne (match, niveau) ou (None, None). Niveau: EXACT / FORT / MAPPING."""
    ko_pari = U.parse_iso(pari["ko"])

    # 1) table de correspondance déjà validée
    ids_connus = (
        mapping.get(U.normaliser_equipe(pari["home"])),
        mapping.get(U.normaliser_equipe(pari["away"])),
    )
    for m in matchs:
        ko_m = U.parse_iso(m["utcDate"])
        if abs((ko_m - ko_pari).total_seconds()) > C.TOLERANCE_KO_MIN * 60:
            continue
        h, a = m["homeTeam"], m["awayTeam"]
        if ids_connus[0] == h.get("id") and ids_connus[1] == a.get("id"):
            return m, "MAPPING"

    # 2) matching par noms + coup d'envoi
    meilleur, score = None, 0.0
    for m in matchs:
        ko_m = U.parse_iso(m["utcDate"])
        if abs((ko_m - ko_pari).total_seconds()) > C.TOLERANCE_KO_MIN * 60:
            continue
        h = m["homeTeam"].get("name") or m["homeTeam"].get("shortName") or ""
        a = m["awayTeam"].get("name") or m["awayTeam"].get("shortName") or ""
        s = min(U.similarite(pari["home"], h), U.similarite(pari["away"], a))
        if s > score:
            meilleur, score = m, s
    if meilleur is None:
        return None, None
    if score >= 0.999:
        return meilleur, "EXACT"
    if score >= C.SEUIL_FUZZY_FORT:
        return meilleur, "FORT"
    print(f"[UNSETTLED] pas de correspondance sûre pour "
          f"{pari['home']} - {pari['away']} (meilleur score {score:.2f})")
    return None, None


def resultat_1n2(match):
    ft = (match.get("score") or {}).get("fullTime") or {}
    h, a = ft.get("home"), ft.get("away")
    if h is None or a is None:
        return None
    return "H" if h > a else ("A" if a > h else "D"), h, a


def _reporte(pari, tous_matchs):
    """M18 : le match existe (tout statut) sous les MÊMES noms normalisés,
    mais à un horaire écarté de plus de la tolérance -> c'est un report."""
    ko_pari = U.parse_iso(pari["ko"])
    for m in tous_matchs:
        h = m["homeTeam"].get("name") or m["homeTeam"].get("shortName") or ""
        a = m["awayTeam"].get("name") or m["awayTeam"].get("shortName") or ""
        if U.normaliser_equipe(h) == U.normaliser_equipe(pari["home"]) and \
           U.normaliser_equipe(a) == U.normaliser_equipe(pari["away"]):
            try:
                ko_m = U.parse_iso(m["utcDate"])
            except Exception:
                continue
            if abs((ko_m - ko_pari).total_seconds()) > C.TOLERANCE_KO_MIN * 60:
                return True
    return False


def executer():
    jeton = _jeton()
    etats = U.etat_paris()
    maintenant = U.maintenant_utc()

    en_attente = []
    for bid, e in etats.items():
        if e["reglement"] is not None:
            continue
        ko = U.parse_iso(e["pari"]["ko"])
        if (maintenant - ko).total_seconds() >= C.DELAI_REGLEMENT_H * 3600:
            en_attente.append((bid, e))

    if not en_attente:
        print("[INFO] Rien à régler.")
    mapping = U.charger_json(U.TEAM_MAPPING, {})
    etat = U.charger_etat()

    # Regrouper par compétition, une seule requête par compétition
    par_comp = {}
    for bid, e in en_attente:
        par_comp.setdefault(e["pari"]["fd_code"], []).append((bid, e))

    regles = 0
    for i, (code, lot) in enumerate(sorted(par_comp.items())):
        kos = [U.parse_iso(e["pari"]["ko"]) for _, e in lot]
        date_de = min(kos).strftime("%Y-%m-%d")
        # fenêtre élargie : un match reporté réapparaît souvent quelques jours après
        from datetime import timedelta
        date_a = (max(kos) + timedelta(days=4)).strftime("%Y-%m-%d")
        if i > 0:
            time.sleep(6.5)  # 10 req/min max sur le tier gratuit
        tous_matchs = matchs_de_competition(jeton, code, date_de, date_a)
        matchs = [m for m in tous_matchs if m.get("status") == "FINISHED"]

        for bid, e in lot:
            pari = e["pari"]
            match, niveau = apparier(pari, matchs, mapping)
            if match is None:
                # M18 — VOID : après 72 h, si le match existe sous les MÊMES noms
                # exacts mais à un AUTRE horaire, c'est un report -> mise rendue,
                # pari exclu de N. On ne devine toujours pas un score.
                age_h = (maintenant - U.parse_iso(pari["ko"])).total_seconds() / 3600
                if age_h >= C.VOID_APRES_H and _reporte(pari, tous_matchs):
                    U.ajouter(U.GRAND_LIVRE, {
                        "type": "REGLEMENT", "id": bid, "ts": U.iso(maintenant),
                        "score": "REPORTE", "resultat": None,
                        "issue": "VOID", "pnl": 0.0, "matching": "REPORT",
                        "clv_disponible": e["cloture"] is not None,
                    })
                    regles += 1
                    print(f"[VOID] {pari['home']} - {pari['away']} reporté "
                          f"-> mise rendue, exclu de N (M18)")
                continue
            res = resultat_1n2(match)
            if res is None:
                continue
            resultat, bh, ba = res
            gagne = (resultat == pari["marche"])
            pnl = round(pari["mise"] * (pari["cote_unibet"] - 1.0), 2) if gagne \
                else -pari["mise"]
            U.ajouter(U.GRAND_LIVRE, {
                "type": "REGLEMENT", "id": bid, "ts": U.iso(maintenant),
                "score": f"{bh}-{ba}", "resultat": resultat,
                "issue": "GAGNE" if gagne else "PERDU", "pnl": pnl,
                "matching": niveau,
                "clv_disponible": e["cloture"] is not None,
            })
            regles += 1
            # Mémoriser les correspondances sûres (les deux sens)
            if niveau in ("EXACT", "FORT"):
                mapping[U.normaliser_equipe(pari["home"])] = match["homeTeam"].get("id")
                mapping[U.normaliser_equipe(pari["away"])] = match["awayTeam"].get("id")
            print(f"[RÈGLEMENT] {pari['home']} - {pari['away']} {bh}-{ba} "
                  f"-> {('GAGNÉ +' + str(pnl)) if gagne else ('PERDU ' + str(pnl))}")

    U.sauver_json(U.TEAM_MAPPING, mapping)

    # Alerte UNSETTLED > 48 h (une seule fois par pari)
    deja = set(etat.get("alertes_unsettled", []))
    for bid, e in U.etat_paris().items():
        if e["reglement"] is not None or bid in deja:
            continue
        ko = U.parse_iso(e["pari"]["ko"])
        if (maintenant - ko).total_seconds() > C.ALERTE_UNSETTLED_H * 3600:
            U.telegram(
                f"⚠️ ROBIN MIROIR — pari NON RÉGLÉ depuis 48 h : "
                f"{e['pari']['home']} - {e['pari']['away']} ({e['pari']['ligue']}). "
                f"Matching à vérifier."
            )
            deja.add(bid)
    etat["alertes_unsettled"] = sorted(deja)
    etat["dernier_reglement"] = U.iso(maintenant)
    U.sauver_etat(etat)

    import dashboard
    dashboard.generer()
    print(f"[FIN] {regles} pari(s) réglé(s).")


if __name__ == "__main__":
    try:
        executer()
    except Exception as e:
        traceback.print_exc()
        U.telegram(f"🚨 ROBIN MIROIR — RÈGLEMENT EN ÉCHEC : {e}")
        sys.exit(1)
