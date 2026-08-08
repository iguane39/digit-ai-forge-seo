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
    borne,
    chapitre,
    esc,
    legende_preuves,
    page,
    recherche_globale,
    resume,
    sommaire,
    strate,
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
    e, prov, cad = d["etat"], d["prov"], d["cadrage"]
    meta = [
        ("Domaine", e.get("domaine") or "—"),
        ("Client", e.get("client") or "—"),
        ("Date du rapport", dt.date.today().isoformat()),
        ("Modèle d'acquisition", e.get("modele_acquisition")
         or champ_cadrage(cad, "Modele d'acquisition") or "non déclaré"),
        ("Marché", champ_cadrage(cad, "Pays / langue") or "non déclaré"),
        ("Audience", champ_cadrage(cad, "Audience du livrable") or "non déclarée"),
        ("Version de grille", prov.get("version_grille") or "—"),
        ("Étape du pipeline", e.get("etape_courante") or "—"),
    ]
    dl = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in meta)
    return (
        '<header class="band"><p class="eyebrow">Digit-AI — Audit &amp; stratégie SEO</p>'
        f'<h1>Étude SEO — {esc(e.get("domaine") or "site")}</h1>'
        f'<dl class="meta">{dl}</dl>{repart}</header>'
    )


# ------------------------------------------------------------------- actions


def _ids(brut) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", str(brut or ""))]


def _cout(a: dict) -> str:
    """Un coût nul ne s'affiche pas comme une donnée — il ne s'affiche pas."""
    v = (a.get("cout_eur") or "").strip()
    if not v or v in ("0", "0.0", "-"):
        return "—" if a.get("axe_cout") == "PAYANT" else "gratuit"
    return v


def _filiere(a: dict) -> str:
    return f'{a.get("axe_execution") or "?"} + {a.get("axe_cout") or "?"}'


def enrichir_actions(d: dict) -> list[dict]:
    """Rattache chaque action aux nœuds qu'elle couvre : c'est de là que viennent le
    « pourquoi » (le mécanisme constaté) et la branche de regroupement."""
    par_id = {n["id"]: n for n in d["noeuds"]}
    out = []
    for a in d["actions"][:MAX_ACTIONS]:
        ids = _ids(a.get("noeuds_couverts"))
        noeuds = [par_id[i] for i in ids if i in par_id]
        mecanismes = [n.get("interpretation") for n in noeuds if n.get("interpretation")]
        out.append({
            **a,
            "_noeuds": noeuds,
            "_branche": noeuds[0]["branche"] if noeuds else "—",
            "_pourquoi": (a.get("hypothese_structurante") or "").strip()
                         or (mecanismes[0] if mecanismes else ""),
            "_filiere": _filiere(a),
            "_cout": _cout(a),
        })
    return out


def bloc_actions(actions: list[dict]) -> str:
    if not actions:
        return absence(
            "Aucune action produite",
            "L'étape 5 du pipeline n'a pas été menée : aucun fichier actions-*.csv "
            "dans seo/livrables/.",
            "sans elle, le rapport constate sans proposer — il n'y a rien à engager.",
            "produire les actions en suivant seo/METHODE.md, puis régénérer",
        )

    colonnes = [
        {"t": "ID", "w": 5, "tri": "num"},
        {"t": "Action", "w": 30, "tri": "txt"},
        {"t": "Branche", "w": 10, "tri": "txt"},
        {"t": "Horizon", "w": 9, "tri": "txt"},
        {"t": "Filière", "w": 10, "tri": "txt"},
        {"t": "Gain", "w": 7, "tri": "num"},
        {"t": "Effort", "w": 7, "tri": "num"},
        {"t": "Confiance", "w": 7, "tri": "num"},
        {"t": "Score", "w": 6, "tri": "num"},
        {"t": "Coût", "w": 9, "tri": "txt"},
    ]

    lignes = []
    for a in actions:
        libelle = a.get("action") or a.get("libelle") or ""
        n1, tronque = resume(libelle)
        noeuds = ", ".join(f'{n["id"]} · {n["noeud"]}' for n in a["_noeuds"]) or "—"
        delai = a.get("delai_effet_mesurable") or a.get("delai_effet_mesurable_jours") or ""
        impact = (
            f'{badge_preuve("T4", compact=True)} gain estimé {esc(a.get("gain"))}/5'
            + (f" · effet mesurable sous {esc(delai)}" if delai else "")
        )
        n2 = [
            ("Énoncé complet", esc(libelle) if tronque else ""),
            ("Pourquoi", esc(borne(a["_pourquoi"])) if a["_pourquoi"] else
             "<i>non renseigné — le mécanisme du nœud couvert n'a pas été instruit</i>"),
            ("Impact attendu", impact),
            ("Critère d'acceptation", esc(a.get("critere_acceptation"))),
            ("Nœuds couverts", esc(noeuds)),
            ("Régime", esc(a.get("regime_automatisation"))),
        ]
        lignes.append([
            (f'<span class="num">{esc(a.get("id"))}</span>', str(_ids(a.get("id")) or [0])[1:-1]),
            strate(esc(n1), "pourquoi et impact", n2),
            esc(a["_branche"]),
            esc(a.get("horizon")),
            esc(a["_filiere"]),
            (barre(a.get("gain"), 5, "gain"), a.get("gain") or ""),
            (barre(a.get("effort"), 5, "effort"), a.get("effort") or ""),
            (barre(a.get("confiance"), 5, "confiance"), a.get("confiance") or ""),
            (f'<span class="num">{esc(a.get("score"))}</span>', a.get("score") or ""),
            esc(a["_cout"]),
        ])

    return (
        "<p>Une ligne par action, l'essentiel visible. <b>« + pourquoi et impact »</b> "
        "déplie le raisonnement sans quitter la ligne. Trier, filtrer, grouper et "
        "chercher agissent sur ce tableau — les vues du chapitre suivant le pilotent.</p>"
        + tableau(
            "t-actions", colonnes, lignes, "Actions à mettre en œuvre",
            groupes=[("Horizon", 3), ("Filière", 4), ("Branche", 2)],
            tri_defaut=(8, -1),
        )
    )


