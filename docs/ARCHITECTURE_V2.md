# PharmaGraph Clinical — extension du projet existant

## Ce qui est réutilisé

Le namespace, les molécules, les axiomes OWL initiaux, le traducteur pharmaceutique, l’API FastAPI, l’interface HTML et l’installation Protégé restent disponibles. L’extension ajoute `data/clinical.ttl`, sans remplacer `data/ontology.ttl` ni le fichier ouvert précédemment dans Protégé.

## Lancer l’application complète

Dans un premier terminal, depuis la racine :

```powershell
python -m pip install --target .deps -r requirements.txt
python run.py
```

Dans un deuxième terminal :

```powershell
python run_streamlit.py
```

Interface Python : http://127.0.0.1:8501 ; interface initiale : http://127.0.0.1:8000 ; documentation API : http://127.0.0.1:8000/docs.

Un `.env` facultatif configure l’adresse API, le port et le chemin des données. Copier `.env.example` en `.env` et ajuster les valeurs. Aucune clé API n’est nécessaire : l’interdiction initiale des API de LLM est respectée.

## Modèle complet

19 classes : EntiteSante, Molecule, MoleculeAvecRisque, EffetSecondaire, ContreIndication, EssaiClinique, Personne, Patient, Medecin, Consultation, RendezVous, Maladie, Traitement, Medicament, Prescription, Hopital, Service, Assurance, Vehicule.

Jeu clinique synthétique : 8 patients, 3 médecins, 8 consultations, 5 prescriptions, 2 rendez-vous, 3 maladies, 3 médicaments, 2 traitements, 2 hôpitaux, 3 services, 2 assurances et 3 véhicules. Les six molécules et données cliniques du premier projet sont conservées. Les noms, associations et protocoles sont fictifs ; les formats sont réalistes, aucune posologie médicale réelle n’est fournie.

La distinction `Medicament` / `Molecule` permet de relier la prescription à un produit, puis à sa molécule, ses effets et ses contre-indications.

## Modules

| Couche | Fichiers | Responsabilité |
|---|---|---|
| UI Python | `ui/app.py`, `ui/client.py` | Streamlit, Plotly et appels HTTP réels |
| API | `backend/app.py` | Routes, validation Pydantic, verrou partagé |
| Schéma | `backend/schema.py` | Classes, propriétés et champs dérivés du graphe OWL |
| Métier | `backend/entities.py` | CRUD de classes et relations ; validation des cibles, valeurs et cardinalités |
| Persistance | `backend/store.py` | Migration additive, SPARQL UPDATE sur copie, sauvegarde atomique |
| Requêtes | `backend/engine.py`, `backend/queries.py` | Analyse syntaxique, contrôle des opérations et bibliothèque complexe |
| NLP | `backend/nlp.py`, `backend/clinical_nlp.py` | Reconnaissance des entités et compilation de critères vers SPARQL |
| Statistiques | `backend/analytics.py` | Agrégations calculées par SPARQL |
| Qualité | `backend/quality.py` | Contrôles explicables des données contre le schéma |
| Protégé | `scripts/protege_data.py` | Échange RDF/XML et Turtle avec sauvegarde avant import |

## NLP et explication

Outils réellement utilisés : NLTK `RegexpTokenizer`, `FrenchStemmer`, `EnglishStemmer`, normalisation Unicode, expressions régulières, lexique des individus et propriétés OWL, parseur SPARQL RDFLib. Le moteur est un analyseur sémantique à règles ; il n’utilise ni LLM, ni modèle entraîné, ni service externe.

Les phrases ne sont pas mémorisées comme des questions exactes : plusieurs critères compatibles se composent (médecin + hôpital + maladie + médicament + véhicule + âge + période). Chaque propriété utilisée doit être présente dans le schéma réel. Les labels et identifiants sont résolus dynamiquement, y compris pour les individus ajoutés via le CRUD. Les URI viennent du graphe ; la question brute n’est pas injectée dans SPARQL.

L’anglais couvre notamment la liste de patients, la possession d’un véhicule, le suivi par un médecin, des filtres d’âge et les périodes. Il ne couvre pas toutes les paraphrases françaises et anglaises. La console permet d’exprimer les demandes en dehors de la grammaire implémentée. Les alternatives et négations non prises en charge sont refusées. Les exemples sont fournis par `/api/examples` et testés sur les résultats RDF attendus.

