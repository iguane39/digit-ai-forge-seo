---
id: 13
branche: Architecture
noeud: Pages Satellites
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

# Architecture / Pages Satellites

> Volet **TRANSVERSAL** -- statut **SD** (instrumente sans dependance externe)

## Question d'audit

Des pages de soutien pointent-elles vers les pages money ?

## Source requise

crawl

## Methode

compter les liens internes contextuels entrants vers chaque page money, en excluant menus et pieds de page

## Critere de verdict

≥ 3 satellites par page money, liens en corps de texte

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
