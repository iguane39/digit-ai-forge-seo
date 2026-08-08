"""Lecture de la source de verite de forge-seo.

SOURCE DE VERITE : .claude/skills/seo-audit-strategie/references/grille-82-noeuds.md

Le fichier input/Schema SEO.MD n'est JAMAIS parse par aucun script de ce projet.
Motif verifie : son bloc `Objectif` (lignes 219-229) a une indentation cassee -- ses
5 feuilles sont ecrites au niveau racine, sans le prefixe de profondeur utilise
partout ailleurs. Un parseur naif produit donc :

    branches: 21   (attendu 16)
    feuilles: 77   (attendu 82)

soit 5 dossiers racine parasites (Trafic Qualifie, Leads Entrants, Ventes,
Autorite, Machine SEO) au lieu de les ranger sous Objectif/. Effet de bord plus
grave : `Autorite`, promu branche par erreur, cesse d'etre detecte comme doublon
de la vraie branche `Autorite` -- le controle de coherence passe au vert sur une
arborescence fausse.

Ce module est partage par scaffold.py et validate.py : c'est ce qui garantit
qu'il n'existe qu'une seule lecture de la grille, donc pas de derive.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------- constantes

RACINE = Path(__file__).resolve().parent.parent

GRILLE = (
    RACINE
    / ".claude"
    / "skills"
    / "seo-audit-strategie"
    / "references"
    / "grille-82-noeuds.md"
)

NB_BRANCHES = 16
NB_NOEUDS = 82

STATUTS = {"SD", "EX", "PY", "NM", "RV", "CA"}

# Enum ASCII, aligne sur assets/snapshot.schema.json du skill.
# Deux conventions divergentes pour un meme champ seraient exactement la derive
# que ce projet cherche a rendre impossible.
VOLETS = {
    "ÉTAT": "ETAT",
    "STRATÉGIE": "STRATEGIE",
    "TRANSVERSAL": "TRANSVERSAL",
    "CADRAGE": "CADRAGE",
}

RE_SECTION = re.compile(r"^##\s+(\d{1,2})\.\s+(.+?)\s*(?:—|--).*$")
RE_LIGNE = re.compile(r"^\|\s*(\d{1,2})\s*\|")
RE_CODE = re.compile(r"`([A-Z]{2})`")


class ErreurGrille(RuntimeError):
    """La grille ne se lit pas comme attendu. On echoue fort, jamais en silence."""


# ------------------------------------------------------------------ utilitaires


def slugify(texte: str) -> str:
    """Nom de dossier ASCII kebab-case.

    Les noms litteraux du schema portent 7 classes de caracteres non-ASCII, dont
    U+2019 (apostrophe typographique) dans "Boucles D'Amelioration". Les garder
    dans un chemin, c'est un piege durable pour tout script shell et une source
    de divergence NFC/NFD entre systemes de fichiers.
    """
    texte = texte.replace("’", " ").replace("'", " ")
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = re.sub(r"[^A-Za-z0-9]+", "-", texte).strip("-").lower()
    if not texte:
        raise ErreurGrille(f"slug vide pour {texte!r}")
    return texte


def _cellules(ligne: str) -> list[str]:
    return [c.strip() for c in ligne.strip().strip("|").split("|")]


def _statut(cellule: str) -> str:
    """Premier code a deux lettres de la cellule statut.

    Les cellules portent souvent une degradation : "`PY` -- degradation `SD` : ..."
    Le statut retenu est le premier code, jamais celui de la degradation.
    """
    for code in RE_CODE.findall(cellule):
        if code in STATUTS:
            return code
    raise ErreurGrille(f"aucun statut lisible dans {cellule!r}")


def _volet(cellule: str) -> str:
    if cellule not in VOLETS:
        raise ErreurGrille(f"volet inconnu : {cellule!r}")
    return VOLETS[cellule]


# --------------------------------------------------------------------- lecture


def lire(chemin: Path | None = None) -> dict:
    """Retourne {'branches': [...], 'noeuds': [...]} depuis la grille.

    Echoue si les comptes ne sont pas exactement 16 branches et 82 noeuds :
    c'est le controle qui aurait attrape le defaut du fichier .MD d'origine.
    """
    chemin = chemin or GRILLE
    if not chemin.exists():
        raise ErreurGrille(f"grille introuvable : {chemin}")

    texte = chemin.read_text(encoding="utf-8")

    branches: list[dict] = []
    noeuds: list[dict] = []
    courante: dict | None = None

    for ligne in texte.split("\n"):
        section = RE_SECTION.match(ligne)
        if section:
            rang = int(section.group(1))
            nom = section.group(2).strip()
            courante = {
                "rang": rang,
                "nom": nom,
                "slug": f"{rang:02d}-{slugify(nom)}",
                "noeuds": [],
            }
            branches.append(courante)
            continue

        if not RE_LIGNE.match(ligne) or courante is None:
            continue

        cells = _cellules(ligne)
        if len(cells) != 8:
            raise ErreurGrille(
                f"ligne a {len(cells)} cellules au lieu de 8 : {ligne[:80]!r}"
            )

        identifiant = int(cells[0])
        nom = cells[1]
        rang_local = len(courante["noeuds"]) + 1

        noeud = {
            "id": identifiant,
            "branche": courante["nom"],
            "slug_branche": courante["slug"],
            "noeud": nom,
            "slug_noeud": f"{rang_local:02d}-{slugify(nom)}",
            "volet": _volet(cells[2]),
            "statut": _statut(cells[7]),
            "question_audit": cells[3],
            "source_requise": cells[4],
            "methode": cells[5],
            "critere_verdict": cells[6],
            "doublon_de": None,
        }
        noeud["chemin"] = f"{courante['slug']}/{noeud['slug_noeud']}"
        courante["noeuds"].append(noeud)
        noeuds.append(noeud)

    _resoudre_doublons(branches, noeuds)
    _controler(branches, noeuds)

    for b in branches:
        b["volet_dominant"] = _volet_dominant(b["noeuds"])

    return {"branches": branches, "noeuds": noeuds}


def _resoudre_doublons(branches: list[dict], noeuds: list[dict]) -> None:
    """Un noeud en statut RV renvoie vers la branche homonyme, qui fait autorite."""
    par_nom = {b["nom"]: b for b in branches}
    for n in noeuds:
        if n["statut"] != "RV":
            continue
        cible = par_nom.get(n["noeud"])
        if cible is None:
            raise ErreurGrille(
                f"noeud {n['id']} en renvoi mais aucune branche nommee {n['noeud']!r}"
            )
        n["doublon_de"] = cible["slug"]


def _volet_dominant(noeuds: list[dict]) -> str:
    compte: dict[str, int] = {}
    for n in noeuds:
        compte[n["volet"]] = compte.get(n["volet"], 0) + 1
    return max(compte.items(), key=lambda kv: (kv[1], kv[0]))[0]


def _controler(branches: list[dict], noeuds: list[dict]) -> None:
    if len(branches) != NB_BRANCHES:
        raise ErreurGrille(f"{len(branches)} branches lues, {NB_BRANCHES} attendues")
    if len(noeuds) != NB_NOEUDS:
        raise ErreurGrille(f"{len(noeuds)} noeuds lus, {NB_NOEUDS} attendus")

    ids = [n["id"] for n in noeuds]
    if ids != list(range(1, NB_NOEUDS + 1)):
        manquants = sorted(set(range(1, NB_NOEUDS + 1)) - set(ids))
        doublons = sorted({i for i in ids if ids.count(i) > 1})
        raise ErreurGrille(
            f"identifiants non contigus 1-{NB_NOEUDS} "
            f"(manquants={manquants}, doublons={doublons})"
        )

    rangs = [b["rang"] for b in branches]
    if rangs != list(range(1, NB_BRANCHES + 1)):
        raise ErreurGrille(f"ordre des branches rompu : {rangs}")

    chemins = [n["chemin"] for n in noeuds]
    if len(set(chemins)) != len(chemins):
        raise ErreurGrille("collision de chemin entre deux noeuds")


if __name__ == "__main__":
    donnees = lire()
    print(f"branches : {len(donnees['branches'])}")
    print(f"noeuds   : {len(donnees['noeuds'])}")
    print(f"dossiers : {len(donnees['branches']) + len(donnees['noeuds'])}")
    for n in donnees["noeuds"]:
        if n["doublon_de"]:
            print(f"renvoi   : {n['id']:>2} {n['chemin']} -> {n['doublon_de']}")