Les résultats comprennent le SPARQL, une explication des critères, les tokens, les racines, les entités reconnues et un résumé du nombre de résultats. Aucune réponse n’est créée à partir d’informations absentes du graphe. Un résultat vide n’est pas assimilé à une absence réelle (hypothèse de monde ouvert).

## SPARQL avancé

La bibliothèque de la console démontre : jointures jusqu’à six classes, FILTER numérique et temporel, OPTIONAL, UNION, DISTINCT, GROUP BY, HAVING, ORDER BY, COUNT, AVG, SUM, MIN, MAX et sous-requêtes. Toutes les requêtes d’exemple sont exécutées dans les tests, certaines avec un résultat de référence exact.

La console valide l’arbre syntaxique avant exécution. `SERVICE`, `FROM` et les opérations d’écriture y sont refusés. Les chaînes littérales contenant ces mots restent autorisées. Le CRUD utilise réellement `INSERT DATA`, `DELETE DATA` et `DELETE WHERE`, dans des transactions préparées sur une copie du graphe avant sauvegarde.

## CRUD et liens

Les formulaires reprennent les DataProperty et ObjectProperty applicables à la classe et ses parents. Ils proposent les cibles du type OWL attendu. Les champs obligatoires du métier, dates ISO, âges, valeurs numériques, propriétés fonctionnelles et identifiants sont contrôlés côté serveur. Les classes définies par restriction, comme `MoleculeAvecRisque`, sont consultables et éditables avec les propriétés de leurs parents explicites ; aucune inférence OWL générale n’est simulée.

La suppression retire les liens entrants et sortants, mais elle est bloquée si elle rend une relation obligatoire orpheline. L’écran Relations permet de retirer un lien sans supprimer ses individus. Les types et annotations hors des propriétés éditées sont préservés lors d’une modification. L’ancienne API molécules reste compatible.

## Dashboard et fonctionnalité supplémentaire

Les nombres et graphiques viennent exclusivement d’agrégations SPARQL, avec leur requête consultable. Âge et sexe définissent la cohorte ; les dates filtrent les consultations et prescriptions. Le compteur des patients ne devient pas artificiellement un compteur d’actes dans la période. Les maladies d’un même patient peuvent contribuer à plusieurs barres ; les catégories ne sont donc pas exclusives.

L’audit des données vérifie les champs requis, cardinalités, types, domaines, portées et disjonctions explicites. Chaque anomalie précise l’individu, la règle et le problème. Il s’agit d’une fonctionnalité de qualité explicable, pas d’un raisonneur OWL complet ni d’un diagnostic médical.

## Protégé et persistance

Au premier démarrage, l’extension est ajoutée au graphe existant. Un marqueur `ClinicalExtension` empêche de réintroduire les individus supprimés aux démarrages suivants. Les données utilisateur existantes sont conservées.

Pour ouvrir le modèle complet dans Protégé sans écraser l’ancien fichier :

```powershell
python scripts/protege_data.py export data/pharmagraph-complet.owl
```

Ou utiliser **Ontologie → Exporter OWL pour Protégé** dans Streamlit. L’export inclut les données actives. Dans Protégé, **File → Open**, sélectionner ce fichier, éditer puis enregistrer en RDF/XML. Arrêter l’API avant d’importer :

```powershell
python scripts/protege_data.py import data/pharmagraph-complet.owl
python run.py
```

Pas de synchronisation temps réel entre le processus Protégé et l’API. Ne pas modifier le fichier exporté sur disque en supposant qu’il remplace automatiquement le graphe en mémoire.

## Validation et limites

```powershell
python -c "import sys; sys.path.insert(0,'.deps'); import pytest; sys.exit(pytest.main(['-q','--basetemp=.test-tmp-validation']))"
```

Les tests isolent les données et ne modifient pas le graphe de démonstration. Le système reste une application universitaire locale, sur un seul processus API. Sans authentification ni limite de temps d’exécution des requêtes : ne pas exposer les ports à Internet. Les résultats sont limités à 1 000 lignes pour l’affichage, 100 pour le NLP. Les périodes NLP relatives sont calculées au jour de la requête ; les requêtes temporelles de la bibliothèque ont des bornes explicites pour une démonstration reproductible.

Validation de cette version : 60 tests, dont l’exécution des sept écrans Streamlit sur une API de test, une soumission NLP et l’identité unique de l’ontologie exportée. Les vérifications dans le navigateur ont couvert une question complexe, le dashboard et un ajout réel depuis le formulaire (individu de test retiré après vérification).
