# Volet STRATÉGIE — méthode

À charger en **R3**. C'est ce qui distingue une trajectoire d'un audit : l'audit dit où en est le site, la stratégie dit où il peut aller, dans quel ordre, et à quelles conditions.

Garde-fou dominant sur tout ce fichier : **le futur est du `[T4]`.** Fourchette obligatoire, calcul visible, sensibilité déclarée. Une projection présentée comme une prévision est un défaut de livraison.

---

## 1. Lire le modèle d'acquisition avant tout

Le même diagnostic produit des stratégies opposées selon le modèle. Ce paramètre entre par le cadrage et n'est jamais deviné.

| Modèle | Ce qui compte | Ce qui est un piège |
|---|---|---|
| **B2B lead-gen** | requêtes à intention d'achat, même à faible volume ; preuve d'expertise ; pages de solution et de comparaison | le volume. Un site à 200 visites/mois et 3 leads à fort panier n'a pas de problème de trafic |
| **E-commerce** | couverture catégorielle et attributs, facettes indexables maîtrisées, requêtes produit et marque | le contenu éditorial déconnecté des pages transactionnelles |
| **Média / affiliation** | volume, longue traîne, fraîcheur, comparatifs, surfaces de découverte | le contenu qui ne se monétise pas ; l'exhaustivité sans intention commerciale |
| **Local** | requêtes géolocalisées, cohérence des informations d'établissement, avis, pages par zone | la duplication entre pages de villes |
| **SaaS** | requêtes de problème et d'alternative, cas d'usage, intégrations, documentation indexable | les requêtes de marque des concurrents comme axe principal |

Si le modèle déclaré et la structure observée divergent — un site B2B bâti comme un média, par exemple —, **c'est le premier constat stratégique du livrable**, avant toute recommandation.

---

## 2. Construire la cible 12 et 24 mois

### Avec baseline GSC

Calcul à afficher intégralement dans le livrable, requête par requête ou par famille :

```
Pour chaque famille de requêtes retenue :
  gain_clics = impressions_actuelles × (CTR_cible − CTR_actuel)

  CTR_actuel : mesuré, [T2 déclaré]
  CTR_cible  : CTR médian OBSERVÉ SUR CE SITE pour la tranche de position visée, [T2 déclaré]

Cible_12m = baseline_clics + Σ gain_clics des familles engagées sur 4 trimestres
```

Le `CTR_cible` se prend sur **les données du site lui-même**, pas sur une courbe de CTR par position issue d'une étude externe. Deux raisons : la courbe dépend du type de requête et de la SERP, et une valeur empruntée est un `[T3]` daté qui contamine tout le calcul. Si le site n'a aucune page en top 3 permettant d'établir sa propre médiane, dis-le et élargis la fourchette au lieu d'importer un chiffre.

**Fourchette obligatoire** : hypothèse basse = la moitié des familles atteignent la position cible ; hypothèse haute = toutes l'atteignent. Jamais un chiffre unique.

### Sans baseline GSC

La cible n'est **pas calculable en clics**. Deux sorties acceptables, jamais une troisième :

1. **Cible en jalons observables** : nombre de requêtes cibles avec une page dédiée indexée, nombre de silos structurés, nombre de domaines référents thématiques, présence en top 10 sur N requêtes vérifiée manuellement à date. Tout est `[T1]` ou `[T3]`, vérifiable, et suffit à piloter.
2. **Déclaration explicite de non-calculabilité** de la cible en trafic, avec la liste de ce qu'il faut fournir pour la calculer.

Ne jamais produire une cible en clics à partir de volumes de recherche estimés de mémoire.

### Cible business

Ne s'obtient que par chaînage, et chaque maillon peut manquer :

```
clics cibles → × taux de conversion organique mesuré (nœud 46) → leads cibles
             → × valeur client (nœud 8)                       → revenu cible
```

