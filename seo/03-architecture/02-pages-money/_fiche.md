---
id: 12
branche: Architecture
noeud: Pages Money
volet: TRANSVERSAL
statut_instrumentation: SD
source_requise: "crawl + cadrage (requêtes money)"
doublon_de: null
modeles: b2b-lead-gen,e-commerce,local,media-affiliation,saas
# --- rempli pendant la mission ---
etat: a-faire
motif_hors_perimetre: null
verdict: null
niveau_preuve: null
date_mesure: null
actions_liees: []
---

# Architecture / Pages Money

> Volet **TRANSVERSAL** -- statut **SD** (instrumente sans dependance externe)

## Question d'audit

Les pages à intention transactionnelle sont-elles identifiées, uniques et hautes dans l'arbre ?

## Source requise

crawl + cadrage (requêtes money)

## Methode

pour chaque requête money du cadrage, identifier la page cible ; détecter les cas où deux pages visent la même requête

## Critere de verdict

1 page par requête money (0 cannibalisation) **et** profondeur ≤ 2 clics

---

## Constat

<!-- Etape 2 du pipeline. Ce qui est, mesure. Chaque chiffre porte son
     niveau de preuve : [T1 observe] [T2 declare] [T3 tiers] [T4 infere].
     Si non mesurable : le dire et renseigner motif_hors_perimetre. -->

## Preuves

<!-- Ou la mesure a ete prise : URL, fichier d'export et periode, requete,
     date de consultation. Verifiable par un tiers. -->

## Interpretation

<!-- Etape 3 du pipeline. Le mecanisme : comment ce constat coute du trafic
     ou des leads. "Ce n'est pas optimal" n'est pas un mecanisme. -->
