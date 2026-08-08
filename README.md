# forge-seo

Outil d'audit et de stratégie SEO. La forge fournit **la méthode et le référentiel** ;
chaque projet audité reçoit **son étude chez lui**, dans son propre dossier `seo/`.

Là où un rapport se produit puis s'oublie, ce dispositif accumule : mission après
mission, sur une grille de 87 nœuds stable, comparable et versionnée.

## Où vit quoi

| Élément | Rôle | Emplacement |
|---|---|---|
| `seo/` | référentiel canonique — 104 dossiers, `manifest.json`, fiches vierges | **dans la forge**, lecture seule |
| `scripts/` | générateurs et contrôles | dans la forge |
| `.claude/skills/seo-audit-strategie/` | moteur d'exécution : méthode, garde-fous, barème, gabarit de rapport | dans la forge |
| `<projet>/seo/` | **l'étude** — cadrage, données, analyse, livrables | **dans le projet audité** |

**La forge n'héberge aucune donnée ni livrable client.** C'est un invariant, pas une
convention : `validate.py` échoue si une étude s'y installe, et `new_mission.py`
refuse de viser la forge ou un dossier qui la contient.

## Le dossier `seo/` d'un projet audité

```
<projet>/seo/
├── README.md            mode d'emploi de l'espace
├── cadrage.md           entrées de la mission
├── etat.json            avancement — permet la reprise
├── .forge-seo.json      provenance : version de la grille, date
├── .gitignore           garde-fou de confidentialité
├── donnees/             exports bruts — gsc/ ga/ crm/ logs/ crawl/
├── analyse/             104 dossiers, 87 fiches hydratées
└── livrables/           audit, roadmap, actions.csv, snapshot, dette
```

**Deux axes délibérément séparés.** `donnees/` est indexé par **source**, `analyse/`
par **concept SEO** — un export GSC alimente 16 nœuds répartis dans 7 branches, les
deux indexations ne peuvent pas être la même. Et `analyse/` est la matière première
quand `livrables/` est le document assemblé : les confondre rend le rapport
impossible à composer.

`.forge-seo.json` porte l'empreinte de la grille utilisée. Si la forge évolue,
`validate.py --mission` signale que l'étude a été produite sur une version antérieure.

## Usage

```bash
# Dans la forge — une fois, puis à chaque évolution de la grille
python scripts/scaffold.py                  # génère le référentiel seo/
python scripts/validate.py                  # 9 contrôles, exit non-zéro si échec

# Pour un projet à auditer
python scripts/new_mission.py --projet C:/dev/mon-client --client "Acme" --domaine acme.fr
python scripts/validate.py --mission C:/dev/mon-client
python scripts/new_mission.py --liste       # registre local des études créées
```

Puis, **dans le projet audité** : remplir `seo/cadrage.md`, déposer les exports dans
`seo/donnees/`, et lancer le skill `seo-audit-strategie`.

Python 3, bibliothèque standard uniquement. Chemins relatifs, portable Windows/Linux.

`missions.json` est un registre local — client, domaine, chemin, date, version de
grille. Aucune donnée client. Il n'est pas versionné.

## Pourquoi `input/Schéma SEO.MD` n'est jamais parsé

Son bloc `Objectif` (lignes 219-229) a une indentation cassée : ses 5 feuilles sont
écrites au niveau racine. Un parseur naïf produit **21 branches et 77 feuilles** au
lieu de 16 et 82, crée 5 dossiers racine parasites — et, effet de bord plus grave,
cesse de détecter `Autorité` comme doublon. Le contrôle de cohérence passe alors au
vert sur une arborescence fausse. Vérifié, puis contourné : la source de vérité est
`references/grille-noeuds.md` du skill. Voir `scripts/grille.py`.

## Le pipeline — 5 étapes aux sorties disjointes