# ------------------------------------------------------- gains et priorites


def bloc_gains(actions: list[dict]) -> str:
    if not actions:
        return absence(
            "Vue gain × effort indisponible",
            "Elle se construit à partir des actions, absentes de cette mission.",
            "sans elle, impossible de voir où sont les gains faciles.",
            "produire actions-*.csv",
        )

    def ent(v, defaut=0):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return defaut

    cases: dict[tuple[int, int], list[dict]] = {}
    for a in actions:
        g, e = ent(a.get("gain")), ent(a.get("effort"))
        if 1 <= g <= 5 and 1 <= e <= 5:
            cases.setdefault((g, e), []).append(a)

    # Masquer les rangees et colonnes vides : 25 cellules pour 12 actions est un
    # mauvais rapport signal/surface.
    gains = sorted({g for g, _ in cases}, reverse=True) or [5, 4, 3, 2, 1]
    efforts = sorted({e for _, e in cases}) or [1, 2, 3, 4, 5]

    cols = f"grid-template-columns:auto repeat({len(efforts)},minmax(0,1fr))"
    html = [f'<div class="mx" style="{cols}">', '<div class="axl axis-y">Gain →</div>']
    for e in efforts:
        html.append(f'<div class="axl">Effort {e}</div>')
    for g in gains:
        html.append(f'<div class="axl">Gain {g}</div>')
        for e in efforts:
            lot = cases.get((g, e), [])
            cl = ("cell hot" if (g >= 4 and e <= 2)
                  else "cell cold" if (g <= 2 and e >= 4) else "cell")
            chips = "".join(
                '<button class="chip" type="button" '
                f"onclick=\"DigitAITableTools.cibler('t-actions','{esc(a.get('id'))}')\" "
                f'title="{esc(a.get("action") or a.get("libelle"))}">'
                f'<b>{esc(a.get("id"))}</b>{esc(resume(a.get("action") or a.get("libelle"), 5)[0])}'
                "</button>"
                for a in sorted(lot, key=lambda x: -float(x.get("score") or 0))
            )
            html.append(f'<div class="{cl}">{chips}</div>')
    html.append("</div>")

    # --- quadrants : compteurs et pilotage, la liste vit dans la table ---------
    quads: dict[str, list[dict]] = {}
    for a in actions:
        quads.setdefault(a["_filiere"], []).append(a)
    cartes = []
    for exe in ("IA", "MANUEL"):
        for cout in ("GRATUIT", "PAYANT"):
            cle = f"{exe} + {cout}"
            lot = sorted(quads.get(cle, []), key=lambda x: -float(x.get("score") or 0))
            tete = (resume(lot[0].get("action") or lot[0].get("libelle"), 8)[0]
                    if lot else "—")
            cartes.append(
                f'<div class="quad"><h3>{esc(cle)}</h3>'
                f'<p class="q-n">{len(lot)}</p>'
                f'<p class="q-d">action{"s" if len(lot) > 1 else ""} · '
                f'effort cumulé {sum(ent(a.get("effort")) for a in lot)} j-h estimés</p>'
                f'<p class="q-a">En tête : {esc(tete)}</p>'
                + (
                    '<button type="button" onclick="DigitAITableTools.cibler'
                    f"('t-actions','{esc(cle)}')\">Voir ces {len(lot)} actions</button>"
                    if lot else ""
                )
                + "</div>"
            )

    socle = quads.get("MANUEL + PAYANT", [])
    avert = (
        '<div class="warn"><p class="warn-t">Avertissement sur l\'avantage concurrentiel</p>'
        "<p>Le quadrant IA + GRATUIT est celui de la plus faible barrière à l'entrée, donc "
        "du plus faible avantage concurrentiel durable : vos concurrents outillés en IA "
        "exécutent les mêmes actions, au même coût, dans le même délai. Elles sont "
        "nécessaires — elles ramènent à la parité — mais elles ne créent pas d'écart.</p>"
    )
    if socle:
        noms = ", ".join(
            resume(a.get("action") or a.get("libelle"), 7)[0] for a in socle[:3]
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
        "<p>Chaque pastille est un bouton : elle <b>filtre le tableau des actions</b> "
        "ci-dessus. Les rangées et colonnes vides sont masquées.</p>"
        "<h3>Gain × effort</h3>" + "".join(html)
        + "<h3>Dispatch en 4 quadrants</h3>"
        + f'<div class="quads">{"".join(cartes)}</div>' + avert
    )


