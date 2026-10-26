# PharmaGraph — identité visuelle et accès par rôle

L’interface conserve Streamlit et l’API FastAPI. Le thème commun utilise un vert profond, une palette menthe, des cartes blanches, une typographie plus lisible et une illustration SVG pharmaceutique locale. Les dossiers, le parcours guidé, les tableaux de bord et les outils sémantiques utilisent les mêmes couleurs, espacements, formulaires et boutons.

Le style est centralisé dans `ui/assets/theme.css`, chargé par `ui/theme.py`. Les boutons simples et les boutons de formulaire ont les mêmes contrastes ; les états désactivés et les focus clavier restent identifiables. Sur petit écran, le panneau de présentation se réduit pour donner la priorité au formulaire. La page **Mon équipe** rassemble recherche, filtre d’état, liste de membres et un seul éditeur d’accès ; la liste se rafraîchit après l’enregistrement.

## Premier démarrage

1. Dans un terminal du projet, lancer `python setup_admin.py` pour configurer le premier **Administrateur**. Le mot de passe est saisi sans être affiché.
2. Lancer `python run.py`, puis `python run_streamlit.py` dans un second terminal.
3. Ouvrir http://127.0.0.1:8501.
4. Ouvrir « Se connecter » et utiliser les identifiants administrateur choisis.

Il n’existe aucun compte ni mot de passe prédéfini. L’inscription publique propose uniquement **Médecin** et **Chercheur**, même avant la configuration locale. L’API refuse toujours une inscription au rôle Administrateur. Le script local ne crée qu’un administrateur initial ; les droits supplémentaires se gèrent depuis « Mon équipe ».

## Inscrire et activer les membres

Les inscriptions choisissent **Médecin** ou **Chercheur**. Le compte reste en attente tant qu’un administrateur ne l’a pas activé.

Depuis le compte administrateur : ouvrir **Mon équipe**, vérifier le compte, attribuer son rôle et cocher **Autoriser l’accès**, puis enregistrer. Le membre peut alors se connecter. Un administrateur peut aussi attribuer le rôle Administrateur à un compte existant. Il ne peut pas retirer ses propres droits ni désactiver le dernier administrateur actif.

## Droits effectifs

| Fonction | Administrateur | Médecin | Chercheur |
|---|---|---|---|
| Lire les dossiers synthétiques et les résultats | Oui | Oui | Oui |
| Poser des questions et exécuter SELECT/ASK | Oui | Oui | Oui |
| Voir les statistiques | Oui | Oui | Oui |
| Ajouter / modifier les patients, consultations, prescriptions et rendez-vous | Oui | Oui | Non |
| Enregistrer le parcours guidé | Oui | Oui | Non |
| Modifier les molécules et les autres classes de référence | Oui | Non | Non |
| Ajouter ou retirer des relations avec l’éditeur générique | Oui | Non | Non |
| Explorer et exporter l’ontologie | Oui | Via l’API | Oui |
| Gérer les comptes et leurs droits | Oui | Non | Non |

Le rôle Médecin dispose des écrans de soins ; le Chercheur dispose d’écrans en lecture seule et des outils d’analyse. Le contrôle n’est pas limité à la navigation : l’API retourne **401** sans session valide et **403** si le rôle ne permet pas l’opération. Les écritures sont toujours validées contre le modèle RDF.

Les dossiers restent entièrement fictifs. Le rôle Chercheur consulte le jeu de démonstration complet ; cette version n’implémente ni anonymisation de dossiers réels ni filtrage par médecin référent. Ne pas y importer de données médicales personnelles.

## Comptes et sessions

- Les comptes sont enregistrés dans `data/accounts.sqlite3`, séparément de l’ontologie.
- Les mots de passe sont dérivés avec `hashlib.scrypt` et un sel aléatoire propre à chaque compte.
- Les sessions utilisent des jetons opaques aléatoires. Seule leur empreinte SHA-256 est stockée côté serveur.
- Une session expire après huit heures ; la déconnexion la révoque immédiatement.
- Un changement de rôle ou une désactivation révoque les sessions du compte concerné.
- Cinq échecs de connexion pour une adresse provoquent un délai de quinze minutes.
- Le fichier des comptes, les sessions, `.env` et les secrets sont exclus de Git.

L’interface Streamlit conserve le jeton dans la session serveur Streamlit. L’ancienne interface HTML utilise `sessionStorage` pour sa propre session et présente également un écran de connexion. Aucune session ne passe dans les paramètres d’URL.

## API et documentation

Routes publiques : `/api/auth/status`, `/api/auth/register`, `/api/auth/login`.

Routes de session : `/api/auth/me`, `/api/auth/logout`. Administration : `/api/auth/users` et `/api/auth/users/{id}`.

Dans http://127.0.0.1:8000/docs, se connecter avec `POST /api/auth/login`, copier le jeton retourné puis cliquer sur **Authorize** pour tester les routes protégées. Ne pas publier le jeton.

## Limites de cette version locale

Cette authentification est destinée à l’application universitaire locale. Il n’y a pas d’envoi d’e-mail, de vérification d’adresse, de récupération automatique du mot de passe ni de MFA. Les comptes professionnels sont vérifiés manuellement par l’administrateur. Un hébergement public demanderait notamment HTTPS, une configuration de déploiement adaptée et une politique d’accès plus fine.

## Sources de référence

Le stockage des mots de passe s’appuie sur [la documentation officielle de hashlib.scrypt](https://docs.python.org/3/library/hashlib.html#hashlib.scrypt). Le contrôle des requêtes utilise le mécanisme de [middleware de FastAPI](https://fastapi.tiangolo.com/tutorial/middleware/).