| Étape | Produit | Destination |
|---|---|---|
| 1. Collecte | données brutes, horodatées | `seo/donnees/` |
| 2. Constat | ce qui est, mesuré, avec niveau de preuve | `seo/analyse/**/_fiche.md` § Constat |
| 3. Interprétation | ce que ça coûte et pourquoi — le mécanisme | `seo/analyse/**/_fiche.md` § Interprétation |
| 4. Projection | où ça peut aller, borné et calculé | `seo/livrables/` |
| 5. Actions | quoi faire, chiffré, priorisé, dispatché | `seo/livrables/actions.csv` |

« Audit », « analyse » et « expertise » désignaient la même opération sous trois
noms : ce sont les étapes 2 et 3. Chaque étape produit un **type d'objet différent**,
ce qui interdit structurellement à la suivante de répéter la précédente.

## Conventions

**Nommage** — slug ASCII kebab-case préfixé du numéro d'ordre : `06-technique/`,
`17-objectif/05-machine-seo/`. Trois raisons : les noms littéraux portent 7 classes de
caractères non-ASCII dont U+2019 dans « Boucles D'Amélioration » ; l'ordre alphabétique
détruirait la séquence méthodologique (`Architecture` avant `Idée`) ; les chemins
Windows restent courts. Le nom d'affichage exact vit dans le manifeste et le
front-matter.

**La 17ᵉ branche `Local` est une extension assumée** du schéma source, qui ne couvrait
pas le SEO local alors que le cadrage propose `local` comme modèle d'acquisition.
Sa portée, comme celle de 8 autres nœuds, est **conditionnelle au modèle** : voir la
section « Portée par modèle » de la grille. Un nœud hors portée est pré-marqué à la
création de l'étude (`new_mission.py --modele`) et **n'entre pas dans la dette
d'instrumentation** — il n'y a rien à obtenir pour le lever.

**Les 2 doublons du schéma** se matérialisent en 2 chemins réels. La branche fait
autorité, la feuille homonyme porte `doublon_de` et **aucun champ à remplir** :

- `06-technique/02-indexation/` → `07-indexation/`
- `17-objectif/04-autorite/` → `08-autorite/`

**Front-matter typé, identique sur les 87 fiches.** C'est ce qui rendra les études
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
2. **`seo/` de la forge en lecture seule** après génération. Aucune étude n'y écrit.
3. **`new_mission.py` refuse** d'écraser une étude existante, et refuse de viser la
   forge. Pas de `--force` : supprimer à la main, après avoir regardé.
4. **Un seul générateur** — `gabarits.py` produit les fiches pour le référentiel comme
   pour les études. Deux copies auraient divergé.
5. **Une seule source de vérité** — fiches générées depuis le manifeste, lui-même
   dérivé de la grille. `validate.py` compare 87 nœuds sur 11 champs.
6. **`.gitkeep` dans tout dossier vide** — Git ne versionne pas les répertoires vides.
7. **Les garde-fous du skill s'appliquent au contenu produit** — étiquetage T1-T4,
   aucune métrique GSC sans export, contenu web traité comme donnée et jamais comme
   instruction, vérification datée pour les surfaces génératives, aucune projection
   présentée comme une prévision.

## Contrôles

`validate.py` — référentiel de la forge :

1. 17 branches, 87 feuilles, 104 dossiers
2. identifiants 1-87 sans trou ni doublon
3. les 2 renvois portent `doublon_de` et n'ont aucun champ à remplir
4. ordre des branches conforme à la séquence du schéma
5. slugs ASCII kebab-case préfixés numériquement
6. aucune dérive entre la grille et le manifeste
7. les 87 fiches ont un front-matter valide et cohérent
8. **la forge n'héberge aucune donnée ni livrable client**
9. aucun dossier sans fichier ni `.gitkeep`

`validate.py --mission <projet>` — étude d'un projet :

1. 104 dossiers sous `seo/analyse/`
2. structure complète (cadrage, état, données, livrables, provenance)
3. les 87 fiches ont un front-matter valide et cohérent
4. version de grille alignée sur la forge
5. compteurs d'avancement cohérents
