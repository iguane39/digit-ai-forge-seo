"""Validateur JSON Schema minimal — bibliotheque standard uniquement.

Ne couvre que ce que `referentiel/snapshot.schema.json` utilise reellement :
type, properties, required, additionalProperties, enum, const, items, minItems,
maxItems, minimum, maximum, $ref vers $defs, et les unions de types.

Un contrat de 773 lignes que rien n'applique n'est pas un contrat : une cle mal
orthographiee disparait du rapport sans un mot. C'est exactement le mode de
defaillance que ce projet combat ailleurs.

`format` est ignore volontairement : le valider demanderait des dependances, et une
date mal formee se voit a la lecture.

Python 3, bibliotheque standard uniquement.
"""

from __future__ import annotations

import json
from pathlib import Path

TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_ok(valeur, attendu) -> bool:
    noms = [attendu] if isinstance(attendu, str) else list(attendu)
    for n in noms:
        cible = TYPES.get(n)
        if cible is None:
            continue
        # bool est un int en Python : sans ce garde-fou, True passerait pour un entier.
        if n in ("integer", "number") and isinstance(valeur, bool):
            continue
        if n == "boolean" and not isinstance(valeur, bool):
            continue
        if isinstance(valeur, cible):
            return True
    return False


def _resoudre(schema: dict, racine: dict) -> dict:
    ref = schema.get("$ref")
    if not ref:
        return schema
    noeud = racine
    for part in ref.lstrip("#/").split("/"):
        noeud = noeud.get(part, {})
    return noeud


def valider(donnees, schema: dict, racine: dict | None = None,
            chemin: str = "$") -> list[str]:
    """Retourne la liste des ecarts. Liste vide = conforme."""
    racine = racine if racine is not None else schema
    schema = _resoudre(schema, racine)
    err: list[str] = []

    if "const" in schema and donnees != schema["const"]:
        err.append(f"{chemin} : attendu {schema['const']!r}, reçu {donnees!r}")
        return err

    if "enum" in schema and donnees not in schema["enum"]:
        err.append(f"{chemin} : {donnees!r} hors des valeurs admises {schema['enum']}")
        return err

    if "type" in schema and not _type_ok(donnees, schema["type"]):
        err.append(f"{chemin} : type {type(donnees).__name__}, attendu {schema['type']}")
        return err

    if isinstance(donnees, dict):
        props = schema.get("properties", {})
        for cle in schema.get("required", []):
            if cle not in donnees:
                err.append(f"{chemin}.{cle} : champ requis absent")
        if schema.get("additionalProperties") is False:
            for cle in donnees:
                if cle not in props:
                    err.append(f"{chemin}.{cle} : champ inconnu du schéma")
        for cle, val in donnees.items():
            if cle in props:
                err += valider(val, props[cle], racine, f"{chemin}.{cle}")

    elif isinstance(donnees, list):
        if "minItems" in schema and len(donnees) < schema["minItems"]:
            err.append(f"{chemin} : {len(donnees)} éléments, minimum {schema['minItems']}")
        if "maxItems" in schema and len(donnees) > schema["maxItems"]:
            err.append(f"{chemin} : {len(donnees)} éléments, maximum {schema['maxItems']}")
        if "items" in schema:
            for i, item in enumerate(donnees):
                err += valider(item, schema["items"], racine, f"{chemin}[{i}]")

    elif isinstance(donnees, (int, float)) and not isinstance(donnees, bool):
        if "minimum" in schema and donnees < schema["minimum"]:
            err.append(f"{chemin} : {donnees} < minimum {schema['minimum']}")
        if "maximum" in schema and donnees > schema["maximum"]:
            err.append(f"{chemin} : {donnees} > maximum {schema['maximum']}")

    return err


def valider_fichier(donnees_path: Path, schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    donnees = json.loads(donnees_path.read_text(encoding="utf-8"))
    return valider(donnees, schema)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("usage : python scripts/schema.py <donnees.json> <schema.json>")
        raise SystemExit(2)
    ecarts = valider_fichier(Path(sys.argv[1]), Path(sys.argv[2]))
    if not ecarts:
        print("conforme")
        raise SystemExit(0)
    print(f"{len(ecarts)} écart(s) :")
    for e in ecarts[:30]:
        print(f"  {e}")
    raise SystemExit(1)