# ---------------------------------------------------------------- synthese


def manque_a_fournir(d: dict) -> list[str]:
    """Sources absentes du snapshot ET du dossier donnees/ — ce qu'il faut demander."""
    srcs = d["snapshot"].get("sources") or {}
    besoin = []
    for cle, libelle in (
        ("gsc", "export Google Search Console"),
        ("ga", "export Google Analytics"),
        ("crm", "données CRM ou e-commerce"),
    ):
        if (srcs.get(cle) or {}).get("disponible"):
            continue
        dossier = d["base"] / "donnees" / cle
        if not dossier.is_dir() or not any(
            p.name != ".gitkeep" for p in dossier.iterdir()
        ):
            besoin.append(libelle)
    return besoin


def bloc_synthese(d: dict, actions: list[dict], compte: dict) -> str:
    """Un lecteur qui ne lit que ce chapitre doit pouvoir décider."""
    snap, noeuds = d["snapshot"], d["noeuds"]
    faits = sum(1 for n in noeuds if n.get("etat") == "fait")
    hors_mod = sum(1 for n in noeuds if hors_modele(n))
    hors = sum(1 for n in noeuds if n.get("etat") == "hors-perimetre") - hors_mod
    maturite = (snap.get("maturite") or {}).get("score")

    faibles = [n for n in noeuds if n.get("verdict") == "non-conforme"]
    blocage = ""
    if faibles:
        blocage = (faibles[0].get("interpretation") or faibles[0].get("constat")
                   or f'{faibles[0]["branche"]} / {faibles[0]["noeud"]}')

    verdict = ["<p><b>Le constat</b> — "]
    verdict.append(
        esc(f"{faits} nœuds instruits sur {len(noeuds)} ; "
            f"{len(faibles)} verdicts non conformes.")
        + "</p>"
    )
    if blocage:
        verdict.append(f"<p><b>Le blocage principal</b> — {esc(borne(blocage, 45))}</p>")
    manquants = manque_a_fournir(d)
    if manquants:
        verdict.append(
            "<p><b>Ce qu'il faut fournir</b> — " + esc(", ".join(manquants)) + ".</p>"
        )

    cartes = [
        f'<div class="card"><h3>Couverture</h3><p class="kpi">{faits}'
        f'<span class="mono"> / {len(noeuds)}</span>'
        f"<small>nœuds instruits — {hors} non mesurables"
        + (f", {hors_mod} hors portée du modèle" if hors_mod else "")
        + "</small></p></div>",
        '<div class="card"><h3>Maturité</h3><p class="kpi">'
        + (barre(maturite, 5, "maturité") if maturite else "n/d")
        + "<small>« Machine SEO » — nœud 87</small></p></div>",
        f'<div class="card"><h3>Actions</h3><p class="kpi">{len(actions)}'
        "<small>chiffrées, priorisées, dispatchées</small></p></div>",
    ]
    cible = snap.get("cible") or {}
    if cible.get("calculable") and cible.get("horizons"):
        h = cible["horizons"][0]
        cartes.append(
            f'<div class="card"><h3>Cible {esc(h.get("echeance_mois"))} mois</h3>'
            f'<p class="kpi">{esc(h.get("borne_basse"))}–{esc(h.get("borne_haute"))} '
            f'{badge_preuve("T4", compact=True)}'
            f'<small>{esc(borne(str(h.get("indicateur")) + " — " + str(h.get("calcul")), 22))}'
            "</small></p></div>"
        )
    else:
        cartes.append(
            '<div class="card"><h3>Cible 12 mois</h3><p class="kpi">'
            + badge_preuve("NM", compact=True)
            + "<small>non calculable — "
            + esc(cible.get("motif_non_calculable") or "baseline absente")
            + "</small></p></div>"
        )

    top = ""
    if actions:
        # FIGÉES : les trois premières par score, pas « les trois du tri courant ».
        trois = sorted(actions, key=lambda a: -float(a.get("score") or 0))[:3]
        li = "".join(
            f'<li><span class="t">{esc(resume(a.get("action") or a.get("libelle"), 14)[0])}</span>'
            f'<span class="m">{esc(a.get("id"))} · gain {esc(a.get("gain"))}/5 · '
            f'effort {esc(a.get("effort"))}/5 · {esc(a.get("horizon"))} · '
            f'{esc(a["_filiere"])}</span></li>'
            for a in trois
        )
        top = f"<h3>Les 3 actions qui comptent</h3><ul class=\"top3\">{li}</ul>"

    return (
        f'<div class="verdict">{"".join(verdict)}</div>'
        f'<div class="cards">{"".join(cartes)}</div>{top}{legende_preuves()}'
    )