Si un maillon est en `NM`, la cible s'arrête au maillon précédent et la suite est déclarée non calculable (nœuds 79 et 80). **Un taux de conversion supposé rend toute la chaîne fictive** — c'est le point où un audit SEO perd sa crédibilité le plus vite.

---

## 3. Trajectoire T1 → T4 : l'ordre avant le contenu

Une roadmap qui liste des chantiers par trimestre sans justifier l'ordre n'est pas une trajectoire, c'est un calendrier. **Chaque chantier déclare ce qui doit être fini avant lui.**

### Dépendances structurantes — non négociables

| Avant | Il faut | Pourquoi |
|---|---|---|
| produire du contenu | le site est indexable et crawlable | publier dans un site non indexable ne produit rien de mesurable |
| créer les pages money | l'architecture et les silos sont arrêtés | sinon les pages sont créées au mauvais endroit et devront être redirigées |
| créer les satellites | la page money existe | un satellite sans cible pointe dans le vide |
| lancer l'acquisition de liens | le contenu qui les mérite existe | on n'obtient pas de lien vers une page vide |
| optimiser | la mesure est en place | optimiser sans mesure, c'est deviner puis oublier |
| industrialiser (contenu programmatique, génération) | un gabarit a été validé manuellement sur 5 à 10 pages | industrialiser un mauvais gabarit multiplie le défaut par N |
| viser les surfaces génératives | les nœuds d'entité et de contenu non substituable sont traités | une entité floue n'est pas citée |

### Forme attendue

Par trimestre : les chantiers, leur charge cumulée en jours-homme confrontée à la capacité déclarée, les dépendances levées, et **ce qui devient mesurable à la fin du trimestre**. Un trimestre qui ne rend rien mesurable est un trimestre à réordonner.

Séquence par défaut, à adapter et à justifier si modifiée :

- **T1 — débloquer et mesurer** : levée des blocages techniques et d'indexation, pose de la mesure, quick wins à confiance élevée.
- **T2 — structurer** : architecture, silos, pages money, maillage, correction de la cannibalisation.
- **T3 — produire** : piliers, guides, comparatifs, couverture des questions, premières briques d'entité.
- **T4 — amplifier et composer** : autorité, partenariats, industrialisation de ce qui a été validé, ouverture du silo suivant, boucle d'amélioration outillée.

---

## 4. Nouveaux territoires — sur un site existant

Les nœuds `Idée/Niche`, `Idée/Opportunité Cachée` et `Croissance/Nouveaux Silos` sont écrits comme pour une création. Appliqués à un site en production, ils se reformulent en **extension de couverture**, et la question dominante devient la légitimité.

Test à trois conditions — les trois doivent passer :

1. **Demande démontrée** : requêtes identifiées avec une preuve de demande (`[T2]` impressions, ou `[T3]` SERP active et concurrence présente). Pas d'intuition de sujet porteur.
2. **Légitimité démontrable** : le site peut produire sur ce thème quelque chose qu'un concurrent ne copie pas en une semaine (donnée propre, expérience, produit, expertise identifiable). Sans cela, le territoire est ouvert puis perdu.
3. **SERP attaquable** : nœud 20, au moins 3 signaux de faiblesse sur le top 10.

Un territoire qui échoue au test 2 est un territoire à ne pas ouvrir, même si les tests 1 et 3 passent — c'est le cas le plus fréquent et le plus coûteux.

Sur le nœud 74 (`Nouveaux Sites`), la question se pose **à l'envers** : qu'est-ce qui empêche de le faire sur le domaine existant ? Un nouveau site n'est justifié que par une inadéquation structurelle du domaine (marque, langue, modèle économique distinct), jamais pour contourner un déficit d'autorité — qu'il aggrave, puisqu'il repart de zéro.

---

## 5. Validation économique quand le client ne connaît pas ses chiffres

Cas le plus fréquent : ni coût du lead, ni valeur client, ni vitesse de monétisation. Protocole :

