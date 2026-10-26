"""Local accounts, scrypt passwords, opaque sessions and role authorization."""
from contextlib import contextmanager, closing
from pathlib import Path
import hashlib
import hmac
import re
import secrets
import sqlite3
import time

ROLES={'admin':'Administrateur','medecin':'Médecin','chercheur':'Chercheur'}

class AuthError(Exception):
    def __init__(self,status,message):
        self.status=status
        super().__init__(message)

def password_hash(password):
    salt=secrets.token_bytes(16)
    derived=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1,dklen=64)
    return 'scrypt$'+salt.hex()+'$'+derived.hex()

def password_matches(password,encoded):
    _,salt,expected=encoded.split('$')
    actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=64)
    return hmac.compare_digest(actual.hex(),expected)

class Accounts:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL, role TEXT NOT NULL,
              active INTEGER NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
              token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts (
              email TEXT PRIMARY KEY, failures INTEGER NOT NULL, first_at INTEGER NOT NULL);
            ''')
        self.dummy_hash=password_hash(secrets.token_urlsafe(32))

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path,timeout=15)) as db:
            db.row_factory=sqlite3.Row
            with db:yield db

    def public(self,user):
        return {k:user[k] for k in ['id','name','email','role','active','created_at']}

    def initialized(self):
        with self.connection() as db:
            return bool(db.execute("SELECT 1 FROM users WHERE role='admin' AND active=1 LIMIT 1").fetchone())

    def register(self,name,email,password,role):
        if role=='admin':raise AuthError(403,'Le rôle administrateur ne peut pas être choisi à l’inscription.')
        return self._create(name,email,password,role)

    def create_admin(self,name,email,password):
        """Local setup only; never exposed as a public API route."""
        return self._create(name,email,password,'admin',administrator=True)

    def _create(self,name,email,password,role,administrator=False):
        name=name.strip();email=email.strip().lower()
        if not 2<=len(name)<=100:raise AuthError(422,'Indiquez un nom entre 2 et 100 caractères.')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>200:
            raise AuthError(422,'Indiquez une adresse e-mail valide.')
        if not 10<=len(password)<=128:raise AuthError(422,'Le mot de passe doit contenir entre 10 et 128 caractères.')
        if role not in ROLES:raise AuthError(422,'Rôle inconnu.')
        encoded=password_hash(password)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if administrator and db.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
                raise AuthError(409,'Le compte administrateur est déjà configuré.')
            if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
                raise AuthError(409,'Un compte existe déjà avec cette adresse e-mail.')
            user_id=secrets.token_hex(12)
            db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)',(user_id,name,email,encoded,role,int(administrator),int(time.time())))
            user=self.public(db.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone())
        return {'user':user,'requires_approval':not administrator,
                'message':'Votre espace administrateur est prêt. Connectez-vous pour continuer.' if administrator else 'Votre demande a été enregistrée. Un administrateur doit activer votre compte.'}

    def login(self,email,password):
        email=email.strip().lower();now=int(time.time())
        with self.connection() as db:
            attempt=db.execute('SELECT * FROM attempts WHERE email=?',(email,)).fetchone()
            if attempt and attempt['failures']>=5 and now-attempt['first_at']<900:
                raise AuthError(429,'Trop de tentatives. Réessayez dans 15 minutes.')
            user=db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        valid=password_matches(password,user['password_hash'] if user else self.dummy_hash)
        if not valid or not user:
            with self.connection() as db:
                if not attempt or now-attempt['first_at']>=900:
                    db.execute('INSERT OR REPLACE INTO attempts VALUES (?,?,?)',(email,1,now))
                else:db.execute('UPDATE attempts SET failures=failures+1 WHERE email=?',(email,))
            raise AuthError(401,'Adresse e-mail ou mot de passe incorrect.')
        if not user['active']:raise AuthError(403,'Votre compte attend son activation par un administrateur.')
        token=secrets.token_urlsafe(32);expires=now+8*3600
        with self.connection() as db:
            db.execute('DELETE FROM attempts WHERE email=?',(email,))
            db.execute('DELETE FROM sessions WHERE expires_at<=?',(now,))
            db.execute('INSERT INTO sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],expires))
        return {'token':token,'expires_at':expires,'user':self.public(user)}

    def authenticate(self,header):
        if not header or not header.startswith('Bearer '):raise AuthError(401,'Connectez-vous pour accéder à votre espace.')
        token=header[7:]
        if not token or len(token)>200:raise AuthError(401,'Session invalide. Connectez-vous à nouveau.')
        with self.connection() as db:
            user=db.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1',
                            (hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
        if not user:raise AuthError(401,'Votre session a expiré ou a été révoquée. Connectez-vous à nouveau.')
        return self.public(user)

    def logout(self,header):
        token=header[7:] if header else ''
        with self.connection() as db:db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))

    def users(self):
        with self.connection() as db:return [self.public(row) for row in db.execute('SELECT * FROM users ORDER BY created_at,name')]

    def update(self,actor,user_id,role,active):
        if role not in ROLES:raise AuthError(422,'Rôle inconnu.')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
            if not current:raise AuthError(404,'Compte introuvable.')
            if current['id']==actor['id'] and (not active or role!='admin'):
                raise AuthError(422,'Vous ne pouvez pas retirer vos propres droits administrateur.')
            if current['role']=='admin' and current['active'] and (not active or role!='admin'):
                remaining=db.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1 AND id!=?",(user_id,)).fetchone()[0]
                if not remaining:raise AuthError(422,'Conservez au moins un administrateur actif.')
            changed=current['role']!=role or bool(current['active'])!=active
            db.execute('UPDATE users SET role=?,active=? WHERE id=?',(role,int(active),user_id))
            if changed:db.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
            return self.public(db.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone())

def authorize(user,method,path):
    role=user['role']
    if path.startswith('/api/auth/users') and role!='admin':raise AuthError(403,'Cet espace est réservé à l’administrateur.')
    if role=='admin':return
    if method=='GET' or path in ('/api/ask','/api/sparql','/api/auth/logout'):return
    clinical=path=='/api/care/visits' or path.startswith('/api/entities/Patient') or path.startswith('/api/entities/Consultation') or path.startswith('/api/entities/Prescription') or path.startswith('/api/entities/RendezVous')
    if role=='medecin' and clinical:return
    raise AuthError(403,'Votre rôle ne permet pas cette modification.')