# ---------------------------------------------------------------- existant


def constat_li(n: dict, classe: str) -> str:
    tier = (n.get("niveau_preuve") or "").upper()
    if n.get("verdict") == "non-mesure" or n.get("etat") == "hors-perimetre":
        tier = "NM"
    n1, tronque = resume(n.get("constat") or f'{n["branche"]} / {n["noeud"]}', 16)
    n2 = [
        ("Constat complet", esc(n.get("constat")) if tronque else ""),
        ("Mécanisme", esc(borne(n.get("interpretation")))),
        ("Question d'audit", esc(n.get("question_audit"))),
        ("Critère de verdict", esc(n.get("critere_verdict"))),
        ("Preuves", esc(n.get("preuves"))),
        ("Motif", esc((n.get("motif_hors_perimetre") or "").strip('"'))),
    ]
    return (
        f'<li class="{classe}">'
        f'<p class="t">{badge_preuve(tier)} {esc(n["branche"])} / {esc(n["noeud"])}</p>'
        + strate(esc(n1), "détail, mécanisme et preuves", n2)
        + f'<p class="trace">nœud {esc(n["id"])}</p></li>'
    )


def bloc_existant(d: dict) -> str:
    faits = [n for n in d["noeuds"] if n.get("etat") == "fait"]
    if not faits:
        return absence(
            "Aucun constat enregistré",
            "Aucune fiche n'est à l'état « fait » : l'étape 2 du pipeline (constat) "
            "n'a pas été menée sur cette mission.",
            "le rapport ne peut rien affirmer sur l'état du site.",
            "renseigner les fiches de seo/analyse/ puis régénérer ce rapport",
        )
    forts = [n for n in faits if n.get("verdict") == "conforme"][:MAX_FORTS]
    faibles = [n for n in faits if n.get("verdict") in ("non-conforme", "partiel")][:MAX_FAIBLES]
    out = []
    if faibles:
        out.append(f"<h3>Points faibles, par impact décroissant ({len(faibles)})</h3>")
        out.append('<ul class="constats">'
                   + "".join(constat_li(n, "faible") for n in faibles) + "</ul>")
    if forts:
        out.append(f"<h3>Points forts ({len(forts)})</h3>")
        out.append('<ul class="constats">'
                   + "".join(constat_li(n, "fort") for n in forts) + "</ul>")
    if not out:
        out.append(absence(
            "Aucun verdict tranché",
            "Des fiches sont renseignées mais aucune ne porte de verdict.",
            "impossible de distinguer ce qui va de ce qui ne va pas.",
            "renseigner le champ verdict des fiches concernées",
        ))
    return "".join(out)


# ------------------------------------------------------------------ requetes