1. **Demander une fois, explicitement**, en disant à quoi chaque chiffre sert. Beaucoup de clients les ont sans savoir qu'ils sont pertinents ici.
2. Si le chiffre arrive : `[T2 déclaré]`, avec la source et la période. L'utiliser tel quel, ne pas le « corriger ».
3. Si le chiffre n'arrive pas : **ne pas le remplacer par une moyenne sectorielle.** Basculer sur les jalons observables du point 2, et inscrire le manque dans `dette-instrumentation` avec ce qu'il bloque précisément.
4. Si le client propose lui-même une estimation, la reprendre comme **hypothèse du client** (`[T2]`, mention « estimation client non mesurée ») et la mettre en tête de la note de sensibilité — c'est souvent la variable la plus fragile de tout le plan.

---

## 6. Surfaces génératives — GEO

Domaine où le risque de conseil périmé est le plus élevé. **Garde-fou 4 obligatoire : vérification web datée avant toute recommandation, à chaque run.** Le socle de connaissances du modèle est daté et ce champ bouge en continu.

### Mesurer la présence actuelle

Protocole explicite, reproductible et daté :

- N requêtes cibles, formulations exactes consignées ;
- surfaces interrogées, nommées et datées ;
- pour chacune : le site est-il cité, sous quelle forme, à quel rang, avec quel extrait ;
- résultat consigné avec sa date.

**Limite à déclarer sans détour** : ces réponses ne sont ni stables ni reproductibles — elles varient selon l'utilisateur, la session et le moment. Le taux de citation relevé est une **photographie datée**, pas une métrique de suivi. Le présenter comme un KPI mesurable serait un abus.

### Construire la présence

Ce qui relève de l'observable et se travaille sans dépendre d'une surface particulière :

1. **Entité nette** (nœud 53) : identité balisée, cohérente sur tout le site, liée à des profils tiers vérifiables. Une entité ambiguë n'est pas citée.
2. **Affirmations attribuables** (nœud 26) : information factuelle, formulée de façon autonome, rattachable à une source identifiée.
3. **Réponse en tête** : la réponse à la question de la page se trouve dans les premières lignes, pas au terme d'une mise en scène.
4. **Contenu non substituable** (nœud 56) : donnée propre, chiffre original, expérience. Ce qui est déjà partout n'a aucune raison d'être cité depuis ce site plutôt qu'un autre.
5. **Accessible sans JavaScript** : ce qui n'est pas dans le HTML initial n'est pas garanti d'être lu.

Ces cinq leviers sont des invariants raisonnables, mais **leur formulation doit être revérifiée à chaque run** — ne pas les traiter comme un acquis figé.

---

## 7. Règle de projection

Toute projection de trafic, de position, de leads ou de revenu :

- porte l'étiquette **`[T4 inféré]`** ;
- affiche son **calcul en clair**, avec les valeurs d'entrée et leur propre étiquette ;
- donne une **fourchette basse / haute**, jamais un chiffre unique ;
- s'accompagne d'une **note de sensibilité** nommant la variable qui casse la projection et l'effet de son erreur.

Modèle de note de sensibilité :

> La cible à 12 mois repose sur trois hypothèses. **(1)** Le taux de conversion organique de 2,4 % `[T2, GA, 2026-02→07]` reste stable à volume triplé — s'il tombe à 1,2 %, la cible en leads est divisée par deux, la cible en trafic reste valable. **(2)** Les 14 requêtes du silo X atteignent le top 5 — si seules 6 y parviennent, le gain en clics passe de 2 100 à 900 par mois. **(3)** La capacité déclarée de 4 j-h par mois est maintenue — une réduction à 2 j-h reporte T3 et T4 d'un trimestre chacun. **Variable la plus fragile : (1)**, car elle n'a jamais été observée à ce volume.

Si aucune note de sensibilité ne peut être écrite parce qu'aucune variable n'est mesurée, alors **il n'y a pas de projection à faire** : produire des jalons observables et le dire.
