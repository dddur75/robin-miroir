# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — M13 : TEST DE BOUT EN BOUT À BLANC.
Aucun appel réseau : l'API est remplacée par des fixtures.
Un jeu de matchs fictifs traverse TOUTE la chaîne :
capture -> règles M1/M2/M4/M5 -> pari papier -> clôture/CLV -> règlement/P&L
-> rapport -> dashboard. Idempotence vérifiée (double run sans doublon).
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as C
import utils as U

# ---------------------------------------------------- bac à sable isolé
BAC = tempfile.mkdtemp(prefix="robin_test_")
for nom in ("data", "docs", "rapports"):
    os.makedirs(os.path.join(BAC, nom), exist_ok=True)
U.GRAND_LIVRE = os.path.join(BAC, "data", "grand_livre.jsonl")
U.SHADOW = os.path.join(BAC, "data", "shadow.jsonl")
U.STATE = os.path.join(BAC, "data", "state.json")
U.TEAM_MAPPING = os.path.join(BAC, "data", "team_mapping.json")
U.DOCS = os.path.join(BAC, "docs")
U.RAPPORTS = os.path.join(BAC, "rapports")

# ---------------------------------------------------- horloge contrôlée
T0 = datetime(2026, 7, 2, 14, 0, tzinfo=timezone.utc)
HORLOGE = {"now": T0}
U.maintenant_utc = lambda: HORLOGE["now"]

KO = T0 + timedelta(minutes=120)          # coup d'envoi dans la fenêtre T-2
KO_ISO = KO.strftime("%Y-%m-%dT%H:%M:%SZ")
SPORT = "soccer_fifa_world_cup"

def h2h(home, away, cH, cD, cA, book, lu=None):
    m = {"key": "h2h", "outcomes": [
        {"name": home, "price": cH}, {"name": "Draw", "price": cD},
        {"name": away, "price": cA}]}
    if lu:
        m["last_update"] = lu
    return {"key": book, "markets": [m]}

def ev(eid, home, away, books):
    return {"id": eid, "sport_key": SPORT, "commence_time": KO_ISO,
            "home_team": home, "away_team": away, "bookmakers": books}

