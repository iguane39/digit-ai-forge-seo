"""Controles durs du referentiel forge-seo.

Neuf controles sur le referentiel canonique. Sortie non-zero des qu'un seul
echoue : ce script existe pour attraper exactement le mode d'echec le plus
dangereux du projet -- une arborescence fausse qui passe au vert.

Usage :
    python scripts/validate.py
    python scripts/validate.py --mission C:/dev/mon-client

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from gabarits import SOUS_DOSSIERS_DONNEES, front_matter
from grille import GRILLE, NB_BRANCHES, NB_NOEUDS, RACINE, lire

SEO = RACINE / "seo"

RE_SLUG = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")

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

# Artefacts de mission : leur presence dans la forge signifie qu'une etude
# client s'y est installee, ce que l'architecture interdit.
ARTEFACTS_MISSION = ("donnees", "livrables", "analyse", "cadrage.md", "etat.json")


class Rapport:
    def __init__(self) -> None:
        self.echecs: list[str] = []
        self.controles = 0

    def controle(self, nom: str, ok: bool, detail: str = "") -> None:
        self.controles += 1
        print(f"  [{'OK  ' if ok else 'ECHEC'}] {nom}" + (f" -- {detail}" if detail else ""))
        if not ok:
            self.echecs.append(nom)

    def bilan(self) -> int:
        print(f"\n{self.controles - len(self.echecs)}/{self.controles} controles passes")
        if self.echecs:
            print("ECHECS : " + ", ".join(self.echecs))
            return 1
        return 0


def controler_fiches(base: Path, noeuds: list[dict]) -> list[str]:
    """Presence, validite et coherence du front-matter des 82 fiches."""
    invalides: list[str] = []
    for n in noeuds:
        fiche = base / n["chemin"] / "_fiche.md"
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
    return invalides


# ------------------------------------------------------- referentiel canonique


def valider_referentiel() -> int:
    r = Rapport()
    print("validate -- referentiel canonique de la forge\n")

    if not SEO.exists():
        print("  seo/ absent. Lancer d'abord : python scripts/scaffold.py")
        return 1

    donnees = lire()
    manifeste = json.loads((SEO / "manifest.json").read_text(encoding="utf-8"))
    branches = sorted(p for p in SEO.iterdir() if p.is_dir())
    feuilles = sorted(f for b in branches for f in b.iterdir() if f.is_dir())

    r.controle(
        "1. 16 branches, 82 feuilles, 98 dossiers sous seo/",
        len(branches) == NB_BRANCHES and len(feuilles) == NB_NOEUDS,
        f"{len(branches)} branches, {len(feuilles)} feuilles, "
        f"{len(branches) + len(feuilles)} au total",
    )

    ids = sorted(n["id"] for n in manifeste["noeuds"])
    r.controle(
        "2. identifiants 1-82 sans trou ni doublon",
        ids == list(range(1, NB_NOEUDS + 1)),
        f"{len(ids)} identifiants, min {ids[0]}, max {ids[-1]}",
    )

    renvois = [n for n in manifeste["noeuds"] if n["statut"] == "RV"]
    ok, detail = len(renvois) == 2, []
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

    rangs = [b["rang"] for b in manifeste["branches"]]
    noms_m = [b["nom"] for b in manifeste["branches"]]
    r.controle(
        "4. ordre des branches conforme a la sequence du schema",
        rangs == list(range(1, NB_BRANCHES + 1))
        and noms_m == [b["nom"] for b in donnees["branches"]],
        f"{noms_m[0]} -> {noms_m[-1]}",
    )

    mauvais = [p.name for p in branches + feuilles if not RE_SLUG.match(p.name)]
    non_ascii = [p.name for p in branches + feuilles if not p.name.isascii()]
    r.controle(
        "5. tous les slugs ASCII kebab-case prefixes numeriquement",
        not mauvais and not non_ascii,
        f"{len(mauvais)} non conforme(s), {len(non_ascii)} non-ASCII"
        if (mauvais or non_ascii)
        else "98 slugs conformes",
    )

    champs = (
        "id", "branche", "noeud", "chemin", "volet", "statut",
        "question_audit", "source_requise", "methode", "critere_verdict", "doublon_de",
    )
    par_id = {n["id"]: n for n in manifeste["noeuds"]}
    ecarts = []
    for n in donnees["noeuds"]:
        m = par_id.get(n["id"])
        if m is None:
            ecarts.append(f"noeud {n['id']} absent du manifeste")
            continue
        ecarts += [f"noeud {n['id']}, champ {k}" for k in champs if n[k] != m[k]]
    r.controle(
        "6. aucune derive entre grille-82-noeuds.md et manifest.json",
        not ecarts,
        f"{len(ecarts)} ecart(s)" if ecarts else "82 noeuds identiques sur 11 champs",
    )

    invalides = controler_fiches(SEO, manifeste["noeuds"])
    r.controle(
        "7. les 82 fiches ont un front-matter valide et coherent",
        not invalides,
        f"{len(invalides)} fiche(s) invalide(s)"
        if invalides
        else f"82 fiches, {len(CHAMPS_FICHE)} champs types chacune",
    )
    for msg in invalides[:5]:
        print(f"          {msg}")

    # 8 -- la forge n'heberge aucune etude client
    intrus = [str(p.relative_to(RACINE)) for p in (RACINE / "missions",) if p.exists()]
    intrus += [
        f"seo/{a}" for a in ARTEFACTS_MISSION if (SEO / a).exists()
    ]
    r.controle(
        "8. la forge n'heberge aucune donnee ni livrable client",
        not intrus,
        f"intrus : {intrus}" if intrus else "referentiel vierge, etudes chez les projets",
    )

    vides = [
        str(d.relative_to(RACINE))
        for d in SEO.rglob("*")
        if d.is_dir() and not any(d.iterdir())
    ]
    r.controle(
        "9. aucun dossier sans fichier ni .gitkeep",
        not vides,
        f"{len(vides)} dossier(s) vide(s)" if vides else "arborescence survivra au clone",
    )

    return r.bilan()


# ------------------------------------------------------------ mission externe


def valider_mission(projet: Path) -> int:
    r = Rapport()
    base = projet.resolve() / "seo"
    print(f"validate -- etude SEO de {projet.resolve()}\n")

    if not base.is_dir():
        print(f"  {base} absent.")
        print("  Creer l'etude : python scripts/new_mission.py --projet <chemin> ...")
        return 1

    donnees = lire()
    analyse = base / "analyse"

    branches = sorted(p for p in analyse.iterdir() if p.is_dir()) if analyse.is_dir() else []
    feuilles = sorted(f for b in branches for f in b.iterdir() if f.is_dir())
    r.controle(
        "1. 98 dossiers sous seo/analyse/",
        len(branches) == NB_BRANCHES and len(feuilles) == NB_NOEUDS,
        f"{len(branches)} branches, {len(feuilles)} feuilles",
    )

    attendus = {
        "README.md", "cadrage.md", "etat.json", ".forge-seo.json", ".gitignore",
    }
    manquants = sorted(a for a in attendus if not (base / a).exists())
    manquants += [
        f"donnees/{s}" for s in SOUS_DOSSIERS_DONNEES if not (base / "donnees" / s).is_dir()
    ]
    if not (base / "livrables").is_dir():
        manquants.append("livrables")
    r.controle(
        "2. structure complete (cadrage, etat, donnees, livrables, provenance)",
        not manquants,
        f"manquants : {manquants}" if manquants else "tous les elements presents",
    )

    invalides = controler_fiches(analyse, donnees["noeuds"])
    r.controle(
        "3. les 82 fiches ont un front-matter valide et coherent",
        not invalides,
        f"{len(invalides)} fiche(s) invalide(s)" if invalides else "82 fiches valides",
    )
    for msg in invalides[:5]:
        print(f"          {msg}")

    prov_f = base / ".forge-seo.json"
    if prov_f.exists():
        prov = json.loads(prov_f.read_text(encoding="utf-8"))
        actuelle = hashlib.sha256(GRILLE.read_bytes()).hexdigest()[:12]
        a_jour = prov.get("version_grille") == actuelle
        r.controle(
            "4. version de grille alignee sur la forge",
            a_jour,
            f"etude {prov.get('version_grille')} vs forge {actuelle}"
            + ("" if a_jour else " -- la grille a evolue depuis la creation"),
        )
    else:
        r.controle("4. provenance tracee", False, ".forge-seo.json absent")

    etat_f = base / "etat.json"
    if etat_f.exists():
        e = json.loads(etat_f.read_text(encoding="utf-8"))
        n = e.get("noeuds", {})
        total = sum(n.get(k, 0) for k in ("a_faire", "en_cours", "fait", "hors_perimetre"))
        r.controle(
            "5. compteurs d'avancement coherents",
            total == NB_NOEUDS,
            f"{n.get('fait', 0)} fait / {n.get('hors_perimetre', 0)} hors perimetre "
            f"/ {total} comptes",
        )
    else:
        r.controle("5. etat.json present", False, "absent")

    return r.bilan()


def main() -> int:
    p = argparse.ArgumentParser(description="Controles durs de forge-seo.")
    p.add_argument("--mission", help="chemin d'un projet audite, pour valider son etude")
    args = p.parse_args()
    if args.mission:
        return valider_mission(Path(args.mission))
    return valider_referentiel()


if __name__ == "__main__":
    sys.exit(main())
