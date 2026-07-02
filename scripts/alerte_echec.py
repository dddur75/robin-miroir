# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — M9 : un capteur qui meurt en silence fabrique des trous
invisibles dans N = 200. Ce script tourne quand un workflow échoue :
Telegram + issue GitHub (une par jour et par workflow, pas de spam).
Usage : python scripts/alerte_echec.py "Capture"
"""
import os
import sys

import utils as U


def main():
    nom = sys.argv[1] if len(sys.argv) > 1 else "Workflow"
    url_run = os.environ.get("RUN_URL", "")
    jour = U.maintenant_utc().strftime("%Y-%m-%d")
    titre = f"🚨 Échec {nom} — {jour}"
    U.telegram(f"🚨 ROBIN MIROIR — {nom} en échec. Détails : {url_run}")

    jeton = os.environ.get("GH_TOKEN")
    repo = os.environ.get("GH_REPO")
    if not jeton or not repo:
        return
    try:
        import requests
        entetes = {"Authorization": f"Bearer {jeton}",
                   "Accept": "application/vnd.github+json"}
        # Une seule issue par jour et par workflow
        r = requests.get(
            f"https://api.github.com/repos/{repo}/issues",
            headers=entetes, params={"state": "open", "per_page": 50}, timeout=20,
        )
        if r.ok and any(i.get("title") == titre for i in r.json()):
            return
        requests.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers=entetes, timeout=20,
            json={"title": titre,
                  "body": f"Run en échec : {url_run}\n\n"
                          "Le Grand Livre n'a PAS été altéré (append-only). "
                          "Vérifier les logs du run."},
        )
    except Exception as e:
        print(f"[ALERTE] création d'issue impossible : {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
