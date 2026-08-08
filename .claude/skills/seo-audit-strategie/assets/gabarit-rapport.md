# Gabarit du rapport — `audit-<domaine>-<AAAA-MM-JJ>.md`

Structure imposée. **≤ 4 000 mots hors tables.** Les sections marquées *(obligatoire)* ne sont jamais omises, même vides — une section vide porte son motif.

---

## Bloc 0 — Périmètre et fiabilité *(obligatoire, en tête)*

Ce bloc vient avant toute conclusion. Il dit au lecteur ce qu'il peut croire.

```markdown
# Audit & stratégie SEO — <domaine>
**Date du run** : AAAA-MM-JJ · **Audience** : <dirigeant / marketing / technique>
**Modèle d'acquisition** : <…> · **Marché** : <pays, langue>

## Périmètre et fiabilité

| | |
|---|---|
| Pages découvertes | N `[T1]` |
| Pages échantillonnées | N (méthode : …) |
| Concurrents analysés | … |
| Exports fournis | GSC : oui/non (période) · GA : oui/non (période) · CRM : oui/non |
| Nœuds mesurés | N / 82 |
| Nœuds non mesurables | N / 82 — détail dans `dette-instrumentation-<domaine>-<date>.md` |
| Plafond de run | N fetches · N recherches web |
| Rendu JavaScript | détecté oui/non — gabarits affectés : … |

**Ce que ce rapport ne peut pas dire** : <liste directe des conclusions hors de portée faute de source>.

**Légende des preuves** — `[T1 observé]` mesuré · `[T2 déclaré]` export client, période indiquée ·
`[T3 tiers]` source et date citées · `[T4 inféré]` hypothèse, fourchette et calcul visibles.
```

---

## Bloc 1 — Synthèse *(obligatoire)*

Une page, calibrée sur l'audience déclarée. Contenu :

- **Le constat en trois phrases** — dont une qui nomme le blocage principal, sans le diluer.
- **Score de maturité 1-5** (nœud 82, `Machine SEO`), justifié en une ligne.
- **Les trois actions qui comptent** — les trois premières du tri, avec leur gain, leur effort et leur horizon.
- **La cible 12 mois** — fourchette basse/haute, `[T4]`, avec renvoi au calcul du bloc 4.
- **Ce qu'il faut fournir** pour lever les principales zones aveugles.

Pas de recommandation nouvelle ici : la synthèse ne dit rien que le corps ne démontre.

---

## Bloc 2 — Volet ÉTAT *(obligatoire)*

### 2.1 Baseline mesurée

Uniquement `[T1]` et `[T2]`. C'est l'état de référence que le prochain run comparera. Si vide faute d'export, l'écrire : *« aucune baseline de performance — le suivi démarrera au prochain run avec export GSC »*.

### 2.2 Points forts — 10 maximum

Format par point : le constat · la preuve étiquetée · pourquoi c'est un actif à préserver.

### 2.3 Points faibles — 15 maximum, par impact décroissant

Format par point : le constat · la preuve étiquetée · **le mécanisme** (comment cela coûte du trafic ou des leads) · le ou les nœuds concernés · l'action qui y répond (renvoi vers son id).

> « Ce n'est pas optimal » n'est pas un mécanisme. « Les 8 pages money sont à 4 clics de l'accueil et reçoivent chacune moins de 2 liens internes contextuels : l'autorité interne se concentre sur le blog, et ces pages ne dépassent pas la page 2 sur leurs requêtes » en est un.

### 2.4 Couverture 82/82 *(obligatoire, table compacte)*

| # | Nœud | Volet | Statut | Verdict ou motif de non-mesure |
|---|---|---|---|---|

82 lignes. Aucune omise. Le compte est affiché en fin de table.

---

## Bloc 3 — Volet STRATÉGIE *(obligatoire)*

### 3.1 Lecture du modèle d'acquisition

