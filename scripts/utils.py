# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — Utilitaires communs.
Grand Livre = JSONL append-only (on AJOUTE, on ne modifie JAMAIS).
Types d'enregistrements : PARI, CLOTURE, REGLEMENT (liés par 'id'),
plus OBS (chaque sélection évaluée) et SHADOW (rejets tracés) dans shadow.jsonl.
"""
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone, date
from difflib import SequenceMatcher

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RACINE, "data")
DOCS = os.path.join(RACINE, "docs")
RAPPORTS = os.path.join(RACINE, "rapports")
LABO = os.path.join(RACINE, "labo")

GRAND_LIVRE = os.path.join(DATA, "grand_livre.jsonl")
SHADOW = os.path.join(DATA, "shadow.jsonl")
STATE = os.path.join(DATA, "state.json")
TEAM_MAPPING = os.path.join(DATA, "team_mapping.json")
SANTE = os.path.join(DATA, "sante.json")
VERSION_FICHIER = os.path.join(DATA, "version.json")

# --------------------------------------------------------------- temps (M10)
def maintenant_utc():
    """Toujours UTC dans les données. Paris uniquement à l'affichage."""
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


# ----------------------------------------------------------- fichiers JSON(L)
def _lire_jsonl(chemin):
    if not os.path.exists(chemin):
        return []
    lignes = []
    with open(chemin, "r", encoding="utf-8") as f:
        for l in f:
            l = l.strip()
            if l:
                lignes.append(json.loads(l))
    return lignes


def ajouter(chemin, enregistrement):
    """Append-only : une ligne JSON, flush + fsync (jamais de réécriture)."""
    with open(chemin, "a", encoding="utf-8") as f:
        f.write(json.dumps(enregistrement, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def charger_livre():
    return _lire_jsonl(GRAND_LIVRE)


def charger_shadow():
    return _lire_jsonl(SHADOW)


def charger_json(chemin, defaut):
    if not os.path.exists(chemin):
        return defaut
    with open(chemin, "r", encoding="utf-8") as f:
        contenu = f.read().strip()
    return json.loads(contenu) if contenu else defaut


def sauver_json(chemin, obj):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, chemin)


def charger_etat():
    return charger_json(STATE, {})


def sauver_etat(etat):
    sauver_json(STATE, etat)


# ------------------------------------------------------- pliage du Grand Livre
def etat_paris(livre=None):
    """
    Replie le journal append-only en état courant :
    { bet_id: {'pari': {...}, 'cloture': {...}|None, 'reglement': {...}|None} }
    """
    livre = charger_livre() if livre is None else livre
    paris = {}
    for rec in livre:
        t = rec.get("type")
        bid = rec.get("id")
        if not bid:
            continue
        entree = paris.setdefault(bid, {"pari": None, "cloture": None, "reglement": None})
        if t == "PARI" and entree["pari"] is None:          # idempotence (M8)
            entree["pari"] = rec
        elif t == "CLOTURE" and entree["cloture"] is None:
            entree["cloture"] = rec
        elif t == "REGLEMENT" and entree["reglement"] is None:
            entree["reglement"] = rec
    return {k: v for k, v in paris.items() if v["pari"] is not None}


def id_pari(event_id, marche):
    """M8 : identifiant déterministe -> re-runs sans doublons."""
    return hashlib.sha1(f"{event_id}|{marche}".encode("utf-8")).hexdigest()[:16]


def phase_du_jour(d=None):
    from config import DEBUT_OFFICIEL
    d = d or maintenant_utc().date()
    return "OFFICIEL" if d >= DEBUT_OFFICIEL else "RODAGE"


# ------------------------------------------------------------------- Telegram
def telegram(message):
    """Notification best-effort. Sans secrets Telegram : simple print."""
    jeton = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    print(f"[NOTIF] {message}")
    if not jeton or not chat:
        return False
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{jeton}/sendMessage",
            json={"chat_id": chat, "text": message},
            timeout=15,
        )
        return True
    except Exception as e:  # la notif ne doit jamais tuer le run
        print(f"[NOTIF] échec Telegram: {e}", file=sys.stderr)
        return False


def creer_issue(titre, corps):
    """Issue GitHub best-effort, dédupliquée par titre exact (issues ouvertes)."""
    jeton = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GH_REPO")
    if not jeton or not repo:
        print(f"[ISSUE non envoyée — hors GitHub] {titre}")
        return False
    try:
        import requests
        entetes = {"Authorization": f"Bearer {jeton}",
                   "Accept": "application/vnd.github+json"}
        r = requests.get(f"https://api.github.com/repos/{repo}/issues",
                         headers=entetes,
                         params={"state": "open", "per_page": 100}, timeout=20)
        if r.ok and any(i.get("title") == titre for i in r.json()):
            return True
        requests.post(f"https://api.github.com/repos/{repo}/issues",
                      headers=entetes, timeout=20,
                      json={"title": titre, "body": corps})
        return True
    except Exception as e:
        print(f"[ISSUE] échec : {e}", file=sys.stderr)
        return False


# ------------------------------------------------------------------- HTTP
def http_get_json(url, headers=None, params=None, timeout=30):
    """Couche HTTP unique — remplacée par les fixtures dans le test à blanc."""
    import requests
    r = requests.get(url, headers=headers or {}, params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json(), dict(r.headers)


# ------------------------------------------- normalisation / matching équipes
_TOKENS_INUTILES = {"fc", "afc", "cf", "cfc", "sc", "fk", "club", "cd", "sad", "1"}


def normaliser_equipe(nom):
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", " and ").replace("-", " ").replace(".", " ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    mots = [m for m in s.split() if m not in _TOKENS_INUTILES]
    return " ".join(mots)


def similarite(a, b):
    na, nb = normaliser_equipe(a), normaliser_equipe(b)
    if na == nb:
        return 1.0
    r = SequenceMatcher(None, na, nb).ratio()
    # bonus si l'un contient l'autre (« Wolves » dans « Wolverhampton Wanderers »)
    if na and nb and (na in nb or nb in na):
        r = max(r, 0.90)
    return r