EVENEMENTS = [
    # A : déclencheur propre (H) — pin 2.30/3.40/3.30, unibet H 2.60
    #     (ratio brut 1.130 : dans le couloir [seuil edge ; seuil suspect[)
    ev("evA", "FC Essai", "AC Témoin",
       [h2h("FC Essai", "AC Témoin", 2.30, 3.40, 3.30, "pinnacle"),
        h2h("FC Essai", "AC Témoin", 2.60, 3.35, 3.10, "unibet_fr")]),
    # B : boost suspect (M2) — unibet A = pinnacle A × 1.25
    ev("evB", "SC Boost", "US Promo",
       [h2h("SC Boost", "US Promo", 1.80, 3.60, 4.00, "pinnacle"),
        h2h("SC Boost", "US Promo", 1.78, 3.55, 5.00, "unibet_fr")]),
    # C : gros edge mais hors bande (M1) — outsider unibet 5.50
    ev("evC", "Racing Bande", "Olympique Marge",
       [h2h("Racing Bande", "Olympique Marge", 1.55, 4.10, 5.80, "pinnacle"),
        h2h("Racing Bande", "Olympique Marge", 1.52, 4.00, 5.50, "unibet_fr")]),
    # D : deux déclencheurs -> M4 garde le plus gros edge (H attendu)
    ev("evD", "Stade Double", "Union Choix",
       [h2h("Stade Double", "Union Choix", 2.60, 3.20, 2.90, "pinnacle"),
        h2h("Stade Double", "Union Choix", 2.95, 3.60, 2.75, "unibet_fr")]),
    # E : Unibet absent -> NO_QUOTE (mesure de couverture)
    ev("evE", "CF Absent", "Deportivo Vide",
       [h2h("CF Absent", "Deportivo Vide", 2.00, 3.30, 3.90, "pinnacle")]),
    # G : cote Unibet périmée (mise à jour il y a 2 h) -> STALE (M19)
    ev("evG", "FC Figé", "Sporting Gelé",
       [h2h("FC Figé", "Sporting Gelé", 2.30, 3.40, 3.30, "pinnacle",
            lu=(T0).strftime("%Y-%m-%dT%H:%M:%SZ")),
        h2h("FC Figé", "Sporting Gelé", 2.60, 3.30, 3.10, "unibet_fr",
            lu=(T0 - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"))]),
]

CLOTURE_A = {"id": "evA", "sport_key": SPORT, "commence_time": KO_ISO,
             "home_team": "FC Essai", "away_team": "AC Témoin",
             "bookmakers": [h2h("FC Essai", "AC Témoin", 2.15, 3.50, 3.45, "pinnacle")]}

CLOTURE_D = {"id": "evD", "sport_key": SPORT, "commence_time": KO_ISO,
             "home_team": "Stade Double", "away_team": "Union Choix",
             "bookmakers": [h2h("Stade Double", "Union Choix", 2.85, 3.25, 2.70, "pinnacle")]}

KO_VIEUX = T0 - timedelta(hours=80)   # pari fantôme vieux de 80 h (test VOID M18)

MATCHS_FD = {"matches": [
    {
        "utcDate": KO_ISO, "status": "FINISHED",
        "homeTeam": {"id": 101, "name": "Essai United"},     # fuzzy FORT attendu
        "awayTeam": {"id": 102, "name": "AC Temoin"},
        "score": {"fullTime": {"home": 2, "away": 1}},
    },
    {   # même affiche que le pari fantôme, mais 26 h plus tard : REPORTÉ
        "utcDate": (KO_VIEUX + timedelta(hours=26)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "SCHEDULED",
        "homeTeam": {"id": 201, "name": "Vieux FC"},
        "awayTeam": {"id": 202, "name": "Report United"},
        "score": {"fullTime": {"home": None, "away": None}},
    },
]}

QUOTA = {"x-requests-remaining": "497"}

def faux_http(url, headers=None, params=None, timeout=30):
    if url.endswith("/sports/"):
        return ([{"key": SPORT, "active": True},
                 {"key": "soccer_epl", "active": False}], QUOTA)
    if url.endswith(f"/sports/{SPORT}/events"):
        return ([{k: e[k] for k in
                  ("id", "sport_key", "commence_time", "home_team", "away_team")}
                 for e in EVENEMENTS], QUOTA)
    if url.endswith(f"/sports/{SPORT}/odds"):
        return (EVENEMENTS, QUOTA)
    if f"/events/evA/odds" in url:
        return (CLOTURE_A, QUOTA)
    if f"/events/evD/odds" in url:
        return (CLOTURE_D, QUOTA)
    if "/competitions/WC/matches" in url:
        return (MATCHS_FD, dict())
    raise RuntimeError(f"Fixture manquante pour {url}")

U.http_get_json = faux_http
os.environ.setdefault("ODDS_API_KEY", "cle-de-test")
os.environ.setdefault("FOOTBALL_DATA_TOKEN", "jeton-de-test")
os.environ.pop("TELEGRAM_BOT_TOKEN", None)

import capture, reglement, rapport, dashboard  # noqa: E402  (après les patchs)

def livre():
    return U.charger_livre()

def shadow():
    return U.charger_shadow()

print("=" * 62)
print("TEST À BLANC — 1) CAPTURE T-2 (5 matchs fictifs)")
capture.executer()
paris = [r for r in livre() if r["type"] == "PARI"]
statuts = [r.get("statut") for r in shadow()]
assert len(paris) == 2, f"attendu 2 paris, obtenu {len(paris)}"
assert {p["event_id"] for p in paris} == {"evA", "evD"}
assert all(p["phase"] == "RODAGE" for p in paris)
assert all(p["methode"] == "shin" for p in paris)
assert "SUSPECT" in statuts, "M2 non déclenché"
assert "HORS_BANDE" in statuts, "M1 non déclenché"
assert "SECOND_PICK" in statuts, "M4 non déclenché"
assert "NO_QUOTE_UNIBET" in statuts, "mesure de couverture absente"
assert "STALE" in statuts, "M19 (cote périmée) non déclenché"
pA = next(p for p in paris if p["event_id"] == "evA")
pD = next(p for p in paris if p["event_id"] == "evD")
assert pA["marche"] == "H" and pA["cote_unibet"] == 2.60
assert pD["marche"] == "H", f"M4 devait garder H sur evD, obtenu {pD['marche']}"
print(f"   ✔ 2 paris papier (evA:H, evD:H), M1/M2/M4 + NO_QUOTE tracés en shadow")
print(f"   ✔ evA : edge {pA['edge']:+.2%}, p_vraie {pA['p_vraie']}, "
      f"marge Pinnacle {pA['marge_pinnacle']:.2%}")

print("TEST À BLANC — 2) IDEMPOTENCE (re-run immédiat, M8)")
capture.executer()
assert len([r for r in livre() if r["type"] == "PARI"]) == 2, "doublon détecté !"
print("   ✔ re-run : zéro doublon")

print("TEST À BLANC — 3) CAP JOURNALIER (M5)")
etat = U.charger_etat()
compteur = {"n": C.MAX_PARIS_PAR_JOUR}
evF = ev("evF", "FC Onze", "Onze United",
         [h2h("FC Onze", "Onze United", 2.30, 3.40, 3.30, "pinnacle"),
          h2h("FC Onze", "Onze United", 2.60, 3.30, 3.10, "unibet_fr")])
n = capture.evaluer_evenement(evF, "Coupe du Monde", "WC", etat, compteur)
assert n == 0 and any(r.get("statut") == "CAP_JOURNALIER" for r in shadow())
print("   ✔ 11e déclencheur du jour -> SHADOW CAP_JOURNALIER, pas de pari")

print("TEST À BLANC — 4) CLÔTURE + CLV (M6)")
HORLOGE["now"] = KO - timedelta(minutes=10)          # fenêtre [T-15, T-2]
capture.executer()
clot = [r for r in livre() if r["type"] == "CLOTURE"]
assert len(clot) == 2, f"attendu 2 clôtures, obtenu {len(clot)}"
clvA = next(r for r in clot if r["id"] == pA["id"])["clv"]
assert clvA > 0, "le CLV de la fixture evA devait être positif"
print(f"   ✔ clôtures evA + evD capturées : evA Pinnacle 2.30 -> 2.15, CLV {clvA:+.2%}")

print("TEST À BLANC — 5) RÈGLEMENT + P&L + MATCHING (M11) + VOID (M18)")
# Pari fantôme vieux de 80 h dont le match a été reporté de 26 h -> VOID attendu
pariV = {
    "type": "PARI", "id": U.id_pari("evV", "H"), "phase": "RODAGE",
    "ts_capture": U.iso(KO_VIEUX - timedelta(minutes=120)),
    "ligue": "Coupe du Monde", "fd_code": "WC", "event_id": "evV",
    "ko": KO_VIEUX.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "home": "Vieux FC", "away": "Report United",
    "marche": "H", "selection": "Vieux FC",
    "cote_unibet": 2.0, "cote_pinnacle": 1.9, "p_vraie": 0.5,
    "p_shin": 0.5, "p_mult": 0.5, "methode": "shin", "edge": 0.0,
    "marge_pinnacle": 0.03, "age_p_min": 1.0, "age_u_min": 1.0,
    "mise": 10.0, "sport_key": SPORT,
}
U.ajouter(U.GRAND_LIVRE, pariV)
HORLOGE["now"] = KO + timedelta(hours=4)
reglement.executer()
regs = [r for r in livre() if r["type"] == "REGLEMENT"]
regA = next(r for r in regs if r["id"] == pA["id"])
assert regA["issue"] == "GAGNE" and abs(regA["pnl"] - 16.0) < 1e-9
assert regA["matching"] in ("FORT", "EXACT")
regV = next(r for r in regs if r["id"] == pariV["id"])
assert regV["issue"] == "VOID" and regV["pnl"] == 0.0, "M18 VOID non appliqué"
mapping = U.charger_json(U.TEAM_MAPPING, {})
assert mapping, "table de correspondance non mémorisée"
print(f"   ✔ evA réglé 2-1 -> GAGNÉ +16.0 u (matching {regA['matching']}), "
      f"mapping mémorisé")
print(f"   ✔ match reporté -> VOID, mise rendue, exclu de N (M18)")

print("TEST À BLANC — 6) MÉTRIQUES : VOID hors N, 5 agents présents")
import metriques
mm = metriques.calculer()
rod_m = mm["rodage"]
assert rod_m["n_regles"] == 1, f"N devait valoir 1 (VOID exclu), obtenu {rod_m['n_regles']}"
assert rod_m["n_void"] == 1
assert len(mm["agents"]) == 5
print(f"   ✔ N = {rod_m['n_regles']} (le VOID ne compte pas), n_void = 1, agents = 5")

print("TEST À BLANC — 7) AUDITEUR (M20) : contrôle d'intégrité")
import audit
ok_audit = audit.executer(silencieux=True)
assert ok_audit is True, "l'Auditeur a trouvé une anomalie sur un livre sain"
sante = U.charger_json(U.SANTE, {})
assert sante.get("ok") is True and len(sante.get("checks", [])) >= 10
print(f"   ✔ {len(sante['checks'])}/{len(sante['checks'])} contrôles verts, "
      f"sante.json écrit")

print("TEST À BLANC — 8) CHEF D'ORCHESTRE : routage + secret manquant géré")
import chef
assert chef.tache_depuis("*/10 * * * *", "auto") == "capture"
assert chef.tache_depuis("30 1 * * *", "auto") == "reglement"
assert chef.tache_depuis("0 19 * * 0", "auto") == "rapport"
assert chef.tache_depuis("", "labo") == "labo"
jeton_sauve = os.environ.pop("FOOTBALL_DATA_TOKEN")
os.environ["TACHE"] = "reglement"
os.environ["SCHEDULE"] = ""
chef.executer()   # ne doit PAS exploser : issue d'aide + arrêt propre
os.environ["FOOTBALL_DATA_TOKEN"] = jeton_sauve
os.environ.pop("TACHE")
print("   ✔ routage cron->tâche correct ; secret manquant = arrêt propre + aide")

print("TEST À BLANC — 9) RAPPORT + DASHBOARD")
texte = rapport.construire()
assert texte.count("\n") <= 11, "rapport > 10 lignes"
dashboard.generer()
page = open(os.path.join(U.DOCS, "index.html"), encoding="utf-8").read()
assert "Robin Miroir" in page and "verdict" in page
assert "Guetteur" in page and "Auditeur" in page, "bande des agents absente"
print("   ✔ rapport ≤ 10 lignes ; dashboard généré avec la bande des 5 agents")
print("-" * 62)
print(texte)
print("=" * 62)
print(f"TEST À BLANC : TOUT EST VERT ✅   (bac à sable : {BAC})")
print(json.dumps({"paris": len(paris), "shadow": len(shadow()),
                  "clotures": len(clot), "reglements": len(regs),
                  "voids": 1, "checks_audit": len(sante["checks"])}, indent=2))