def bloc_requetes(d: dict) -> str:
    mesures = [
        n for n in d["noeuds"]
        if n["branche"] in ("Mots Clés", "Signaux", "Mesure", "Idée")
        and n.get("etat") == "fait"
    ]
    if not mesures:
        return absence(
            "Requêtes et recherches non renseignées",
            "Les branches Mots Clés, Signaux, Mesure et Idée ne portent aucun constat. "
            "Sans export Google Search Console, positions, impressions, clics et CTR "
            "SERP sont non observables de l'extérieur et ne seront jamais estimés.",
            "aucune requête ne peut être priorisée par sa demande réelle : la stratégie "
            "repose sur le potentiel supposé, pas sur la demande mesurée.",
            "fournir l'export GSC (requêtes, pages, impressions, clics, position) dans "
            "seo/donnees/gsc/",
        )
    colonnes = [
        {"t": "Nœud", "w": 16, "tri": "txt"},
        {"t": "Branche", "w": 11, "tri": "txt"},
        {"t": "Preuve", "w": 8, "tri": "txt"},
        {"t": "Constat et mécanisme", "w": 40, "tri": "txt"},
        {"t": "Verdict", "w": 11, "tri": "txt"},
        {"t": "Source", "w": 14, "tri": "txt"},
    ]
    lignes = []
    for n in mesures:
        n1, tronque = resume(n.get("constat"), 14)
        n2 = [
            ("Constat complet", esc(n.get("constat")) if tronque else ""),
            ("Question d'audit", esc(n.get("question_audit"))),
            ("Critère de verdict", esc(n.get("critere_verdict"))),
            ("Mécanisme", esc(borne(n.get("interpretation")))),
        ]
        v = n.get("verdict") or ""
        lignes.append([
            f'{esc(n["noeud"])} <span class="trace">#{esc(n["id"])}</span>',
            esc(n["branche"]),
            badge_preuve((n.get("niveau_preuve") or "NM").upper()),
            strate(esc(n1), "question, critère, mécanisme", n2),
            esc(LIBELLE_VERDICT.get(v, v)),
            esc(borne(n.get("preuves"), 12)),
        ])
    return (
        "<p>Ce que cherchait chaque nœud, ce qui a été mesuré, et ce que l'écart coûte. "
        "Déplier une ligne donne la question d'audit et le critère qui produit le verdict "
        "— c'est ce qui rend le constat opposable.</p>"
        + tableau("t-requetes", colonnes, lignes, "Requêtes et résultats des recherches",
                  groupes=[("Branche", 1), ("Verdict", 4)], tri_defaut=(1, 1))
    )


# ------------------------------------------------------------------- pages


def bloc_pages(d: dict) -> str:
    pages = d["snapshot"].get("pages") or []
    if not pages:
        return absence(
            "Inventaire par URL non collecté",
            "Le rapport par page — code HTTP, profondeur de clic, title, H1, canonical, "
            "indexabilité, liens internes entrants — n'a pas été produit sur cette "
            "mission. Il n'est pas déduit des autres constats : une liste reconstituée "
            "serait une invention présentée comme un inventaire.",
            "sans lui, impossible de lister les pages en erreur, de mesurer la "
            "profondeur de clic réelle, ni de dire quelles pages sont orphelines. Les "
            "constats restent au niveau du site, jamais de la page.",
            "lancer la collecte de l'étape 1 avec crawl du site, puis alimenter le bloc "
            "pages[] du snapshot",
        )
    colonnes = [
        {"t": "URL", "w": 26, "tri": "txt"},
        {"t": "Gabarit", "w": 10, "tri": "txt"},
        {"t": "Prof.", "w": 6, "tri": "num"},
        {"t": "HTTP", "w": 6, "tri": "num"},
        {"t": "Title", "w": 18, "tri": "txt"},
        {"t": "H1", "w": 12, "tri": "txt"},
        {"t": "Indexable", "w": 8, "tri": "txt"},
        {"t": "Liens int.", "w": 8, "tri": "num"},
        {"t": "Preuve", "w": 6, "tri": "txt"},
    ]
    lignes = []
    for p in pages:
        lignes.append([
            f'<span class="mono">{esc(p.get("url"))}</span>',
            esc(p.get("type_gabarit")),
            (f'<span class="num">{esc(p.get("profondeur_clic"))}</span>',
             p.get("profondeur_clic") or ""),
            (f'<span class="num">{esc(p.get("code_http"))}</span>', p.get("code_http") or ""),
            esc(p.get("title")),
            esc(p.get("h1")),
            "oui" if p.get("indexable") else "non",
            (f'<span class="num">{esc(p.get("liens_internes_entrants"))}</span>',
             p.get("liens_internes_entrants") or ""),
            badge_preuve(p.get("preuve") or "T1", compact=True),
        ])
    ech = d["snapshot"].get("perimetre", {}).get("methode_echantillonnage")
    note = f"<p>Échantillonnage : {esc(ech)}</p>" if ech else ""
    return note + tableau(
        "t-pages", colonnes, lignes, "Inventaire des pages analysées",
        groupes=[("Gabarit", 1), ("Indexable", 6), ("Code HTTP", 3)],
        tri_defaut=(2, 1),
    )


# --------------------------------------------------------------- trajectoire


