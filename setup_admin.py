"""Configure the initial administrator locally, outside public registration."""
import getpass
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.deps'))

def main():
    from dotenv import load_dotenv
    from backend.auth import Accounts, AuthError
    load_dotenv(ROOT/'.env')
    accounts=Accounts(os.getenv('PHARMAGRAPH_AUTH_DB',str(ROOT/'data/accounts.sqlite3')))
    if accounts.initialized():
        print('Un administrateur est déjà configuré. Connectez-vous à votre espace.')
        return 0
    print('Configuration locale du premier administrateur PharmaGraph')
    name=input('Nom complet : ')
    email=input('Adresse e-mail : ')
    password=getpass.getpass('Mot de passe (10 à 128 caractères) : ')
    if password!=getpass.getpass('Confirmer le mot de passe : '):
        print('Les mots de passe ne correspondent pas.')
        return 1
    try:result=accounts.create_admin(name,email,password)
    except AuthError as error:
        print(str(error))
        return 1
    print(result['message'])
    return 0

if __name__=='__main__':raise SystemExit(main())
