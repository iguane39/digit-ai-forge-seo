"""Genere le rapport HTML client d'une etude SEO.

Lit les donnees d'une mission (fiches, cadrage, etat, actions, snapshot) et produit
une page autonome dans `<projet>/seo/livrables/`.

Le livrable n'est pas un gabarit a remplir : c'est ce generateur. Un HTML saisi a la
main pour 87 noeuds et 40 actions ne survit pas au deuxieme audit, et diverge de sa
source des la premiere correction (decision D-11).

Usage :
    python scripts/rapport_html.py --projet C:/dev/mon-client
    python scripts/rapport_html.py --projet C:/dev/mon-client --verifier

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

from gabarit_html import (
    absence,
    badge_preuve,
    barre,
    esc,
    legende_preuves,
    page,
    section,
    tableau,
)
from gabarits import MOTIF_MODELE, front_matter
from grille import NB_NOEUDS, RACINE

MANIFESTE = RACINE / "seo" / "manifest.json"

MAX_FORTS, MAX_FAIBLES, MAX_ACTIONS = 10, 15, 40

RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
RE_TIER = re.compile(r"\[(T[1-4])\b", re.I)

LIBELLE_VOLET = {
    "ETAT": "État",
    "STRATEGIE": "Stratégie",
    "TRANSVERSAL": "Transversal",
    "CADRAGE": "Cadrage",
}
LIBELLE_STATUT = {
    "SD": "sans dépendance",
    "EX": "si export fourni",
    "PY": "si outil payant",
    "NM": "non mesurable",
    "RV": "renvoi",
    "CA": "cadrage",
}
LIBELLE_VERDICT = {
    "conforme": "Conforme",
    "partiel": "Partiel",
    "non-conforme": "Non conforme",
    "non-mesure": "Non mesuré",
    "sans-objet": "Sans objet",
}


# ------------------------------------------------------------------- collecte


def corps_fiche(chemin: Path) -> dict:
    """Extrait Constat / Preuves / Interpretation, commentaires de gabarit retires."""
    texte = chemin.read_text(encoding="utf-8")
    corps = texte.split("\n---\n", 2)[-1]
    corps = RE_COMMENT.sub("", corps)
    out = {"constat": "", "preuves": "", "interpretation": ""}
    cle = None
    tampon: dict[str, list[str]] = {k: [] for k in out}
    for ligne in corps.split("\n"):
        t = ligne.strip()
        bas = t.lower()
        if bas.startswith("## "):
            titre = bas[3:].strip()
            cle = (
                "constat"
                if titre.startswith("constat")
                else "preuves"
                if titre.startswith("preuve")
                else "interpretation"
                if titre.startswith("interpr")
                else None
            )
            continue
        if cle and t:
            tampon[cle].append(t)
    for k in out:
        out[k] = " ".join(tampon[k]).strip()
    return out


def collecter(projet: Path) -> dict:
    base = projet / "seo"
    if not base.is_dir():
        raise SystemExit(f"{base} absent — créer l'étude avec new_mission.py")

    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    etat = json.loads((base / "etat.json").read_text(encoding="utf-8"))

    prov = {}
    if (base / ".forge-seo.json").exists():
        prov = json.loads((base / ".forge-seo.json").read_text(encoding="utf-8"))

    noeuds, absents = [], []
    for n in manifeste["noeuds"]:
        fiche = base / "analyse" / n["chemin"] / "_fiche.md"
        if not fiche.exists():
            absents.append(n["chemin"])
            continue
        fm = front_matter(fiche)
        noeuds.append({**n, **fm, **corps_fiche(fiche)})

    # REFUS si l'etude ne couvre pas toute la grille courante. Sans ce controle, une
    # etude ouverte avant une evolution de la grille rend un rapport silencieusement
    # ampute -- "Couverture des 82 noeuds" la ou le referentiel en compte 87 --, et le
    # client recoit un document qui pretend etre complet. Le rapport affichait la
    # version de grille sans jamais la comparer : afficher n'est pas verifier.
    if absents:
        v_etude = prov.get("version_grille", "inconnue")
        raise SystemExit(
            f"REFUS : {len(absents)} nœud(s) de la grille n'ont pas de fiche dans cette "
            f"étude ({len(noeuds)}/{NB_NOEUDS} trouvés).\n"
            f"L'étude a été créée sur la grille {v_etude} ; le référentiel a évolué "
            f"depuis.\n"
            f"Premiers manquants : {', '.join(absents[:3])}"
            + (f" … (+{len(absents) - 3})" if len(absents) > 3 else "")
            + "\n\nUn rapport partiel qui se présente comme complet est pire qu'aucun "
            "rapport.\nDiagnostic : python <forge>/scripts/validate.py --mission "
            f'"{projet}"'
        )

    livrables = base / "livrables"
    actions = []
    csvs = sorted(livrables.glob("actions-*.csv")) if livrables.is_dir() else []
    if csvs:
        with csvs[-1].open(encoding="utf-8-sig", newline="") as f:
            actions = list(csv.DictReader(f))

    # Chainage des runs : on filtre sur le domaine de l'etude et on trie sur la date
    # extraite du nom, pas sur l'ordre lexicographique du glob. Deux domaines dans un
    # meme projet, ou un nom de fichier inhabituel, suffiraient sinon a comparer deux
    # runs sans rapport -- et le diff est ce que le client achete au second audit.
    domaine = etat.get("domaine") or ""
    snaps = []
    if livrables.is_dir():
        motif = re.compile(
            rf"^snapshot-{re.escape(domaine)}-(\d{{8}})\.json$" if domaine
            else r"^snapshot-.*-(\d{8})\.json$"
        )
        snaps = sorted(
            (p for p in livrables.glob("snapshot-*.json") if motif.match(p.name)),
            key=lambda p: motif.match(p.name).group(1),
        )

    snapshot, snap_precedent = {}, None
    if snaps:
        snapshot = json.loads(snaps[-1].read_text(encoding="utf-8"))
        if len(snaps) > 1:
            snap_precedent = json.loads(snaps[-2].read_text(encoding="utf-8"))

    # etat.json porte le chainage : sans mise a jour il reste a null indefiniment et
    # ment sur l'historique reel. Ce script est le seul a connaitre le contenu de
    # livrables/ -- c'est donc lui qui le tient a jour.
    attendu = snaps[-2].name if len(snaps) > 1 else None
    if etat.get("snapshot_precedent") != attendu:
        etat["snapshot_precedent"] = attendu
        (base / "etat.json").write_text(
            json.dumps(etat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    cadrage = ""
    if (base / "cadrage.md").exists():
        cadrage = (base / "cadrage.md").read_text(encoding="utf-8")

    return {
        "base": base,
        "etat": etat,
        "prov": prov,
        "noeuds": noeuds,
        "actions": actions,
        "snapshot": snapshot,
        "precedent": snap_precedent,
        "cadrage": cadrage,
        "sources": {
            "actions": csvs[-1].name if csvs else None,
            "snapshot": snaps[-1].name if snaps else None,
        },
    }


def champ_cadrage(cadrage: str, libelle: str) -> str:
    for ligne in cadrage.split("\n"):
        if libelle.lower() in ligne.lower() and ":" in ligne:
            val = ligne.split(":", 1)[1].strip()
            val = val.strip("*_ ").replace("**", "")
            if val and not val.startswith("("):
                return val
    return ""


def hors_modele(n: dict) -> bool:
    """Un noeud ecarte parce que le modele d'acquisition ne le concerne pas n'est
    PAS une dette d'instrumentation : il n'y a rien a obtenir pour le lever."""
    return MOTIF_MODELE in (n.get("motif_hors_perimetre") or "")


# --------------------------------------------------------------------- blocs


def repartition(noeuds: list[dict]) -> tuple[str, dict]:
    compte = {"T1": 0, "T2": 0, "T3": 0, "T4": 0, "NM": 0}
    for n in noeuds:
        if n.get("etat") == "hors-perimetre" or n.get("verdict") == "non-mesure":
            compte["NM"] += 1
            continue
        tier = (n.get("niveau_preuve") or "").upper()
        if tier in compte:
            compte[tier] += 1
    total = sum(compte.values())
    if not total:
        return "", compte
    items = "".join(
        f"<li>{badge_preuve(t)} <b>{compte[t]}</b> "
        f"({round(100 * compte[t] / total)}&nbsp;%)</li>"
        for t in ("T1", "T2", "T3", "T4", "NM")
        if compte[t]
    )
    return f'<ul class="repart">{items}</ul>', compte


def bloc_bandeau(d: dict, repart: str) -> str:
    e, prov = d["etat"], d["prov"]
    cad = d["cadrage"]
    meta = [
        ("Domaine", e.get("domaine") or "—"),
        ("Client", e.get("client") or "—"),
        ("Date du rapport", dt.date.today().isoformat()),
        ("Modèle d'acquisition", champ_cadrage(cad, "Modele d'acquisition") or "non déclaré"),
        ("Marché", champ_cadrage(cad, "Pays / langue") or "non déclaré"),
        ("Audience", champ_cadrage(cad, "Audience du livrable") or "non déclarée"),
        ("Version de grille", prov.get("version_grille") or "—"),
        ("Étape du pipeline", e.get("etape_courante") or "—"),
    ]
    dl = "".join(
        f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in meta
    )
    return (
        f'<header class="band"><p class="eyebrow">Digit-AI — Audit &amp; stratégie SEO</p>'
        f'<h1>Étude SEO — {esc(d["etat"].get("domaine") or "site")}</h1>'
        f'<dl class="meta">{dl}</dl>{repart}</header>'
    )


def bloc_synthese(d: dict, compte: dict) -> str:
    snap = d["snapshot"]
    noeuds = d["noeuds"]
    mesures = sum(1 for n in noeuds if n.get("etat") == "fait")
    hors_mod = sum(1 for n in noeuds if hors_modele(n))
    hors = sum(1 for n in noeuds if n.get("etat") == "hors-perimetre") - hors_mod
    maturite = (snap.get("maturite") or {}).get("score")

    cartes = [
        f'<div class="card"><h3>Couverture</h3><p class="kpi">{mesures}<span class="mono"> / {len(noeuds)}</span>'
        f"<small>nœuds instruits — {hors} non mesurables" + (f", {hors_mod} hors portée du modèle" if hors_mod else "") + "</small></p></div>",
        f'<div class="card"><h3>Maturité</h3><p class="kpi">{barre(maturite, 5, "maturité") if maturite else "n/d"}'
        f"<small>« Machine SEO » — nœud 87</small></p></div>",
        f'<div class="card"><h3>Actions</h3><p class="kpi">{len(d["actions"])}'
        f"<small>chiffrées, priorisées, dispatchées</small></p></div>",
    ]

    cible = snap.get("cible") or {}
    if cible.get("calculable") and cible.get("horizons"):
        h = cible["horizons"][0]
        cartes.append(
            f'<div class="card"><h3>Cible {esc(h.get("echeance_mois"))} mois</h3>'
            f'<p class="kpi">{esc(h.get("borne_basse"))}–{esc(h.get("borne_haute"))} '
            f'{badge_preuve("T4")}<small>{esc(h.get("indicateur"))} — '
            f'{esc(h.get("calcul"))}</small></p></div>'
        )
    else:
        motif = cible.get("motif_non_calculable") or "baseline absente"
        cartes.append(
            f'<div class="card"><h3>Cible 12 mois</h3><p class="kpi">{badge_preuve("NM")}'
            f"<small>non calculable — {esc(motif)}</small></p></div>"
        )

    faibles = [n for n in d["noeuds"] if n.get("verdict") == "non-conforme"]
    tete = ""
    if faibles:
        tete = (
            "<p><b>Le blocage principal</b> — "
            + esc(faibles[0].get("interpretation") or faibles[0].get("constat") or
                  f'{faibles[0]["branche"]} / {faibles[0]["noeud"]}')
            + "</p>"
        )

    manquants = manque_a_fournir(d)
    fournir = ""
    if manquants:
        fournir = (
            "<p><b>Ce qu'il faut fournir</b> pour lever les zones aveugles — "
            + esc(", ".join(manquants))
            + ".</p>"
        )

    return tete + f'<div class="cards">{"".join(cartes)}</div>' + fournir


def manque_a_fournir(d: dict) -> list[str]:
    srcs = (d["snapshot"].get("sources") or {})
    besoin = []
    for cle, libelle in (
        ("gsc", "export Google Search Console"),
        ("ga", "export Google Analytics"),
        ("crm", "données CRM ou e-commerce"),
    ):
        if not (srcs.get(cle) or {}).get("disponible"):
            dossier = d["base"] / "donnees" / cle
            if not dossier.is_dir() or not any(
                p.name != ".gitkeep" for p in dossier.iterdir()
            ):
                besoin.append(libelle)
    return besoin


def constat_li(n: dict, classe: str) -> str:
    tier = (n.get("niveau_preuve") or "").upper()
    if n.get("verdict") == "non-mesure" or n.get("etat") == "hors-perimetre":
        tier = "NM"
    corps = [
        f'<p class="t">{badge_preuve(tier)} {esc(n["branche"])} / {esc(n["noeud"])}</p>'
    ]
    if n.get("constat"):
        corps.append(f"<p>{esc(n['constat'])}</p>")
    if n.get("interpretation"):
        corps.append(f'<p class="m"><b>Mécanisme</b> — {esc(n["interpretation"])}</p>')
    if n.get("motif_hors_perimetre") and n["motif_hors_perimetre"] != "null":
        corps.append(f'<p class="m">{esc(n["motif_hors_perimetre"].strip(chr(34)))}</p>')
    if n.get("preuves"):
        corps.append(f'<p class="src">{esc(n["preuves"])}</p>')
    corps.append(
        f'<p class="trace">nœud {esc(n["id"])} · critère : {esc(n.get("critere_verdict", ""))}</p>'
    )
    return f'<li class="{classe}">{"".join(corps)}</li>'


def bloc_existant(d: dict) -> str:
    faits = [n for n in d["noeuds"] if n.get("etat") == "fait"]
    if not faits:
        return absence(
            "Aucun constat enregistré",
            "Aucune fiche n'est à l'état « fait » : l'étape 2 du pipeline (constat) "
            "n'a pas encore été menée sur cette mission.",
            "renseigner les fiches de seo/analyse/ puis régénérer ce rapport",
        )
    forts = [n for n in faits if n.get("verdict") == "conforme"][:MAX_FORTS]
    faibles = [
        n for n in faits if n.get("verdict") in ("non-conforme", "partiel")
    ][:MAX_FAIBLES]

    out = []
    if forts:
        out.append("<h3>Points forts</h3>")
        out.append(
            f'<ul class="constats">{"".join(constat_li(n, "fort") for n in forts)}</ul>'
        )
    if faibles:
        out.append("<h3>Points faibles, par impact décroissant</h3>")
        out.append(
            f'<ul class="constats">{"".join(constat_li(n, "faible") for n in faibles)}</ul>'
        )
    if not out:
        out.append(
            absence(
                "Aucun verdict tranché",
                "Des fiches sont renseignées mais aucune ne porte de verdict.",
                "renseigner le champ verdict des fiches concernées",
            )
        )
    return "".join(out)


def bloc_pages(d: dict) -> str:
    pages = d["snapshot"].get("pages") or []
    if not pages:
        return absence(
            "Inventaire par URL non collecté",
            "Le rapport par page — code HTTP, profondeur de clic, title, H1, canonical, "
            "indexabilité, liens internes entrants — n'a pas été produit sur cette mission. "
            "Il n'est pas déduit des autres constats : une liste reconstituée serait une "
            "invention présentée comme un inventaire.",
            "lancer la collecte de l'étape 1 avec crawl du site, puis alimenter le bloc "
            "pages[] du snapshot",
        )
    entetes = [
        "URL", "Gabarit", "Prof.", "HTTP", "Title", "H1", "Canonical",
        "Indexable", "Liens int.", "Preuve",
    ]
    lignes = []
    for p in pages:
        lignes.append([
            f'<span class="mono">{esc(p.get("url"))}</span>',
            esc(p.get("type_gabarit")),
            f'<span class="num">{esc(p.get("profondeur_clic"))}</span>',
            f'<span class="num">{esc(p.get("code_http"))}</span>',
            esc(p.get("title")),
            esc(p.get("h1")),
            esc(p.get("canonical")),
            "oui" if p.get("indexable") else "non",
            f'<span class="num">{esc(p.get("liens_internes_entrants"))}</span>',
            badge_preuve(p.get("preuve") or "T1"),
        ])
    ech = d["snapshot"].get("perimetre", {}).get("methode_echantillonnage")
    note = f"<p>Échantillonnage : {esc(ech)}</p>" if ech else ""
    return note + tableau("t-pages", entetes, lignes, "Inventaire des pages analysées",
                          [20, 9, 5, 5, 15, 12, 16, 7, 6, 5])


def bloc_requetes(d: dict) -> str:
    mesures = []
    for n in d["noeuds"]:
        if n["branche"] in ("Mots Clés", "Signaux", "Mesure") and n.get("etat") == "fait":
            mesures.append(n)
    if not mesures:
        return absence(
            "Requêtes et recherches non renseignées",
            "Les branches Mots Clés, Signaux et Mesure ne portent aucun constat. "
            "Sans export Google Search Console, positions, impressions, clics et CTR "
            "SERP sont non observables de l'extérieur et ne seront jamais estimés.",
            "fournir l'export GSC (requêtes, pages, impressions, clics, position) dans "
            "seo/donnees/gsc/",
        )
    lignes = [
        [
            esc(n["branche"]),
            esc(n["noeud"]),
            badge_preuve((n.get("niveau_preuve") or "NM").upper()),
            esc(n.get("constat")),
            esc(n.get("preuves")),
        ]
        for n in mesures
    ]
    return tableau(
        "t-requetes",
        ["Branche", "Nœud", "Preuve", "Constat", "Source"],
        lignes,
        "Résultats des recherches et requêtes",
        [12, 14, 7, 42, 25],
    )


def bloc_actions(d: dict) -> str:
    actions = d["actions"][:MAX_ACTIONS]
    if not actions:
        return absence(
            "Aucune action produite",
            "L'étape 5 du pipeline n'a pas été menée : aucun fichier actions-*.csv "
            "dans seo/livrables/.",
            "produire les actions en suivant seo/METHODE.md, puis régénérer",
        )
    entetes = [
        "ID", "Action", "Volet", "Gain", "Effort", "Confiance", "Score",
        "Horizon", "Exécution", "Coût", "Critère d'acceptation",
    ]
    lignes = []
    for a in actions:
        lignes.append([
            f'<span class="mono">{esc(a.get("id"))}</span>',
            esc(a.get("action") or a.get("libelle")),
            esc(LIBELLE_VOLET.get(a.get("volet", ""), a.get("volet"))),
            barre(a.get("gain"), 5, "gain"),
            barre(a.get("effort"), 5, "effort"),
            barre(a.get("confiance"), 5, "confiance"),
            f'<span class="num">{esc(a.get("score"))}</span>',
            esc(a.get("horizon")),
            esc(a.get("axe_execution")),
            esc(a.get("axe_cout")),
            esc(a.get("critere_acceptation")),
        ])
    return tableau("t-actions", entetes, lignes, "Actions chiffrées et priorisées",
                   [4, 20, 8, 7, 7, 7, 5, 10, 8, 8, 16])


def bloc_gains(d: dict) -> str:
    actions = d["actions"][:MAX_ACTIONS]
    if not actions:
        return absence(
            "Vue gain × effort indisponible",
            "Elle se construit à partir des actions, absentes de cette mission.",
            "produire actions-*.csv",
        )

    def entier(v, defaut=0):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return defaut

    cases: dict[tuple[int, int], list[str]] = {}
    for a in actions:
        g, e = entier(a.get("gain")), entier(a.get("effort"))
        if 1 <= g <= 5 and 1 <= e <= 5:
            cases.setdefault((g, e), []).append(a.get("id") or "?")

    html = ['<div class="mx">']
    html.append('<div class="axl axis-y">Gain →</div>')
    for e in range(1, 6):
        html.append(f'<div class="axl">Effort {e}</div>')
    for g in range(5, 0, -1):
        html.append(f'<div class="axl">Gain {g}</div>')
        for e in range(1, 6):
            ids = cases.get((g, e), [])
            cl = "cell hot" if (g >= 4 and e <= 2) else "cell cold" if (g <= 2 and e >= 4) else "cell"
            chips = "".join(f'<span class="chip">{esc(i)}</span>' for i in ids)
            html.append(f'<div class="{cl}">{chips}</div>')
    html.append("</div>")

    quads = {}
    for a in actions:
        cle = (a.get("axe_execution") or "?", a.get("axe_cout") or "?")
        quads.setdefault(cle, []).append(a)
    blocs = []
    for exe in ("IA", "MANUEL"):
        for cout in ("GRATUIT", "PAYANT"):
            lot = quads.get((exe, cout), [])
            if not lot:
                continue
            lot = sorted(lot, key=lambda a: -float(a.get("score") or 0))
            li = "".join(
                f'<li>{esc(a.get("action") or a.get("libelle"))} '
                f'<span class="cout">score {esc(a.get("score"))}'
                + (f' · {esc(a.get("cout_eur"))}' if a.get("cout_eur") else "")
                + (f' · {esc(a.get("regime_automatisation"))}' if a.get("regime_automatisation") else "")
                + "</span></li>"
                for a in lot
            )
            blocs.append(
                f'<div class="quad"><h3>{esc(exe)} + {esc(cout)} '
                f'<span class="cout">({len(lot)})</span></h3><ol>{li}</ol></div>'
            )

    socle = [
        a for a in actions
        if a.get("axe_execution") == "MANUEL" and a.get("axe_cout") == "PAYANT"
    ]
    # Chaque emphase dans son propre bloc : deux <b> inline dans un meme paragraphe
    # produisent, au retour a la ligne, des boites englobantes qui se croisent — que
    # l'oracle V4 compte comme un chevauchement, a juste titre puisqu'il ne peut pas
    # distinguer un faux positif d'un vrai.
    avert = (
        '<div class="warn"><p class="warn-t">Avertissement sur l\'avantage '
        "concurrentiel</p>"
        "<p>Le quadrant IA + GRATUIT est celui de la plus faible barrière à l'entrée, "
        "donc du plus faible avantage concurrentiel durable : vos concurrents outillés en IA "
        "exécutent les mêmes actions, au même coût, dans le même délai. Elles sont "
        "nécessaires — elles ramènent à la parité — mais elles ne créent pas d'écart.</p>"
    )
    if socle:
        noms = ", ".join(
            (a.get("action") or a.get("libelle") or "?") for a in socle[:3]
        )
        avert += (
            '<p class="warn-t">Socle de différenciation</p>'
            f"<p>Ce qui crée un écart durable est dans MANUEL + PAYANT : {esc(noms)}.</p>"
        )
    else:
        avert += (
            "<p>Aucune action du quadrant MANUEL + PAYANT n'a été retenue : ce plan ramène "
            "à la parité sans construire d'avantage durable. C'est un choix, il doit être "
            "assumé.</p>"
        )
    avert += "</div>"

    return (
        "<h3>Gain × effort</h3>"
        + "".join(html)
        + "<h3>Dispatch en 4 quadrants</h3>"
        + f'<div class="quads">{"".join(blocs)}</div>'
        + avert
    )


def bloc_trajectoire(d: dict) -> str:
    cible = d["snapshot"].get("cible") or {}
    if not cible:
        return absence(
            "Trajectoire non construite",
            "Le volet stratégie (étape 4 du pipeline) n'a pas été mené.",
            "produire la cible 12/24 mois et la trajectoire T1→T4",
        )
    out = []
    for h in cible.get("horizons", []):
        out.append(
            f'<div class="card"><h3>{esc(h.get("echeance_mois"))} mois — '
            f'{esc(h.get("indicateur"))}</h3><p class="kpi">'
            f'{esc(h.get("borne_basse"))} – {esc(h.get("borne_haute"))} '
            f'{esc(h.get("unite", ""))} {badge_preuve("T4")}'
            f'<small>{esc(h.get("calcul"))}</small></p></div>'
        )
    jalons = cible.get("jalons_observables") or []
    if jalons:
        lignes = [
            [esc(j.get("libelle")), esc(j.get("valeur_actuelle")), esc(j.get("valeur_cible")),
             f'{esc(j.get("echeance_mois"))} mois']
            for j in jalons
        ]
        out.append(tableau("t-jalons", ["Jalon", "Actuel", "Cible", "Échéance"], lignes,
                           "Jalons observables"))
    sens = cible.get("sensibilite") or []
    if sens:
        li = "".join(
            f'<li><b>{"⚠ variable la plus fragile — " if s.get("plus_fragile") else ""}'
            f'{esc(s.get("hypothese"))}</b> — {esc(s.get("effet_si_fausse"))}</li>'
            for s in sens
        )
        out.append(f"<h3>Note de sensibilité</h3><ul>{li}</ul>")
    else:
        out.append(
            absence(
                "Note de sensibilité absente",
                "Une projection sans sensibilité déclarée ne dit pas ce qui la casse.",
                "renseigner cible.sensibilite dans le snapshot",
            )
        )
    return f'<div class="cards">{"".join(o for o in out if o.startswith("<div class=\"card\""))}</div>' + "".join(
        o for o in out if not o.startswith('<div class="card"')
    )


def bloc_couverture(d: dict) -> str:
    lignes = []
    for n in d["noeuds"]:
        etat = n.get("etat", "")
        verdict = n.get("verdict") or ""
        motif = (n.get("motif_hors_perimetre") or "").strip('"')
        lignes.append([
            f'<span class="num">{esc(n["id"])}</span>',
            esc(n["branche"]),
            esc(n["noeud"]),
            esc(LIBELLE_VOLET.get(n["volet"], n["volet"])),
            f'{esc(n["statut"])} — {esc(LIBELLE_STATUT.get(n["statut"], ""))}',
            esc(etat),
            esc(LIBELLE_VERDICT.get(verdict, verdict)) or esc(motif) or "—",
        ])
    return (
        f"<p>Les {len(lignes)} nœuds de la grille, aucun omis. "
        "Un nœud hors périmètre avec motif est un résultat, pas une lacune — "
        "qu'il soit non mesurable faute de source, ou hors de la portée du "
        "modèle d'acquisition retenu.</p>"
        + tableau(
            "t-couverture",
            ["#", "Branche", "Nœud", "Volet", "Instrumentation", "État", "Verdict / motif"],
            lignes,
            "Couverture de la grille",
            [4, 13, 15, 9, 20, 10, 29],
        )
    )


def bloc_dette(d: dict) -> str:
    dette = d["snapshot"].get("dette_instrumentation") or []
    if not dette:
        # Ni les nœuds hors portée du modèle, ni les renvois de doublon ne sont une
        # dette : dans les deux cas il n'y a rien à obtenir pour les lever. Les y
        # laisser gonflerait artificiellement ce que le client croit devoir fournir.
        hors = [
            n for n in d["noeuds"]
            if n.get("etat") == "hors-perimetre"
            and not hors_modele(n)
            and n.get("statut") != "RV"
        ]
        if not hors:
            return ("<p>Aucune dette d'instrumentation enregistrée. Les nœuds écartés "
                    "pour cause de modèle d'acquisition ne comptent pas : il n'y a "
                    "rien à obtenir pour les lever.</p>")
        lignes = [
            [f'<span class="num">{esc(n["id"])}</span>', esc(n["branche"]), esc(n["noeud"]),
             esc((n.get("motif_hors_perimetre") or "").strip('"')),
             esc(n.get("source_requise", "").strip('"'))]
            for n in hors
        ]
        return tableau("t-dette", ["#", "Branche", "Nœud", "Motif", "Ce qu'il faut"],
                       lignes, "Dette d'instrumentation")
    lignes = [
        [f'<span class="num">{esc(x.get("noeud_id"))}</span>', esc(x.get("motif")),
         esc(x.get("a_obtenir")), esc(x.get("date_premiere_constatation"))]
        for x in dette
    ]
    return tableau("t-dette", ["#", "Motif", "Ce qu'il faut obtenir", "Constaté le"],
                   lignes, "Dette d'instrumentation")


def bloc_methode(d: dict) -> str:
    prov, snap = d["prov"], d["snapshot"]
    srcs = snap.get("sources") or {}
    lignes = []
    for cle, libelle in (
        ("gsc", "Google Search Console"), ("ga", "Google Analytics"), ("crm", "CRM / e-commerce"),
        ("logs_serveur", "Logs serveur"), ("index_backlinks", "Index de backlinks"),
        ("source_volume", "Source de volume"),
    ):
        s = srcs.get(cle) or {}
        dispo = "oui" if s.get("disponible") else "non"
        periode = (
            f'{s.get("periode_debut")} → {s.get("periode_fin")}'
            if s.get("periode_debut") else "—"
        )
        lignes.append([esc(libelle), esc(dispo), esc(periode), esc(s.get("note") or "")])
    return (
        "<p>Grille des 87 nœuds de <b>forge-seo</b>. Chaque verdict renvoie au nœud et au "
        "critère qui l'a produit — c'est ce qui rend ce rapport opposable plutôt que "
        "déclaratif.</p>"
        f'<p class="trace">version de grille : {esc(prov.get("version_grille") or "—")} · '
        f'étude créée le {esc(prov.get("date_generation") or "—")} · '
        f'sources lues : {esc(d["sources"]["actions"] or "aucun actions-*.csv")}, '
        f'{esc(d["sources"]["snapshot"] or "aucun snapshot-*.json")}</p>'
        + tableau("t-sources", ["Source", "Disponible", "Période", "Note"], lignes,
                  "Disponibilité des sources de données")
        + "<h3>Ce que ce rapport ne peut pas dire</h3>"
        + "<ul>"
        + "".join(f"<li>{esc(x)}</li>" for x in (
            manque_a_fournir(d) or ["toutes les sources déclarées sont disponibles"]
        ))
        + "</ul>"
    )


def bloc_diff(d: dict) -> str:
    prec = d["precedent"]
    if not prec:
        return ""
    a = {x["id"]: x for x in (prec.get("actions") or [])}
    faites = [x for x in a.values() if x.get("statut_execution") == "faite"]
    lignes = [
        [esc(x.get("id")), esc(x.get("libelle")), esc(x.get("statut_execution")),
         esc(x.get("effet_constate") or "aucun effet mesurable")]
        for x in (prec.get("actions") or [])
    ]
    if not lignes:
        return ""
    return section(
        "diff",
        f"Depuis le run précédent — {len(faites)} action(s) menée(s)",
        tableau("t-diff", ["ID", "Action", "Statut", "Effet constaté"], lignes,
                "Comparaison avec le run précédent"),
        replie=True,
    )


# ------------------------------------------------------------------ assemblage


def construire(d: dict) -> str:
    repart, compte = repartition(d["noeuds"])
    domaine = d["etat"].get("domaine") or "site"
    blocs = [
        bloc_bandeau(d, repart),
        legende_preuves(),
        section("synthese", "Synthèse", bloc_synthese(d, compte)),
        section("existant", "L'existant", bloc_existant(d)),
        bloc_diff(d),
        section("pages", "Pages analysées", bloc_pages(d), replie=True),
        section("requetes", "Requêtes et résultats des recherches", bloc_requetes(d), replie=True),
        section("actions", "Actions à mettre en œuvre", bloc_actions(d)),
        section("gains", "Gains et priorités", bloc_gains(d)),
        section("trajectoire", "Trajectoire 12–24 mois", bloc_trajectoire(d), replie=True),
        section("couverture", f"Couverture des {len(d['noeuds'])} nœuds", bloc_couverture(d), replie=True),
        section("dette", "Dette d'instrumentation", bloc_dette(d), replie=True),
        section("methode", "Méthode et traçabilité", bloc_methode(d), replie=True),
    ]
    pied = (
        '<div class="conf"><b>Confidentiel.</b> Ce document contient des données '
        "d'audience, de conversion et de chiffre d'affaires. Il ne doit pas être déposé "
        "sur un hébergement public ni transmis hors du périmètre convenu.</div>"
        f'<footer class="doc">Digit-AI — {esc(d["etat"].get("client") or "client")} · '
        f'{esc(domaine)} · rapport généré par forge-seo, fichier autonome sans appel réseau.'
        "</footer>"
    )
    return page(f"Étude SEO — {domaine}", [b for b in blocs if b], pied)


# ----------------------------------------------------------------- ecriture


def nom_fichier(domaine: str, jour: str, indice: str) -> str:
    # Gabarit D-03. Le conflit prefixe projet / emetteur reste ouvert cote
    # forge-organization : on applique l'hypothese de travail (prefixe Digit-AI
    # pour ce qui sort du projet) EN LA DECLARANT comme hypothese.
    return f"Digit-AI - Audit - SEO {domaine} - {jour}{indice}.html"


def ecrire_rapport(projet: Path, verifier: bool = False) -> int:
    d = collecter(projet)
    html = construire(d)

    livrables = d["base"] / "livrables"
    livrables.mkdir(parents=True, exist_ok=True)
    domaine = d["etat"].get("domaine") or "site"
    jour = dt.date.today().strftime("%Y%m%d")

    existants = sorted(livrables.glob(f"Digit-AI - Audit - SEO {domaine} - *.html"))
    if existants and existants[-1].read_text(encoding="utf-8") == html:
        print(f"identique a {existants[-1].name} — aucun nouvel indice")
        if verifier:
            return controles(existants[-1], html, d)
        return 0

    # Indice alphabetique obligatoire, y compris pour le premier du jour (D-02).
    # Les versions deja archivees comptent : sans elles les lettres se reutilisent,
    # et l'archivage suivant entre en collision avec un fichier de meme nom.
    old = livrables / "Old"
    archives = list(old.glob(f"Digit-AI - Audit - SEO {domaine} - *.html")) if old.is_dir() else []
    pris = {p.stem[-1] for p in existants + archives if p.stem[-9:-1] == jour}
    libres = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in pris]
    if not libres:
        print(f"26 versions deja produites le {jour} pour {domaine} — rien d'ecrit.")
        return 1
    cible = livrables / nom_fichier(domaine, jour, libres[0])

    # Archivage sans effacement (D-02). Sous Windows, rename echoue si la cible
    # existe : on ne veut jamais ecraser une version archivee en silence.
    if existants:
        old.mkdir(exist_ok=True)
        for p in existants:
            dest = old / p.name
            if dest.exists():
                print(f"  ATTENTION {p.name} deja dans Old/ — conserve en place, non archive")
                continue
            p.rename(dest)

    cible.write_text(html, encoding="utf-8")
    print(f"rapport ecrit : {cible.name}")
    print(f"  taille   : {len(html.encode('utf-8')) // 1024} Ko")
    print(f"  archives : {len(existants)} version(s) deplacee(s) dans Old/")
    if verifier:
        return controles(cible, html, d)
    return 0


def controles(chemin: Path, html: str, d: dict) -> int:
    """Controles autonomes du fichier produit. Les oracles de rendu sont
    exterieurs : render_page.py et l'oracle de filtres."""
    echecs = []
    print("\ncontroles du fichier produit")

    reseau = re.findall(r'(?:src|href)\s*=\s*"(?:https?:)?//|@import\s+url\(', html)
    ok = not reseau
    print(f"  [{'OK  ' if ok else 'ECHEC'}] autonomie — aucune requete reseau"
          f" ({len(reseau)} occurrence(s))")
    if not ok:
        echecs.append("autonomie")

    ok = html.count("<h1") == 1
    print(f"  [{'OK  ' if ok else 'ECHEC'}] un seul <h1>")
    if not ok:
        echecs.append("h1")

    ok = 'lang="fr"' in html and 'name="viewport"' in html
    print(f"  [{'OK  ' if ok else 'ECHEC'}] lang=fr + viewport")
    if not ok:
        echecs.append("entete")

    ok = "Syne" not in html
    print(f"  [{'OK  ' if ok else 'ECHEC'}] police Syne absente")
    if not ok:
        echecs.append("charte")

    ok = "tr[data-tf-hidden]{display:table-row!important}" in html.replace(" ", "")
    print(f"  [{'OK  ' if ok else 'ECHEC'}] G6 — lignes filtrees reaffichees a l'impression")
    if not ok:
        echecs.append("G6")

    filtrables = re.findall(r'<table id="([^"]+)" data-filterable', html)
    compteurs = re.findall(r'data-tf-count-for="([^"]+)" aria-live', html)
    ok = set(filtrables) == set(compteurs) and (
        "DigitAITableFilters" in html if filtrables else True
    )
    print(f"  [{'OK  ' if ok else 'ECHEC'}] G2/G3/G5 — {len(filtrables)} tableau(x) "
          f"filtrable(s), compteurs aria-live et init")
    if not ok:
        echecs.append("filtres")

    hex_hors_root = re.findall(r"#[0-9A-Fa-f]{6}", html.split("}", 1)[-1].split("</style>")[0])
    root = html.split(":root{", 1)[-1].split("}", 1)[0] if ":root{" in html else ""
    hors = [h for h in hex_hors_root if h not in root]
    ok = not hors
    print(f"  [{'OK  ' if ok else 'ECHEC'}] aucun hex en dur hors :root"
          f"{'' if ok else ' — ' + ', '.join(sorted(set(hors))[:5])}")
    if not ok:
        echecs.append("tokens")

    print(f"\n{7 - len(echecs)}/7 controles passes")
    return 1 if echecs else 0


def main() -> int:
    p = argparse.ArgumentParser(description="Genere le rapport HTML client d'une etude SEO.")
    p.add_argument("--projet", required=True, help="chemin du projet audite")
    p.add_argument("--verifier", action="store_true", help="controles du fichier produit")
    args = p.parse_args()
    return ecrire_rapport(Path(args.projet), args.verifier)


if __name__ == "__main__":
    sys.exit(main())
