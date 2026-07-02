# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — PROTOCOLE V1.2 — PARAMÈTRES GELÉS
=================================================
Gel définitif : J3 (4 juillet 2026).
Toute modification après le gel remet le compteur du test à ZÉRO (cf. protocole.md).
Le système ne prédit rien : il compare deux prix.
"""
from datetime import date

VERSION = "1.2"

# ------------------------------------------------------------------
# DÉCLENCHEUR (gelé)
# ------------------------------------------------------------------
SEUIL_EDGE = 1.06            # pari papier si cote_unibet >= cote_juste * 1.06
BANDE_COTES = (1.50, 4.00)   # M1 : hors bande -> SHADOW, jamais parié
RATIO_SUSPECT = 1.15         # M2 : cote_unibet > cote_pinnacle_brute * 1.15 -> SUSPECT
MAX_PARIS_PAR_MATCH = 1      # M4 : on garde le plus gros edge, le reste en SHADOW
MAX_PARIS_PAR_JOUR = 10      # M5 : au-delà -> SHADOW + alerte "journée anormale"

# ------------------------------------------------------------------
# BANKROLL PAPIER (gelée) — aucun euro réel en phase 1
# ------------------------------------------------------------------
BANKROLL_INITIALE = 1000.0   # unités fictives
MISE_FLAT = 10.0             # 1 % flat, jamais modifiée

# ------------------------------------------------------------------
# TEST PRÉ-ENREGISTRÉ (gelé)
# ------------------------------------------------------------------
N_VERDICT = 200              # verdict GO / KILL à N = 200 paris OFFICIELS réglés
N_ALERTE_SECURITE = 100      # simple alerte (jamais de kill anticipé)
CLV_SEUIL_ALERTE = -0.03     # à N >= 100 : CLV moyen <= -3 % => alerte
CLV_CRITERE_MORT = 0.0       # à N = 200 : CLV moyen <= 0 => KILL, clôture propre
DEBUT_OFFICIEL = date(2026, 7, 20)   # avant : phase RODAGE (loggé, ne compte pas)

# ------------------------------------------------------------------
# FENÊTRES DE CAPTURE (gelées) — minutes avant le coup d'envoi
# ------------------------------------------------------------------
FENETRE_T2 = (150, 90)       # capture principale : [T-2h30, T-1h30]
FENETRE_CLOTURE = (15, 2)    # M6 : clôture [T-15, T-2], matchs déclenchés uniquement

# ------------------------------------------------------------------
# DÉVIGAGE
# ------------------------------------------------------------------
# Champion par défaut : Shin (résiste au biais favori-outsider).
# Le duel (scripts/labo_devig.py) confirme ou inverse AVANT le gel J3.
# Les deux méthodes sont loggées à vie dans le Grand Livre quoi qu'il arrive.
DEVIG_CHAMPION = "shin"      # "shin" ou "multiplicatif"

# ------------------------------------------------------------------
# PÉRIMÈTRE — règle David : « si on a les datas -> on joue »
# Éligible = résultats gratuits football-data.org + cotes The Odds API.
# L'ordre ci-dessous = ordre de PRIORITÉ (le délestage coupe par la fin).
# ------------------------------------------------------------------
LIGUES = [
    # (sport_key The Odds API,        code football-data,  label)
    ("soccer_france_ligue_one",       "FL1", "Ligue 1"),
    ("soccer_epl",                    "PL",  "Premier League"),
    ("soccer_germany_bundesliga",     "BL1", "Bundesliga"),
    ("soccer_italy_serie_a",          "SA",  "Serie A"),
    ("soccer_spain_la_liga",          "PD",  "La Liga"),
    ("soccer_uefa_champs_league",     "CL",  "Champions League"),
    ("soccer_efl_champ",              "ELC", "Championship"),
    ("soccer_brazil_campeonato",      "BSA", "Brasileirão"),
    ("soccer_netherlands_eredivisie", "DED", "Eredivisie"),
    ("soccer_portugal_primeira_liga", "PPL", "Primeira Liga"),
    ("soccer_fifa_world_cup",         "WC",  "Coupe du Monde"),
]
LIGUES_DELESTAGE = 5         # crédits bas => on ne garde que les 5 premières du mois
CREDITS_ALERTE = 60          # seuil x-requests-remaining déclenchant le délestage

# ------------------------------------------------------------------
# BOOKMAKERS — assertion dure anti-confusion (audit S2/M2)
# ------------------------------------------------------------------
BOOKMAKER_SHARP = "pinnacle"
BOOKMAKER_SOFT = "unibet_fr"     # JAMAIS "unibet" (feed international, TRJ différent)
BOOKMAKERS_AUTORISES = {BOOKMAKER_SHARP, BOOKMAKER_SOFT}

# ------------------------------------------------------------------
# RÈGLEMENT (football-data.org)
# ------------------------------------------------------------------
DELAI_REGLEMENT_H = 3        # on ne règle qu'un match fini depuis >= 3 h
ALERTE_UNSETTLED_H = 48      # pari non réglé depuis 48 h => alerte Telegram
TOLERANCE_KO_MIN = 40        # écart max coup d'envoi pour apparier deux sources
SEUIL_FUZZY_FORT = 0.85      # M11 : en dessous => UNSETTLED, on ne devine JAMAIS
