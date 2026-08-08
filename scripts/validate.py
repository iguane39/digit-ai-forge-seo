"""Controles durs du referentiel forge-seo.

Neuf controles. Sortie non-zero des qu'un seul echoue : ce script existe pour
attraper exactement le mode d'echec le plus dangereux du projet -- une
arborescence fausse qui passe au vert.

Usage :
    python scripts/validate.py

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from grille import NB_BRANCHES, NB_NOEUDS, RACINE, lire

SEO = RACINE / "seo"
TEMPLATE = RACINE / "missions" / "_TEMPLATE"

RE_SLUG_BRANCHE = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_SLUG_NOEUD = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")

CHAMPS_FICHE = [
    "id",
    "branche",
    "noeud",
    "volet",
    "statut_instrumentation",
    "source_requise",
    "doublon_de",
    "etat",
    "motif_hors_perimetre",
    "verdict",
    "niveau_preuve",
    "date_mesure",
    "actions_liees",
]

ETATS = {"a-faire", "en-cours", "fait", "hors-perimetre"}


class Rapport:
    def __init__(self) -> None:
        self.echecs: list[str] = []
        self.controles = 0

    def controle(self, nom: str, ok: bool, detail: str = "") -> None:
        self.controles += 1
        marque = "OK  " if ok else "ECHEC"
        print(f"  [{marque}] {nom}" + (f" -- {detail}" if detail else ""))
        if not ok:
            self.echecs.append(nom)


def front_matter(chemin: Path) -> dict:
    """Lecture du front-matter plat. Pas de dependance externe : le format est
    volontairement simple (cle: valeur, listes vides), et le rester est un
    controle en soi."""
    texte = chemin.read_text(encoding="utf-8")
    if not texte.startswith("---\n"):
        raise ValueError("pas de front-matter")
    fin = texte.index("\n---\n", 3)
    champs: dict[str, str] = {}
    for ligne in texte[4:fin].split("\n"):
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        if ":" not in ligne:
            raise ValueError(f"ligne de front-matter illisible : {ligne!r}")
        cle, val = ligne.split(":", 1)
        champs[cle.strip()] = val.strip()
    return champs


def dossiers_seo() -> tuple[list[Path], list[Path]]:
    branches = sorted(p for p in SEO.iterdir() if p.is_dir())
    feuilles = sorted(f for b in branches for f in b.iterdir() if f.is_dir())
    return branches, feuilles


def main() -> int:
    r = Rapport()
    print("validate -- referentiel forge-seo\n")

    if not SEO.exists():
        print("  seo/ absent. Lancer d'abord : python scripts/scaffold.py")
        return 1

    donnees = lire()
    manifeste = json.loads((SEO / "manifest.json").read_text(encoding="utf-8"))
    branches, feuilles = dossiers_seo()

    # 1 -- comptes exacts
    r.controle(
        "1. 16 branches, 82 feuilles, 98 dossiers sous seo/",
        len(branches) == NB_BRANCHES
        and len(feuilles) == NB_NOEUDS
        and len(branches) + len(feuilles) == NB_BRANCHES + NB_NOEUDS,
        f"{len(branches)} branches, {len(feuilles)} feuilles, "
        f"{len(branches) + len(feuilles)} au total",
    )

    # 2 -- identifiants contigus
    ids = sorted(n["id"] for n in manifeste["noeuds"])
    r.controle(
        "2. identifiants 1-82 sans trou ni doublon",
        ids == list(range(1, NB_NOEUDS + 1)),
        f"{len(ids)} identifiants, min {ids[0]}, max {ids[-1]}",
    )

    # 3 -- les 2 renvois : presents, marques, non remplissables
    renvois = [n for n in manifeste["noeuds"] if n["statut"] == "RV"]
    ok = len(renvois) == 2
    detail = []
    for n in renvois:
        fiche = SEO / n["chemin"] / "_fiche.md"
        if not fiche.exists():
            ok = False
            detail.append(f"{n['chemin']} sans fiche")
            continue
        fm = front_matter(fiche)
        corps = fiche.read_text(encoding="utf-8").split("\n---\n", 1)[1]
        if n["doublon_de"] is None or fm.get("doublon_de") in (None, "null"):
            ok = False
            detail.append(f"{n['chemin']} sans doublon_de")
        if fm.get("etat") != "hors-perimetre" or "## Constat" in corps:
            ok = False
            detail.append(f"{n['chemin']} a des champs a remplir")
        detail.append(f"{n['chemin']} -> {n['doublon_de']}")
    r.controle(
        "3. les 2 renvois portent doublon_de et n'ont aucun champ a remplir",
        ok,
        " ; ".join(detail),
    )

    # 4 -- ordre methodologique des branches
    rangs = [b["rang"] for b in manifeste["branches"]]
    noms_attendus = [b["nom"] for b in donnees["branches"]]
    noms_manifeste = [b["nom"] for b in manifeste["branches"]]
    r.controle(
        "4. ordre des branches conforme a la sequence du schema",
        rangs == list(range(1, NB_BRANCHES + 1)) and noms_manifeste == noms_attendus,
        f"{noms_manifeste[0]} -> {noms_manifeste[-1]}",
    )

    # 5 -- slugs ASCII kebab-case prefixes
    mauvais = [
        p.name
        for p in branches
        if not RE_SLUG_BRANCHE.match(p.name)
    ] + [p.name for p in feuilles if not RE_SLUG_NOEUD.match(p.name)]
    non_ascii = [
        p.name for p in branches + feuilles if not p.name.isascii()
    ]
    r.controle(
        "5. tous les slugs ASCII kebab-case prefixes numeriquement",
        not mauvais and not non_ascii,
        f"{len(mauvais)} slug(s) non conforme(s), {len(non_ascii)} non-ASCII"
        if (mauvais or non_ascii)
        else "98 slugs conformes",
    )

    # 6 -- derive entre la grille et le manifeste
    champs = (
        "id",
        "branche",
        "noeud",
        "chemin",
        "volet",
        "statut",
        "question_audit",
        "source_requise",
        "methode",
        "critere_verdict",
        "doublon_de",
    )
    ecarts = []
    par_id = {n["id"]: n for n in manifeste["noeuds"]}
    for n in donnees["noeuds"]:
        m = par_id.get(n["id"])
        if m is None:
            ecarts.append(f"noeud {n['id']} absent du manifeste")
            continue
        for k in champs:
            if n[k] != m[k]:
                ecarts.append(f"noeud {n['id']}, champ {k}")
    r.controle(
        "6. aucune derive entre grille-82-noeuds.md et manifest.json",
        not ecarts,
        f"{len(ecarts)} ecart(s)" if ecarts else "82 noeuds identiques sur 11 champs",
    )

    # 7 -- front-matter de chaque fiche
    invalides = []
    for n in manifeste["noeuds"]:
        fiche = SEO / n["chemin"] / "_fiche.md"
        if not fiche.exists():
            invalides.append(f"{n['chemin']} : fiche absente")
            continue
        try:
            fm = front_matter(fiche)
        except ValueError as e:
            invalides.append(f"{n['chemin']} : {e}")
            continue
        manquants = [c for c in CHAMPS_FICHE if c not in fm]
        if manquants:
            invalides.append(f"{n['chemin']} : champs manquants {manquants}")
        if fm.get("id") != str(n["id"]):
            invalides.append(f"{n['chemin']} : id incoherent")
        if fm.get("volet") != n["volet"]:
            invalides.append(f"{n['chemin']} : volet incoherent")
        if fm.get("etat") not in ETATS:
            invalides.append(f"{n['chemin']} : etat invalide {fm.get('etat')!r}")
    r.controle(
        "7. les 82 fiches ont un front-matter valide et coherent",
        not invalides,
        f"{len(invalides)} fiche(s) invalide(s)"
        if invalides
        else f"82 fiches, {len(CHAMPS_FICHE)} champs typés chacune",
    )
    for msg in invalides[:5]:
        print(f"          {msg}")

    # 8 -- miroir du gabarit de mission
    if TEMPLATE.exists():
        attendus = {n["chemin"] for n in manifeste["noeuds"]}
        analyse = TEMPLATE / "analyse"
        reels = {
            f"{b.name}/{f.name}"
            for b in analyse.iterdir()
            if b.is_dir()
            for f in b.iterdir()
            if f.is_dir()
        }
        sans_fiche = [c for c in attendus if not (analyse / c / "_fiche.md").exists()]
        structure_ok = (
            attendus == reels
            and not sans_fiche
            and (TEMPLATE / "cadrage.md").exists()
            and (TEMPLATE / "etat.json").exists()
            and all(
                (TEMPLATE / "donnees" / s).is_dir()
                for s in ("gsc", "ga", "crm", "logs", "crawl")
            )
            and (TEMPLATE / "livrables").is_dir()
        )
        r.controle(
            "8. missions/_TEMPLATE/analyse/ miroir exact des 98 dossiers",
            structure_ok,
            f"{len(reels)} dossiers de noeud, {len(attendus) - len(sans_fiche)} fiches",
        )
    else:
        r.controle("8. missions/_TEMPLATE/ present", False, "gabarit absent")

    # 9 -- aucun dossier vide non sentinelle
    vides = []
    for base in (SEO, RACINE / "missions"):
        for d in base.rglob("*"):
            if d.is_dir() and not any(d.iterdir()):
                vides.append(str(d.relative_to(RACINE)))
    r.controle(
        "9. aucun dossier sans fichier ni .gitkeep",
        not vides,
        f"{len(vides)} dossier(s) vide(s)" if vides else "arborescence survivra au clone",
    )

    print(f"\n{r.controles - len(r.echecs)}/{r.controles} controles passes")
    if r.echecs:
        print("ECHECS : " + ", ".join(r.echecs))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