def bloc_trajectoire(d: dict) -> str:
    cible = d["snapshot"].get("cible") or {}
    if not cible:
        return absence(
            "Trajectoire non construite",
            "Le volet stratégie (étape 4 du pipeline) n'a pas été mené.",
            "le client sait ce qui ne va pas, pas où il peut aller.",
            "produire la cible 12/24 mois et la trajectoire T1→T4",
        )
    cartes = [
        f'<div class="card"><h3>{esc(h.get("echeance_mois"))} mois — '
        f'{esc(h.get("indicateur"))}</h3><p class="kpi">'
        f'{esc(h.get("borne_basse"))} – {esc(h.get("borne_haute"))} '
        f'{esc(h.get("unite", ""))} {badge_preuve("T4", compact=True)}'
        f'<small>{esc(h.get("calcul"))}</small></p></div>'
        for h in cible.get("horizons", [])
    ]
    out = f'<div class="cards">{"".join(cartes)}</div>' if cartes else ""

    jalons = cible.get("jalons_observables") or []
    if jalons:
        colonnes = [
            {"t": "Jalon", "w": 46, "tri": "txt"},
            {"t": "Actuel", "w": 18, "tri": "txt"},
            {"t": "Cible", "w": 18, "tri": "txt"},
            {"t": "Échéance", "w": 18, "tri": "num"},
        ]
        lignes = [
            [esc(j.get("libelle")), esc(j.get("valeur_actuelle")), esc(j.get("valeur_cible")),
             (f'{esc(j.get("echeance_mois"))} mois', j.get("echeance_mois") or "")]
            for j in jalons
        ]
        out += "<h3>Jalons observables</h3>" + tableau(
            "t-jalons", colonnes, lignes, "Jalons observables", tri_defaut=(3, 1)
        )

    sens = cible.get("sensibilite") or []
    if sens:
        li = "".join(
            "<li>"
            + f'<b>{"⚠ variable la plus fragile — " if s.get("plus_fragile") else ""}'
            + f'{esc(s.get("hypothese"))}</b> — {esc(s.get("effet_si_fausse"))}</li>'
            for s in sens
        )
        out += f"<h3>Note de sensibilité</h3><ul>{li}</ul>"
    else:
        out += absence(
            "Note de sensibilité absente",
            "Une projection sans sensibilité déclarée ne dit pas ce qui la casse.",
            "la cible paraît ferme alors qu'elle repose sur des hypothèses non nommées.",
            "renseigner cible.sensibilite dans le snapshot",
        )
    return out


# --------------------------------------------------------------- couverture


def bloc_couverture(d: dict) -> str:
    colonnes = [
        {"t": "#", "w": 5, "tri": "num"},
        {"t": "Nœud", "w": 18, "tri": "txt"},
        {"t": "Branche", "w": 13, "tri": "txt"},
        {"t": "Volet", "w": 10, "tri": "txt"},
        {"t": "Instrumentation", "w": 18, "tri": "txt"},
        {"t": "État", "w": 12, "tri": "txt"},
        {"t": "Verdict / motif", "w": 24, "tri": "txt"},
    ]
    lignes = []
    for n in d["noeuds"]:
        v = n.get("verdict") or ""
        motif = (n.get("motif_hors_perimetre") or "").strip('"')
        lignes.append([
            (f'<span class="num">{esc(n["id"])}</span>', n["id"]),
            esc(n["noeud"]),
            esc(n["branche"]),
            esc(LIBELLE_VOLET.get(n["volet"], n["volet"])),
            f'{esc(n["statut"])} — {esc(LIBELLE_STATUT.get(n["statut"], ""))}',
            esc(n.get("etat")),
            esc(LIBELLE_VERDICT.get(v, v)) or esc(borne(motif, 14)) or "—",
        ])
    return (
        f"<p>Les {len(lignes)} nœuds de la grille, aucun omis. Un nœud hors périmètre "
        "avec motif est un résultat, pas une lacune — qu'il soit non mesurable faute de "
        "source, ou hors de la portée du modèle d'acquisition retenu.</p>"
        + tableau("t-couverture", colonnes, lignes, "Couverture de la grille",
                  groupes=[("Branche", 2), ("Volet", 3), ("État", 5),
                           ("Instrumentation", 4)],
                  tri_defaut=(0, 1))
    )


# --------------------------------------------------------------------- dette