Ce que le modèle déclaré implique, et **tout écart entre le modèle déclaré et la structure observée** — c'est le premier constat stratégique s'il existe.

### 3.2 Axes stratégiques — 5 à 8

Le « quoi » : où le site peut gagner, et pourquoi lui plutôt qu'un concurrent. Un axe sans réponse à la seconde question n'est pas un axe.

### 3.3 Territoires à conquérir

Chacun passé au test à trois conditions (demande démontrée · légitimité démontrable · SERP attaquable). Les territoires **rejetés** sont listés avec le motif : c'est une décision, pas une omission.

### 3.4 Cible 12 et 24 mois

Calcul affiché intégralement, valeurs d'entrée étiquetées, fourchette basse/haute, `[T4]`.
Si non calculable : jalons observables + déclaration explicite de non-calculabilité.

### 3.5 Note de sensibilité *(obligatoire)*

Les hypothèses, leur effet chiffré si elles se démentent, et **la variable la plus fragile nommée**.

---

## Bloc 4 — Actions et priorisation *(obligatoire)*

### 4.1 Barème appliqué

Rappel en 5 lignes des échelles et de la formule, avec le trait de coupe retenu et la capacité déclarée.

### 4.2 Actions au-dessus du trait de coupe

Table renvoyant au CSV pour le détail. Colonnes affichées : id · action · gain · effort · confiance · score · horizon · exécution · coût.

### 4.3 Remontées par dépendance

Actions sous le trait remontées parce qu'une action prioritaire en dépend, chacune nommant l'action dont elle est le prérequis.

### 4.4 Confrontation à la capacité *(obligatoire)*

Somme des efforts retenus vs capacité déclarée, en trimestres réels. **Ce qui a été coupé est nommé.** Si la capacité n'est pas déclarée, le dire et ne pas feindre un plan tenable.

---

## Bloc 5 — Dispatch en 4 quadrants *(obligatoire)*

Un sous-bloc par quadrant, chacun **priorisé en interne** :

### 5.1 `IA + GRATUIT`
### 5.2 `IA + PAYANT` — coûts en € avec périodicité et fourchette
### 5.3 `MANUEL + GRATUIT`
### 5.4 `MANUEL + PAYANT` — coûts en € avec périodicité et fourchette

Chaque action porte son **régime d'automatisation** : `automatisable de bout en bout` · `IA assistée avec validation humaine` · `manuel strict`.

### 5.5 Actions à variantes

Les actions présentes dans plusieurs quadrants, avec les deux variantes décrites et **l'écart de gain entre elles**. Uniquement des variantes réelles.

### 5.6 Avertissement sur l'avantage concurrentiel *(obligatoire, verbatim ou reformulé sans l'affaiblir)*

> Le quadrant `IA + gratuit` est celui de la plus faible barrière à l'entrée, donc du plus faible avantage concurrentiel durable : les concurrents outillés en IA exécutent les mêmes actions, au même coût, dans le même délai. Ces actions sont nécessaires — elles ramènent à la parité — mais elles ne créent pas d'écart.

Suivi de : **socle de différenciation** — les actions du quadrant `manuel + payant` qui, elles, créent un écart durable, nommées et justifiées. Dit sans l'enrober.

---

## Bloc 6 — Prochaines étapes *(obligatoire)*

- Ce qui démarre au T1, avec le premier livrable attendu et sa date.
- Ce qu'il faut obtenir du client (exports, accès, décisions) avec l'échéance.
- La date du prochain run et ce qu'il pourra mesurer de plus.

---

## Interdits de forme

- Aucun chiffre sans étiquette de preuve.
- Aucun tableau rempli « pour faire complet » : une cellule sans donnée porte le motif.
- Aucune recommandation sans critère d'acceptation vérifiable.
- Aucune assertion sur le fonctionnement de Google sans source datée.
- Aucun superlatif à la place d'une mesure (« très bon maillage » → le chiffre, ou rien).
