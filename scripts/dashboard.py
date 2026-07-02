# -*- coding: utf-8 -*-
"""
ROBIN MIROIR — Dashboard statique (docs/index.html, servi par GitHub Pages).
Zéro JavaScript, zéro dépendance, ouverture instantanée sur mobile.
4 métriques gelées + jauge de verdict 0 -> 200 (repère alerte à 100).
"""
import html
import os
from datetime import timezone, timedelta

import config as C
import utils as U
import metriques


def _fr(dt_iso):
    if not dt_iso:
        return "—"
    dt = U.parse_iso(dt_iso).astimezone(timezone(timedelta(hours=2)))  # affichage Paris (été)
    return dt.strftime("%d/%m %H:%M")


def _pct(x, signe=True):
    if x is None:
        return "—"
    return f"{x:+.2%}" if signe else f"{x:.0%}"


COULEURS = {"ok": "#1F6F50", "rodage": "#B7791F", "alerte": "#B3362B"}


def generer():
    m = metriques.calculer()
    off, rod = m["officiel"], m["rodage"]
    n = off["n_regles"]
    pct_n = min(100.0, 100.0 * n / C.N_VERDICT)
    accent = COULEURS[m["couleur"]]
    ic = f" ± {off['ic95']:.2%}" if off["ic95"] is not None else ""
    bandeau_rodage = ""
    if m["phase_courante"] == "RODAGE":
        bandeau_rodage = (
            f"<div class='bandeau'>Phase de rodage — {rod['n_declenches']} déclenchement(s) "
            f"d'essai, couverture Unibet {_pct(rod['couverture_unibet'], False)} "
            f"sur {rod['matchs_vus']} match(s) vus. Rien ne compte avant le "
            f"{C.DEBUT_OFFICIEL.strftime('%d/%m/%Y')}.</div>"
        )

    page = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Robin Miroir — registre</title>
<style>
:root {{
  --papier:#F7F7F3; --encre:#17251E; --trait:#D8DAD2;
  --sourdine:#5C6660; --accent:{accent};
}}
* {{ box-sizing:border-box; margin:0; }}
body {{
  background:var(--papier); color:var(--encre);
  font-family:system-ui, -apple-system, "Segoe UI", sans-serif;
  padding:20px 16px 40px; max-width:680px; margin:0 auto;
  font-variant-numeric: tabular-nums;
}}
.entete {{ display:flex; justify-content:space-between; align-items:baseline;
  border-bottom:3px solid var(--encre); padding-bottom:10px; }}
.entete h1 {{ font-size:1.05rem; letter-spacing:.14em; text-transform:uppercase; }}
.entete .v {{ font-size:.72rem; color:var(--sourdine); letter-spacing:.08em; }}
.statut {{ margin:18px 0 6px; font-size:1.02rem; font-weight:700; line-height:1.45;
  padding-left:14px; border-left:5px solid var(--accent); }}
.bandeau {{ margin:10px 0 0; font-size:.82rem; color:var(--sourdine);
  background:#EFEFE8; border:1px solid var(--trait); padding:8px 10px; }}
.grille {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:22px; }}
.carte {{ background:#FFFFFF; border:1px solid var(--trait); padding:14px 14px 12px; }}
.carte .etiquette {{ font-size:.68rem; letter-spacing:.13em; text-transform:uppercase;
  color:var(--sourdine); }}
.carte .valeur {{ font-size:2.1rem; font-weight:750; line-height:1.15; margin-top:6px; }}
.carte .sous {{ font-size:.74rem; color:var(--sourdine); margin-top:4px; }}
.jauge {{ margin-top:26px; }}
.jauge .titre {{ font-size:.68rem; letter-spacing:.13em; text-transform:uppercase;
  color:var(--sourdine); margin-bottom:8px; }}
.rail {{ position:relative; height:26px; background:#FFFFFF;
  border:1.5px solid var(--encre); }}
.rempli {{ position:absolute; inset:0; width:{pct_n:.2f}%; background:var(--accent); }}
.repere {{ position:absolute; top:-6px; bottom:-6px; width:2px; background:var(--encre); }}
.repere.r100 {{ left:50%; }}
.legende {{ display:flex; justify-content:space-between; font-size:.7rem;
  color:var(--sourdine); margin-top:6px; }}
.ops {{ margin-top:30px; border-top:1px solid var(--trait); padding-top:12px;
  font-size:.78rem; color:var(--sourdine); line-height:1.9; }}
.ops b {{ color:var(--encre); font-weight:650; }}
.devise {{ margin-top:26px; font-size:.78rem; color:var(--sourdine);
  font-style:italic; }}
@media (max-width:430px) {{ .grille {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="entete"><h1>Robin Miroir</h1>
<span class="v">protocole V{C.VERSION} · gelé</span></div>

<p class="statut">{html.escape(m["statut"])}</p>
{bandeau_rodage}

<div class="grille">
  <div class="carte"><div class="etiquette">CLV moyen</div>
    <div class="valeur">{_pct(off["clv_moyen"])}</div>
    <div class="sous">sur {off["clv_n"]} clôture(s){ic}</div></div>
  <div class="carte"><div class="etiquette">Déclenchements réglés</div>
    <div class="valeur">{n} / {C.N_VERDICT}</div>
    <div class="sous">{off["n_attente"]} en attente de règlement</div></div>
  <div class="carte"><div class="etiquette">ROI flat</div>
    <div class="valeur">{_pct(off["roi"])}</div>
    <div class="sous">P&amp;L papier {off["pnl"]:+.0f} u · mise {C.MISE_FLAT:.0f} u</div></div>
  <div class="carte"><div class="etiquette">Écart moyen vs sharp</div>
    <div class="valeur">{_pct(off["ecart_moyen"])}</div>
    <div class="sous">{off["obs"]} sélections évaluées</div></div>
</div>

<div class="jauge">
  <div class="titre">Route vers le verdict</div>
  <div class="rail"><div class="rempli"></div><div class="repere r100"></div></div>
  <div class="legende"><span>0</span><span>100 · alerte sécurité</span>
  <span>{C.N_VERDICT} · verdict</span></div>
</div>

<div class="ops">
Couverture Unibet : <b>{_pct(off["couverture_unibet"] if m["phase_courante"] == "OFFICIEL" else rod["couverture_unibet"], False)}</b>
 · Clôtures manquantes : <b>{off["clotures_manquantes"]}</b>
 · Crédits API restants : <b>{m["credits"] if m["credits"] is not None else "—"}</b>{" · <b>DÉLESTAGE ACTIF</b>" if m["delestage"] else ""}<br>
Dernière capture : <b>{_fr(m["derniere_capture"])}</b>
 · Dernier règlement : <b>{_fr(m["dernier_reglement"])}</b>
</div>

<p class="devise">Ce système ne prédit rien : il compare deux prix. L'issue la plus
probable est de prouver que l'edge n'existe pas — et ce sera un succès.</p>
</body>
</html>"""
    os.makedirs(U.DOCS, exist_ok=True)
    with open(os.path.join(U.DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("[DASHBOARD] docs/index.html régénéré.")


if __name__ == "__main__":
    generer()
