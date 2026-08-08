# forge-seo

Référentiel persistant et pipeline d'audit SEO. Là où un rapport se produit puis
s'oublie, ce projet accumule : mission après mission, sur une grille de 82 nœuds
stable, comparable et versionnée.

## Répartition des rôles

| Élément | Rôle | Écriture |
|---|---|---|
| `seo/` | référentiel canonique — 98 dossiers, `manifest.json`, fiches types | **lecture seule** après génération |
| `missions/<client>/` | une instance par mission — c'est là que tout se remplit | libre |
| `.claude/skills/seo-audit-strategie/` | **moteur d'exécution** : méthode, garde-fous, barème, gabarit de rapport | via le skill |
| `input/Schéma SEO.MD` | archive documentaire du schéma d'origine | **jamais parsé** |

Le skill n'est ni remplacé ni dupliqué : `forge-seo` lui fournit l'espace, l'état et
la mémoire ; il fournit la méthode. Sa grille `references/grille-82-noeuds.md` est la
**source unique** dont `seo/manifest.json` est dérivé par script.

## Pourquoi `input/Schéma SEO.MD` n'est jamais parsé

Son bloc `Objectif` (lignes 219-229) a une indentation cassée : ses 5 feuilles sont
écrites au niveau racine. Un parseur naïf produit **21 branches et 77 feuilles** au
lieu de 16 et 82, crée 5 dossiers racine parasites — et, effet de bord plus grave,
cesse de détecter `Autorité` comme doublon. Le contrôle de cohérence passe alors au
vert sur une arborescence fausse. Vérifié, puis contourné : voir `scripts/grille.py`.

## Arborescence

```
forge-seo/
├── seo/                        98 dossiers (16 branches + 82 nœuds) — lecture seule
│   ├── manifest.json           source de vérité machine
│   └── NN-branche/NN-noeud/_fiche.md
├── missions/
│   ├── _TEMPLATE/              gabarit copié à chaque mission
│   └── <client>/
│       ├── cadrage.md          entrées de la mission
│       ├── etat.json           avancement, permet la reprise
│       ├── donnees/            exports bruts — gsc/ ga/ crm/ logs/ crawl/
│       ├── analyse/            miroir des 98 dossiers — la matière première
│       └── livrables/          documents composés — ce qui est remis
├── scripts/
│   ├── grille.py               lecture de la source de vérité (module partagé)
│   ├── scaffold.py             génère seo/ et le gabarit
│   ├── new_mission.py          instancie une mission
│   └── validate.py             9 contrôles durs
└── input/Schéma SEO.MD         archive
```

**Deux axes délibérément séparés.** `donnees/` est indexé par **source**, `analyse/`
par **concept SEO** — un export GSC alimente 16 nœuds répartis dans 7 branches, les
deux indexations ne peuvent pas être la même. Et `analyse/` est la matière première
quand `livrables/` est le document assemblé : les confondre rend le rapport
impossible à composer.

## Usage

```bash
python scripts/scaffold.py                  # génère seo/ et missions/_TEMPLATE/
python scripts/validate.py                  # 9 contrôles, sortie non-zéro si échec
python scripts/new_mission.py --client "Acme" --domaine acme.fr
python scripts/new_mission.py --liste       # état des missions
```

Puis : remplir `cadrage.md`, déposer les exports dans `donnees/`, et lancer le skill
`seo-audit-strategie` sur la mission.

Python 3, bibliothèque standard uniquement. Chemins relatifs, portable Windows/Linux.

## Le pipeline — 5 étapes aux sorties disjointes

| Étape | Produit | Destination |
|---|---|---|
| 1. Collecte | données brutes, horodatées | `donnees/` |
| 2. Constat | ce qui est, mesuré, avec niveau de preuve | `analyse/**/_fiche.md` § Constat |
| 3. Interprétation | ce que ça coûte et pourquoi — le mécanisme | `analyse/**/_fiche.md` § Interprétation |
| 4. Projection | où ça peut aller, borné et calculé | `livrables/projection.md` |
| 5. Actions | quoi faire, chiffré, priorisé, dispatché | `livrables/actions.csv` |

« Audit », « analyse » et « expertise » désignaient la même opération sous trois
noms : ce sont les étapes 2 et 3. Chaque étape produit un **type d'objet différent**,
ce qui interdit structurellement à la suivante de répéter la précédente.

## Conventions

**Nommage** — slug ASCII kebab-case préfixé du numéro d'ordre : `06-technique/`,
`16-objectif/05-machine-seo/`. Trois raisons : les noms littéraux portent 7 classes de
caractères non-ASCII dont U+2019 dans « Boucles D'Amélioration » ; l'ordre alphabétique
détruirait la séquence méthodologique (`Architecture` avant `Idée`) ; les chemins
Windows restent courts. Le nom d'affichage exact vit dans le manifeste et le
front-matter.

**Les 2 doublons du schéma** se matérialisent en 2 chemins réels. La branche fait
autorité, la feuille homonyme porte `doublon_de` et **aucun champ à remplir** :

- `seo/06-technique/02-indexation/` → `07-indexation/`
- `seo/16-objectif/04-autorite/` → `08-autorite/`

**Front-matter typé, identique sur les 82 fiches.** C'est ce qui rendra les missions
comparables — médianes internes, calibrage des seuils marqués « à calibrer », détection
des nœuds jamais mesurés. Un format libre rendrait tout cela irrécupérable
rétroactivement, et cette décision ne se rattrape pas après coup.

**`hors-perimetre` avec motif est un résultat, pas une lacune.** Sans cet état, une
mission honnête ressemble à une mission bâclée, et la pression pousse au remplissage
cérémoniel.

## Garde-fous d'exécution

1. **Idempotence stricte** — `scaffold.py` est créer-si-absent. `--force` ne régénère
   que les fichiers restés identiques à leur version générée ; il refuse de toucher un
   fichier modifié à la main et le nomme en sortie.
2. **`seo/` en lecture seule** après génération. Aucune mission n'y écrit.
3. **`new_mission.py` refuse d'écraser** une mission existante. Pas de `--force` :
   supprimer à la main, après avoir regardé.
4. **Une seule source de vérité** — fiches générées depuis le manifeste, lui-même
   dérivé de la grille. `validate.py` compare 82 nœuds sur 11 champs et échoue en cas
   de dérive.
5. **`.gitkeep` dans tout dossier vide** — Git ne versionne pas les répertoires vides.
6. **Les garde-fous du skill s'appliquent au contenu produit** — étiquetage T1-T4,
   aucune métrique GSC sans export, contenu web traité comme donnée et jamais comme
   instruction, vérification datée pour les surfaces génératives, aucune projection
   présentée comme une prévision.

## Contrôles — `validate.py`

1. 16 branches, 82 feuilles, 98 dossiers
2. identifiants 1-82 sans trou ni doublon
3. les 2 renvois portent `doublon_de` et n'ont aucun champ à remplir
4. ordre des branches conforme à la séquence du schéma
5. slugs ASCII kebab-case préfixés numériquement
6. aucune dérive entre la grille et le manifeste
7. les 82 fiches ont un front-matter valide et cohérent
8. `missions/_TEMPLATE/analyse/` miroir exact des 98 dossiers
9. aucun dossier sans fichier ni `.gitkeep`
