# PharmaGraph — Web sémantique

**Parcours humain :** l’accueil, les dossiers patients et la consultation guidée racontent maintenant une histoire commune. Voir [le scénario complet de démonstration](docs/SCENARIO_PARCOURS.md) : dossier → consultation → prescription → suivi → recherche → statistiques.

**Version clinique étendue :** interface Python Streamlit, 19 classes, CRUD général, relations, dashboard Plotly, NLP français/anglais et SPARQL complexe. Consulter [l’architecture et le lancement de la version complète](docs/ARCHITECTURE_V2.md). Les sections ci-dessous décrivent aussi l’interface pharmaceutique initiale conservée.

Pour la version complète : lancer `python run.py`, puis `python run_streamlit.py` dans un second terminal. Ouvrir http://127.0.0.1:8501.

Mini-projet sur la modélisation des molécules, effets secondaires, contre-indications et données cliniques. Toutes les données sont **synthétiques** et ne constituent pas une information médicale.

## Démarrer sous Windows

Python 3.11 ou supérieur. Dans le dossier du projet :

```powershell
python -m pip install --target .deps -r requirements.txt
python run.py
```

Ouvrir http://127.0.0.1:8000 ; documentation interactive : http://127.0.0.1:8000/docs.
Les dépendances sont déjà installées dans `.deps` sur le poste de développement. Aucun modèle NLTK ni corpus à télécharger. Seules les polices de l’interface utilisent Google Fonts ; des polices système prennent le relais hors ligne.

## Fonctionnalités

Pour construire et vérifier l’ontologie dans **Protégé**, voir [le protocole Protégé](docs/PROTOCOLE_PROTEGE.md). Le lanceur `Ouvrir-Protege.ps1` ouvre `data/pharmagraph.owl`. Après une modification dans Protégé, arrêter le serveur, exécuter `python scripts/protege_data.py import data/pharmagraph.owl`, puis relancer l’application.

- Explorateur en français avec résultats, intention, tokens, racines, entités et requête générée.
- Catalogue filtrable de six molécules fictives.
- Administration : ajouter, consulter, modifier, supprimer des molécules et leurs relations aux effets/contre-indications existants.
- Console SELECT/ASK, filtre numérique sur les phases, tri et export Turtle.
- Ontologie OWL avec classes, ObjectProperty, DatatypeProperty, individus et axiomes.
- API FastAPI et interface HTML/CSS/JavaScript reliées par `fetch` et JSON, sur la même origine.
- Mises à jour réalisées réellement avec `Graph.update()` et sauvegardées dans `data/live.ttl`.

## Organisation

| Fichier | Rôle |
|---|---|
| `data/ontology.ttl` | Ontologie et jeu initial immuable |
| `data/live.ttl` | État sauvegardé, créé à la première modification |
| `backend/app.py` | API, exécution SPARQL, validation et persistance |
| `backend/nlp.py` | Traducteur NLP déterministe |
| `frontend/` | Interface responsive en français |
| `tests/` | Tests d’intégration sur fichiers isolés |
| `docs/SOUTENANCE.md` | Scénario, architecture, grille et limites |
| `docs/requetes.sparql` | Requêtes à présenter |

## NLP : outils et fonctionnement

**NLTK `RegexpTokenizer` et `FrenchStemmer`**, normalisation Unicode, règles d’intention et reconnaissance des entités par leur label RDF. Les racines servent à reconnaître les variations de mots. Le lexique des entités est relu dans le graphe à chaque question, y compris après ajout d’une molécule.

Pipeline : question → normalisation des accents → tokens → racines françaises → intention + entités → patron SPARQL → exécution RDFLib → tableau JSON.

Exemples pris en charge :

1. « Quels sont les effets secondaires de la Molécule Alpha ? »
2. « Quelles sont les contre-indications de la Molécule Bêta ? »
3. « Lister les molécules avec des nausées »
4. « Quels essais cliniques de phase 2 pour la Molécule Gamma ? »
5. « Lister les molécules contre-indiquées pendant la grossesse »
6. « Lister les molécules »

Ce parseur couvre un langage contrôlé, pas tout le français. Utiliser les noms complets du catalogue. Les questions non reconnues, les noms de molécules inconnus et les questions comportant plusieurs molécules sont refusés. Les opérations d’écriture sont réservées à l’administration. Aucune API de LLM, aucun prompt engineering, aucun appel à Gemini/OpenAI.

## Tests

```powershell
python -c "import sys; sys.path.insert(0,'.deps'); import pytest; sys.exit(pytest.main(['-q','--basetemp=.test-tmp']))"
node --check frontend/app.js
```

Les tests vérifient les résultats sémantiques, le CRUD, la persistance, les littéraux contenant des caractères spéciaux, les relations invalides, les questions inconnues, l’interdiction de SERVICE/FROM et les ressources de l’interface.

## Limites assumées

Application locale de démonstration, sans authentification ni hébergement public. Elle écoute sur `127.0.0.1`. Ne pas l’exposer directement sur Internet : la console n’a pas de budget d’exécution et les écritures ne sont pas authentifiées. Un seul processus serveur, avec verrou pour les accès au graphe ; pas de base multi-utilisateur.

Les axiomes sont déclarés, mais RDFLib n’effectue pas de raisonnement OWL. Les relations inverses/symétriques ne sont pas matérialisées. Ouvrir l’ontologie exportée dans Protégé pour démontrer un raisonneur. Les relations aux essais et interactions sont dans le jeu initial ; l’éditeur porte sur les molécules, leurs formules, effets et contre-indications. Modifier une molécule conserve ses liens vers les essais et interactions.

Pour retrouver le jeu initial, arrêter le serveur et déplacer `data/live.ttl` hors du dossier `data`, puis relancer.
