"""Deploie le declencheur dans ~/.claude/skills/, ou verifie son etat.

Le skill `seo-audit-strategie` vit ici, dans la forge, sous version. Mais un skill
range dans `<projet>/.claude/skills/` n'est decouvert que depuis ce projet : tant
qu'il reste ici, il ne se declenche que lorsqu'on travaille DANS la forge -- soit
exactement quand on n'en a pas besoin.

Pour qu'une demande d'audit SEO lancee depuis un projet client active la methode, le
fichier doit etre copie dans `~/.claude/skills/`. Ce script fait cette copie, et
detecte la derive entre la version de la forge et la version installee.

La forge reste la source : on ne modifie jamais la copie installee a la main.

Usage :
    python scripts/installer_skill.py --verifier    # etat, sans rien ecrire
    python scripts/installer_skill.py               # installe ou met a jour

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

from grille import RACINE

NOM = "seo-audit-strategie"
SOURCE = RACINE / ".claude" / "skills" / NOM / "SKILL.md"
CIBLE = Path.home() / ".claude" / "skills" / NOM / "SKILL.md"


def empreinte(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def etat() -> tuple[str, str]:
    """Retourne (statut, detail)."""
    if not SOURCE.exists():
        return "absent-source", f"{SOURCE} introuvable"
    if not CIBLE.exists():
        return "non-installe", "le declencheur ne s'activera pas hors de la forge"
    a, b = empreinte(SOURCE), empreinte(CIBLE)
    if a == b:
        return "a-jour", f"empreinte {a}"
    return "derive", f"forge {a} != installe {b}"


def main() -> int:
    p = argparse.ArgumentParser(description="Deploie le declencheur SEO.")
    p.add_argument("--verifier", action="store_true", help="etat seul, aucune ecriture")
    args = p.parse_args()

    statut, detail = etat()
    print(f"source  : {SOURCE}")
    print(f"cible   : {CIBLE}")
    print(f"statut  : {statut} — {detail}")

    if statut == "absent-source":
        return 1
    if args.verifier:
        return 0 if statut == "a-jour" else 1
    if statut == "a-jour":
        print("\nrien a faire.")
        return 0

    CIBLE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, CIBLE)
    print(f"\ninstalle — empreinte {empreinte(CIBLE)}")
    print("Le skill se declenchera desormais depuis n'importe quel projet.")
    print("La forge reste la source : ne pas editer la copie installee.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