def bloc_dette(d: dict) -> str:
    dette = d["snapshot"].get("dette_instrumentation") or []
    # Ni les nœuds hors portée du modèle, ni les renvois de doublon ne sont une
    # dette : dans les deux cas il n'y a rien à obtenir pour les lever.
    hors = [
        n for n in d["noeuds"]
        if n.get("etat") == "hors-perimetre"
        and not hors_modele(n) and n.get("statut") != "RV"
    ]
    colonnes = [
        {"t": "#", "w": 6, "tri": "num"},
        {"t": "Nœud", "w": 22, "tri": "txt"},
        {"t": "Motif", "w": 36, "tri": "txt"},
        {"t": "Ce qu'il faut obtenir", "w": 36, "tri": "txt"},
    ]
    lignes = []
    par_id = {n["id"]: n for n in d["noeuds"]}
    for x in dette:
        n = par_id.get(x.get("noeud_id"), {})
        lignes.append([
            (f'<span class="num">{esc(x.get("noeud_id"))}</span>', x.get("noeud_id") or ""),
            esc(n.get("noeud") or "—"),
            esc(x.get("motif")),
            esc(x.get("a_obtenir")),
        ])
    vus = {x.get("noeud_id") for x in dette}
    for n in hors:
        if n["id"] in vus:
            continue
        lignes.append([
            (f'<span class="num">{esc(n["id"])}</span>', n["id"]),
            esc(n["noeud"]),
            esc((n.get("motif_hors_perimetre") or "").strip('"')),
            esc((n.get("source_requise") or "").strip('"')),
        ])
    if not lignes:
        return ("<p>Aucune dette d'instrumentation. Les nœuds écartés pour cause de "
                "modèle d'acquisition, comme les renvois de doublon, ne comptent pas : "
                "il n'y a rien à obtenir pour les lever.</p>")
    return (
        "<p>Ce qui n'a pas pu être mesuré, pourquoi, et ce qu'il faudrait fournir. "
        "Les nœuds hors portée du modèle n'y figurent pas.</p>"
        + tableau("t-dette", colonnes, lignes, "Dette d'instrumentation",
                  tri_defaut=(0, 1))
    )


# ------------------------------------------------------------------- methode


def bloc_methode(d: dict) -> str:
    prov, snap = d["prov"], d["snapshot"]
    srcs = snap.get("sources") or {}
    colonnes = [
        {"t": "Source", "w": 26, "tri": "txt"},
        {"t": "Disponible", "w": 14, "tri": "txt"},
        {"t": "Période", "w": 26, "tri": "txt"},
        {"t": "Note", "w": 34, "tri": "txt"},
    ]
    lignes = []
    for cle, libelle in (
        ("gsc", "Google Search Console"), ("ga", "Google Analytics"),
        ("crm", "CRM / e-commerce"), ("logs_serveur", "Logs serveur"),
        ("index_backlinks", "Index de backlinks"), ("source_volume", "Source de volume"),
    ):
        s = srcs.get(cle) or {}
        periode = (f'{s.get("periode_debut")} → {s.get("periode_fin")}'
                   if s.get("periode_debut") else "—")
        lignes.append([esc(libelle), "oui" if s.get("disponible") else "non",
                       esc(periode), esc(s.get("note") or "")])
    manquants = manque_a_fournir(d)
    return (
        "<p>Grille des nœuds de <b>forge-seo</b>. Chaque verdict renvoie au nœud et au "
        "critère qui l'a produit — c'est ce qui rend ce rapport opposable plutôt que "
        "déclaratif.</p>"
        f'<p class="trace">version de grille : {esc(prov.get("version_grille") or "—")} · '
        f'étude créée le {esc(prov.get("date_generation") or "—")} · '
        f'sources lues : {esc(d["sources"]["actions"] or "aucun actions-*.csv")}, '
        f'{esc(d["sources"]["snapshot"] or "aucun snapshot-*.json")}</p>'
        + tableau("t-sources", colonnes, lignes, "Disponibilité des sources", tri_defaut=(0, 1))
        + "<h3>Ce que ce rapport ne peut pas dire</h3><ul>"
        + "".join(f"<li>{esc(x)}</li>" for x in
                  (manquants or ["toutes les sources déclarées sont disponibles"]))
        + "</ul>"
    )


# ---------------------------------------------------------------------- diff


def bloc_diff(d: dict) -> str:
    prec = d["precedent"]
    if not prec or not (prec.get("actions") or []):
        return ""
    colonnes = [
        {"t": "ID", "w": 8, "tri": "num"},
        {"t": "Action", "w": 38, "tri": "txt"},
        {"t": "Statut", "w": 16, "tri": "txt"},
        {"t": "Effet constaté", "w": 38, "tri": "txt"},
    ]
    lignes = [
        [(f'<span class="num">{esc(x.get("id"))}</span>', x.get("id") or ""),
         esc(resume(x.get("libelle"), 14)[0]),
         esc(x.get("statut_execution")),
         esc(x.get("effet_constate") or "aucun effet mesurable")]
        for x in prec["actions"]
    ]
    faites = sum(1 for x in prec["actions"] if x.get("statut_execution") == "faite")
    return (
        f"<p><b>{faites}</b> action(s) menée(s) depuis le run précédent. "
        "C'est la progression, pas le constat, que mesure ce chapitre.</p>"
        + tableau("t-diff", colonnes, lignes, "Comparaison avec le run précédent",
                  groupes=[("Statut", 2)], tri_defaut=(0, 1))
    )


