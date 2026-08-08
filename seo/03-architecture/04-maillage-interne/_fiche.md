---
id: 14
branche: Architecture
noeud: Maillage Interne
volet: TRANSVERSAL
statut_instrumentation: SD
source_requise: "crawl"
doublon_de: null
# --- rempli pendant la mission ---
etat: a-faire
motif_hors_perimetre: null
verdict: null
niveau_preuve: null
date_mesure: null
actions_liees: []
---

# Architecture / Maillage Interne

> Volet **TRANSVERSAL** -- statut **SD** (instrumente sans dependance externe)

## Question d'audit

Le maillage concentre-t-il l'autorité interne sur les pages à valeur ?

## Source requise

crawl

## Methode

compter les liens internes entrants par page (hors navigation) ; classer par décile

## Critere de verdict

les pages money figurent dans le décile supérieur

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
