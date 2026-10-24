# Une démonstration qui raconte un parcours

L’application s’appelle **PharmaGraph — Le fil des soins**. Son point de départ est une personne et son histoire. Les classes, les relations et SPARQL permettent de retrouver et relier les informations au bon moment.

Tous les patients, médicaments et protocoles sont fictifs. Les actions ci-dessous enregistrent des données de démonstration ; elles ne constituent pas une prise en charge médicale.

## Le personnage et le contexte

Dans le jeu initial, **Nour a 67 ans**. Son dossier est rattaché à l’Hôpital Carthage. Elle est suivie par le docteur Ahmed et le docteur Leïla. Deux consultations et une prescription permettent déjà de retrouver une partie de son parcours.

Vous jouez le rôle d’une personne qui prépare et consigne la prochaine consultation. Votre objectif : comprendre l’existant, ajouter une rencontre cohérente et organiser le suivi. Le même patient reste sélectionné d’une étape à l’autre.

## 1. Commencer par l’accueil

Ouvrir http://127.0.0.1:8501. La page d’accueil donne trois points de départ : retrouver un dossier, préparer une consultation ou poser une question. Les compteurs et les rendez-vous sont issus des données réelles du projet.

Le bloc « Faisons le chemin avec Nour » présente les quatre étapes. Cliquer sur **Ouvrir le dossier de Nour**.

Phrase possible à l’oral :

> « Nous allons suivre le parcours de Nour. Avant d’ajouter une consultation, je souhaite retrouver les personnes qui l’accompagnent et les informations déjà enregistrées. »

## 2. Lire son dossier

L’onglet **En bref** présente l’équipe de soins, les maladies renseignées, l’établissement et le prochain rendez-vous. **Consultations & prescriptions** présente les rencontres et les prescriptions datées. **Historique** rassemble ces événements dans une chronologie. **Médicaments & molécules** relie le parcours de soins au sujet pharmaceutique du projet.

Une prescription ne prouve pas que le médicament est effectivement pris : la fiche distingue les médicaments déclarés comme pris et ceux présents seulement dans une prescription. Les contre-indications affichées sont celles des molécules du jeu fictif, sans conclusion automatique sur le patient.

Cliquer sur **Préparer sa consultation**.

## 3. Préparer la consultation

Choisir le docteur Ahmed, une date et un motif, par exemple « Consultation de suivi — démonstration du projet ». Retenir Diabète parmi les maladies à renseigner pour cette consultation. Cliquer sur **Continuer vers la prescription**.

À ce stade, il s’agit d’un brouillon. Rien n’est enregistré dans l’ontologie.

## 4. Inscrire la prescription choisie

Pour l’exemple universitaire, sélectionner **Médicament Alpha**, une durée de 30 jours et, facultativement, **Protocole A (fictif)**. Il est aussi possible de continuer sans médicament. L’application ne propose pas de recommandation ni de dose : elle consigne les choix de l’utilisateur.

Cliquer sur **Continuer vers le suivi**.

## 5. Prévoir la prochaine rencontre

Cocher **Prévoir un rendez-vous de suivi** et choisir une date après la consultation. Le patient et le médecin sont conservés : aucune nécessité de les ressaisir.

Cliquer sur **Relire le parcours**.

## 6. Relire et enregistrer ensemble

Le récapitulatif montre la personne, la date, le médecin, le motif, les médicaments et le suivi. Il est possible de revenir aux étapes précédentes pour corriger les informations.

Cliquer sur **Enregistrer ce parcours dans le dossier**. Le serveur prépare et valide tous les éléments avant une sauvegarde unique :

- une Consultation reliée à Nour et Ahmed ;
- une Prescription éventuelle, reliée à cette consultation et aux médicaments ;
- un RendezVous éventuel, relié au même patient et au même médecin ;
- les liens de suivi et de maladie renseignés.

Si une cible est invalide, aucun enregistrement partiel n’est conservé. Si une requête identique est renvoyée, l’identifiant d’opération évite de créer une seconde consultation.

## 7. Retrouver le résultat dans le dossier

Cliquer sur **Retrouver le dossier et son historique**. La nouvelle consultation, la prescription et le rendez-vous apparaissent dans le même dossier. Les anciennes informations sont conservées.

Phrase possible à l’oral :

> « Le dossier raconte maintenant la suite du parcours. La consultation, la prescription et le rendez-vous ne sont pas trois fiches isolées : ils sont reliés au même patient et à la même équipe. »

## 8. Poser une question utile

Dans **Poser une question**, saisir :

> « Affiche les patients suivis par le docteur Ahmed. »

Puis une question plus complexe :

> « Quels patients ont consulté plusieurs médecins pour une même maladie ? »

La première question explore une relation de suivi. La seconde croise consultations, patients, médecins et maladies, puis regroupe et compte les médecins distincts. Le résultat vient des données enregistrées. La requête générée et la trace NLP sont consultables sans encombrer le parcours principal.

## 9. Voir l’effet sur l’activité

Ouvrir **Vue d’ensemble**. Les consultations et prescriptions alimentent les statistiques SPARQL. Les filtres d’âge, de sexe et de période permettent de retrouver une population ou une activité particulière. Les nombres ne sont pas codés en dur.

## 10. Expliquer le Web sémantique à la soutenance

Ouvrir **Atelier sémantique**, puis **Ontologie** ou **Console SPARQL**. Ces outils restent disponibles à côté du parcours métier : exploration du modèle, requêtes avancées, gestion des données, relations et audit de cohérence.

Exporter le graphe actif en OWL et l’ouvrir dans Protégé pour montrer les mêmes liens. Le fichier OWL exporté avant la démonstration ne se met pas à jour automatiquement : exporter à nouveau les données après la consultation.

Phrase possible à l’oral :

> « Les écrans suivent une histoire humaine ; l’ontologie donne une structure commune à cette histoire. Chaque information peut être retrouvée par ses relations, interrogée avec SPARQL et expliquée depuis les résultats. »

## Accueillir un autre patient

Dans **Les patients**, ouvrir **Accueillir un nouveau patient**. Renseigner un nom fictif, un âge et, si souhaité, un médecin référent et un établissement. L’identifiant est généré automatiquement. Le nouveau dossier s’ouvre ensuite et permet de commencer le même parcours.