# ------------------------------------------------------------------ assemblage


def construire(d: dict) -> str:
    repart, compte = repartition(d["noeuds"])
    actions = enrichir_actions(d)
    domaine = d["etat"].get("domaine") or "site"

    npages = len(d["snapshot"].get("pages") or [])
    plan = [
        ("synthese", "Synthèse", "décider en une page", bloc_synthese(d, actions, compte), "", ""),
        ("existant", "L'existant", "ce qui a été mesuré, et ce que l'écart coûte",
         bloc_existant(d), "", ""),
        ("actions", "Actions à mettre en œuvre", "chiffrées, priorisées, dispatchées",
         bloc_actions(actions), str(len(actions)) if actions else "", ""),
        ("gains", "Gains et priorités", "où sont les gains faciles, et par quelle filière",
         bloc_gains(actions), "", ""),
        ("trajectoire", "Trajectoire 12–24 mois", "où le site peut aller, et à quelles conditions",
         bloc_trajectoire(d), "", ""),
        ("requetes", "Requêtes et résultats", "constat → nœud → critère → mécanisme",
         bloc_requetes(d), "", ""),
        ("pages", "Pages analysées", "l'inventaire par URL", bloc_pages(d),
         str(npages) if npages else "",
         f"Afficher l'inventaire des {npages} URL" if npages else ""),
        ("couverture", "Couverture de la grille", "tous les nœuds, aucun omis",
         bloc_couverture(d), str(len(d["noeuds"])),
         f"Afficher les {len(d['noeuds'])} nœuds"),
        ("dette", "Dette d'instrumentation", "ce qu'il faudrait pour mesurer plus",
         bloc_dette(d), "", "Afficher la dette"),
        ("methode", "Méthode et traçabilité", "sur quoi ce rapport repose",
         bloc_methode(d), "", "Afficher les sources et la traçabilité"),
    ]
    diff = bloc_diff(d)
    if diff:
        plan.insert(1, ("diff", "Depuis le run précédent", "ce qui a bougé", diff, "", ""))

    chapitres, entrees = [], []
    for num, (ident, titre, st, corps, compt, annexe) in enumerate(plan, start=1):
        chapitres.append(chapitre(num, ident, titre, corps, st, annexe))
        entrees.append((num, ident, titre, compt))

    blocs = [
        bloc_bandeau(d, repart),
        f'<div class="sticky"><div class="sticky-in">{sommaire(entrees)}'
        f"{recherche_globale()}</div></div>",
        *chapitres,
    ]
    pied = (
        '<div class="conf"><b>Confidentiel.</b> Ce document contient des données '
        "d'audience, de conversion et de chiffre d'affaires. Il ne doit pas être déposé "
        "sur un hébergement public ni transmis hors du périmètre convenu.</div>"
        f'<footer class="doc">Digit-AI — {esc(d["etat"].get("client") or "client")} · '
        f"{esc(domaine)} · rapport généré par forge-seo, fichier autonome sans appel "
        "réseau.</footer>"
    )
    return page(f"Étude SEO — {domaine}", blocs, pied)


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

    # Un seul <script> doit exister. Un `</script>` echappe dans un commentaire de
    # composant inline termine l'element : le reste du JS devient du HTML mort, la
    # page s'affiche normalement et plus aucune interaction ne fonctionne.
    ok = html.count("</script") == 1
    print(f"  [{'OK  ' if ok else 'ECHEC'}] JS non tronqué — "
          f"{html.count('</script')} fermeture(s) de script (1 attendue)")
    if not ok:
        echecs.append("script")

    ok = "tr[data-tf-hidden]{display:table-row!important}" in html.replace(" ", "")
    print(f"  [{'OK  ' if ok else 'ECHEC'}] G6 — lignes filtrees reaffichees a l'impression")
    if not ok:
        echecs.append("G6")

    # Tout tableau filtrable doit avoir son compteur ; l'inverse n'est pas vrai, les
    # tableaux courts portent une barre d'outils sans filtres de colonne.
    filtrables = re.findall(r'<table id="([^"]+)"[^>]* data-filterable', html)
    compteurs = re.findall(r'data-tf-count-for="([^"]+)" aria-live', html)
    ok = set(filtrables) <= set(compteurs) and (
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

    print(f"\n{8 - len(echecs)}/8 controles passes")
    return 1 if echecs else 0


def main() -> int:
    p = argparse.ArgumentParser(description="Genere le rapport HTML client d'une etude SEO.")
    p.add_argument("--projet", required=True, help="chemin du projet audite")
    p.add_argument("--verifier", action="store_true", help="controles du fichier produit")
    args = p.parse_args()
    return ecrire_rapport(Path(args.projet), args.verifier)


if __name__ == "__main__":
    sys.exit(main())
