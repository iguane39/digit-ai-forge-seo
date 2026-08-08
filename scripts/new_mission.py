"""Instancie une mission a partir du gabarit.

Copie missions/_TEMPLATE/ vers missions/<client>/ et initialise etat.json.

REFUS D'ECRASEMENT : si la mission existe deja, le script s'arrete. Ecraser une
mission en cours detruirait du travail sans trace -- c'est le seul mode d'echec
de ce projet dont on ne se remet pas. Aucun --force n'est prevu ici : pour
repartir de zero, supprimer explicitement le dossier a la main.

Usage :
    python scripts/new_mission.py --client "Nom Client" --domaine exemple.fr
    python scripts/new_mission.py --client "Nom Client" --domaine exemple.fr --liste

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

from grille import RACINE, slugify

MISSIONS = RACINE / "missions"
TEMPLATE = MISSIONS / "_TEMPLATE"


def lister() -> int:
    if not MISSIONS.exists():
        print("aucune mission (missions/ absent)")
        return 0
    trouvees = [
        d for d in sorted(MISSIONS.iterdir()) if d.is_dir() and d.name != "_TEMPLATE"
    ]
    if not trouvees:
        print("aucune mission instanciee")
        return 0
    print(f"{len(trouvees)} mission(s) :")
    for d in trouvees:
        etat_f = d / "etat.json"
        if etat_f.exists():
            e = json.loads(etat_f.read_text(encoding="utf-8"))
            n = e.get("noeuds", {})
            print(
                f"  {d.name:<28} {e.get('domaine') or '?':<24} "
                f"etape {e.get('etape_courante')} -- "
                f"{n.get('fait', 0)} fait / {n.get('hors_perimetre', 0)} hors perimetre "
                f"/ {n.get('total', 0)} noeuds"
            )
        else:
            print(f"  {d.name:<28} (etat.json absent)")
    return 0


def creer(client: str, domaine: str) -> int:
    if not TEMPLATE.exists():
        print("gabarit absent. Lancer d'abord : python scripts/scaffold.py")
        return 1

    slug = slugify(client)
    cible = MISSIONS / slug

    if cible.exists():
        print(f"REFUS : missions/{slug}/ existe deja.")
        print("Une mission ne s'ecrase pas. Pour repartir de zero, supprimer le")
        print("dossier a la main apres avoir verifie ce qu'il contient.")
        return 1

    shutil.copytree(TEMPLATE, cible)

    etat_f = cible / "etat.json"
    etat = json.loads(etat_f.read_text(encoding="utf-8"))
    etat["client"] = client
    etat["domaine"] = domaine
    etat["date_creation"] = dt.date.today().isoformat()

    anterieurs = sorted(
        p.name
        for d in MISSIONS.iterdir()
        if d.is_dir() and d.name not in ("_TEMPLATE", slug)
        for p in (d / "livrables").glob("snapshot-*.json")
    )
    etat["snapshot_precedent"] = anterieurs[-1] if anterieurs else None

    etat_f.write_text(
        json.dumps(etat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    readme = cible / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("<client>", client),
        encoding="utf-8",
    )

    noeuds = sum(
        1
        for b in (cible / "analyse").iterdir()
        if b.is_dir()
        for f in b.iterdir()
        if f.is_dir()
    )

    print(f"mission creee : missions/{slug}/")
    print(f"  client   : {client}")
    print(f"  domaine  : {domaine}")
    print(f"  noeuds   : {noeuds}")
    print("")
    print("Etapes suivantes :")
    print(f"  1. remplir missions/{slug}/cadrage.md (champs OBLIGATOIRE)")
    print(f"  2. deposer les exports dans missions/{slug}/donnees/{{gsc,ga,crm,logs}}/")
    print("  3. lancer le skill seo-audit-strategie sur cette mission")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Instancie une mission forge-seo.")
    p.add_argument("--client", help="nom du client (sert de nom de dossier, slugifie)")
    p.add_argument("--domaine", help="domaine audite, sans protocole")
    p.add_argument("--liste", action="store_true", help="liste les missions existantes")
    args = p.parse_args()

    if args.liste:
        return lister()
    if not args.client or not args.domaine:
        p.error("--client et --domaine sont requis (ou utiliser --liste)")
    return creer(args.client, args.domaine)


if __name__ == "__main__":
    sys.exit(main())
