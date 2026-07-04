# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — LE CHEF D'ORCHESTRE.
Un seul workflow GitHub appelle ce script. Le chef décide quoi faire :
  - cron */10        -> Guetteur (capture)
  - cron 30 1 * * *  -> Arbitre (règlement) puis Auditeur (intégrité)
  - cron 0 19 * * 0  -> Messager (rapport hebdo)
  - manuel           -> tâche choisie (auto / capture / reglement / rapport / labo / audit)
Si un secret manque, le chef n'explose pas : il ouvre une issue claire qui
explique exactement quoi faire, et le run reste vert.
"""
import os
import sys
import traceback

import utils as U

CRON_VERS_TACHE = {
    "*/10 * * * *": "capture",
    "30 1 * * *": "reglement",
    "0 19 * * 0": "rapport",
}

AIDE_SECRETS = {
    "ODDS_API_KEY":
        "1. Ouvre ton dépôt GitHub → **Settings** → **Secrets and variables** → "
        "**Actions**\n2. **New repository secret**\n3. Name : `ODDS_API_KEY` — "
        "Secret : ta clé The Odds API\n4. **Add secret**\n\nLa machine repartira "
        "toute seule au prochain passage (10 min max), rien d'autre à faire.",
    "FOOTBALL_DATA_TOKEN":
        "1. Ouvre ton dépôt GitHub → **Settings** → **Secrets and variables** → "
        "**Actions**\n2. **New repository secret**\n3. Name : `FOOTBALL_DATA_TOKEN` — "
        "Secret : ta clé football-data.org\n4. **Add secret**\n\nLe règlement "
        "repartira tout seul à la prochaine nuit, rien d'autre à faire.",
}


def tache_depuis(cron, demande):
    if demande and demande != "auto":
        return demande
    if cron in CRON_VERS_TACHE:
        return CRON_VERS_TACHE[cron]
    return "capture"  # lancement manuel "auto" : on capture


def secret_present(nom):
    if os.environ.get(nom):
        return True
    print(f"[CHEF] Secret {nom} absent — j'ouvre une issue d'aide et je m'arrête proprement.")
    U.creer_issue(
        f"🔑 Il manque le secret {nom}",
        f"La machine a tourné mais ne peut rien faire sans `{nom}`.\n\n"
        + AIDE_SECRETS.get(nom, "Ajoute ce secret dans Settings → Secrets → Actions.")
    )
    return False


def executer():
    cron = os.environ.get("SCHEDULE", "")
    demande = os.environ.get("TACHE", "auto")
    tache = tache_depuis(cron, demande)
    print(f"[CHEF] cron='{cron}' demande='{demande}' -> tâche : {tache}")

    if tache == "capture":
        if not secret_present("ODDS_API_KEY"):
            return
        import capture
        capture.executer()

    elif tache == "reglement":
        if not secret_present("FOOTBALL_DATA_TOKEN"):
            return
        import reglement
        reglement.executer()
        import audit
        audit.executer()

    elif tache == "rapport":
        import rapport
        rapport.executer()

    elif tache == "audit":
        import audit
        audit.executer()

    elif tache == "labo":
        import labo_devig
        labo_devig.executer()

    else:
        raise RuntimeError(f"Tâche inconnue : {tache}")


if __name__ == "__main__":
    try:
        executer()
    except Exception as e:
        traceback.print_exc()
        U.telegram(f"🚨 ROBIN MIROIR — tâche en échec : {e}")
        sys.exit(1)
