# Utiliser Protégé avec PharmaGraph

Protégé sert à construire et vérifier l’ontologie. FastAPI et RDFLib servent à exécuter l’application et les requêtes SPARQL. Les deux échangent le même graphe en RDF/XML (`.owl`) et Turtle (`.ttl`). Aucun remplacement du module NLP n’est nécessaire.

## Ouvrir le projet

Lancer `Ouvrir-Protege.ps1` depuis PowerShell, ou lancer `tools/protege/Protege-5.6.9/run.bat` puis **File → Open** et sélectionner `data/pharmagraph.owl`.

Le fichier `.owl` contient les classes, propriétés, individus et axiomes du projet, avec un namespace conservé : `https://pharmagraph.example/ontology#`.

**Extension clinique :** le lanceur ouvre désormais `data/pharmagraph-complet.owl` si ce fichier existe. Il contient les 19 classes du projet étendu ; `data/pharmagraph.owl` reste le modèle initial conservé. Le lanceur accepte aussi `-OntologyPath` pour choisir explicitement un fichier.

## Travailler dans Protégé

1. Onglet **Entities**, puis **Classes** : développer `EntiteSante` et sélectionner `Molecule`.
2. Examiner **Object properties** : `aEffetSecondaire`, `aContreIndication`, `etudieDans`, `interagitAvec`, `effetDe`.
3. Examiner **Data properties** : `formule`, `phase`, `participants`, `statut`, `frequence`.
4. Examiner **Individuals** et sélectionner Alpha pour voir ses relations. Le rendu peut afficher son label français « Molécule Alpha ».
5. Pour créer un individu, conserver le namespace PharmaGraph, choisir un identifiant simple sans espace (par exemple `Omega`), son type `Molecule`, un label français et une formule, puis ajouter les relations souhaitées.
6. Dans **Reasoner**, sélectionner **HermiT**, puis **Start reasoner** pour vérifier la cohérence. Les inférences ne sont pas automatiquement matérialisées dans l’application.
7. Enregistrer avec **File → Save** en gardant le format **RDF/XML**. Si un autre format est choisi, le script d’import ci-dessous doit être adapté.

## Appliquer les modifications à l’application

**Arrêter le serveur avant d’importer** (Ctrl+C dans son terminal), pour éviter que son graphe en mémoire n’écrase les changements.

```powershell
python scripts/protege_data.py import data/pharmagraph.owl
python run.py
```

L’import remplace le graphe actif `data/live.ttl`. Si ce fichier existe, une copie est conservée dans `data/backups/`. L’import vérifie le format et le namespace de base, pas toute la cohérence OWL : lancer le raisonneur dans Protégé.

## Voir les modifications de l’application dans Protégé

Après avoir enregistré des données depuis l’interface Web :

```powershell
python scripts/protege_data.py export data/pharmagraph-actualise.owl
```

Ouvrir ce nouveau fichier dans Protégé. L’export refuse d’écraser un fichier existant pour préserver les modifications faites dans l’éditeur : utiliser un autre nom si nécessaire.

Il n’y a pas de synchronisation automatique en temps réel. En soutenance : modification dans Protégé → sauvegarde → import → lancement de l’application → interrogation NLP/SPARQL.
