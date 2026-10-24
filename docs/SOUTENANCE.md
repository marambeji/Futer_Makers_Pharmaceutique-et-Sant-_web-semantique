# Guide de soutenance — PharmaGraph

Pour la version étendue demandée ensuite (19 classes, Streamlit, CRUD général, NLP clinique et dashboard), utiliser également [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md). Le scénario ci-dessous reste valable pour l’interface pharmaceutique initiale.

## 1. Problématique et scénario

Comment explorer un graphe pharmaceutique sans maîtriser SPARQL ? Un utilisateur pose une question en français et reçoit les liens stockés dans l’ontologie. Un administrateur enrichit le jeu synthétique. Le système rend visible la traduction NLP pour expliquer chaque réponse.

Scénario de 7 à 10 minutes :

1. Présenter la problématique et le caractère fictif des données.
2. Ouvrir « Ontologie », décrire les classes et exporter le Turtle vers Protégé.
3. Montrer les ObjectProperty : `aEffetSecondaire`, `aContreIndication`, `etudieDans`, `interagitAvec`, `effetDe`.
4. Montrer les DataProperty : `formule`, `phase`, `participants`, `statut`, `frequence`.
5. Expliquer les axiomes : domaine/portée, disjonction, inverse, symétrie, cardinalité et restriction existentielle de `MoleculeAvecRisque`.
6. Rechercher les effets d’Alpha ; ouvrir la trace NLP et lire le SPARQL.
7. Rechercher les molécules avec des nausées pour montrer le parcours inverse.
8. Rechercher les essais de phase 2 de Gamma ; montrer les participants et le statut.
9. Dans la console, exécuter la requête de filtrage et celle d’agrégation du fichier `requetes.sparql`.
10. Ajouter `Omega`, nom `Molécule Oméga`, formule `C10H14O2`, avec Nausées et Grossesse. Montrer le SPARQL INSERT et retrouver l’individu par une question.
11. Modifier sa formule ; montrer DELETE + INSERT. Supprimer Omega ; montrer la disparition dans le catalogue.
12. Montrer `/docs` et expliquer que le navigateur communique en HTTP/JSON avec FastAPI.

## 2. Architecture

```text
Navigateur HTML/CSS/JS
    | fetch HTTP / JSON
    v
FastAPI
    +-- /api/ask --> NLTK + lexique RDF + règles --> SELECT
    +-- /api/sparql --> SELECT / ASK locaux
    +-- /api/molecules --> validation --> INSERT / DELETE SPARQL
    |
    v
RDFLib Graph <--> data/live.ttl
    ^
data/ontology.ttl (jeu initial)
```

## 3. Module NLP à expliquer explicitement

Outils utilisés : Python, NLTK (RegexpTokenizer, FrenchStemmer), `unicodedata`, expressions régulières et RDFLib. Aucun LLM, aucun entraînement de modèle, aucune clé API.

Exemple : « Quels sont les effets secondaires de la Molécule Alpha ? »

- Accents normalisés pour comparer les textes.
- Découpage en tokens ; racinisation française pour l’intention.
- Reconnaissance du label `Molécule Alpha` dans le graphe.
- Intention `effets` associée à `aEffetSecondaire`.
- URI de l’entité insérée dans un patron fixe, pas de concaténation libre de la question.
- Exécution du SELECT par RDFLib, restitution en tableau.

La traçabilité et le lexique dynamique constituent la valeur ajoutée. Ne pas présenter ce système comme une compréhension générale du langage. Montrer aussi un refus : « Effets de la Molécule Inconnue ».

## 4. Correspondance avec la grille

| Critère | Démonstration |
|---|---|
| SPARQL (4) | SELECT, ASK, FILTER, ORDER BY, agrégation, INSERT DATA, DELETE WHERE |
| Individus (2) | 6 molécules, 4 effets, 3 contre-indications, 3 essais |
| Scénario (2) | Recherche, exploration clinique et enrichissement du graphe |
| « Api IA » (4) | Endpoint NLP local, NLTK et règles, trace du pipeline ; interprétation à valider avec l’enseignante |
| Interfaces graphiques (3) | Exploration, catalogue, console, ontologie et administration |
| Communication BE/FE (3) | fetch → endpoints FastAPI → JSON → affichage |
| Valeur ajoutée (2) | Explicabilité du NLP, entités dynamiques, export OWL/Turtle, persistance |

## 5. Limites et perspectives

Langage contrôlé ; pas de raisonneur OWL intégré ; données fictives ; pas d’authentification ; pas de concurrence multi-processus. Extensions possibles : corpus annoté et évaluation précision/rappel, reconnaissance d’entités entraînée, SHACL pour la validation et triplestore pour les gros graphes.

La cardinalité OWL décrit le modèle et n’est pas un validateur de formulaires. Le backend contrôle explicitement les champs et les relations éditables. Ne pas affirmer que les tests prouvent une cohérence OWL complète.
