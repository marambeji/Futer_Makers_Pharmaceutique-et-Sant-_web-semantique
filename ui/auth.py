"""Login, registration, account activation and session-aware navigation."""
import html
import streamlit as st
from ui.client import request
from ui.theme import illustration

ROLES={'admin':'Administrateur','medecin':'Médecin','chercheur':'Chercheur'}
DESCRIPTIONS={'admin':'Gestion des comptes, du modèle et de toutes les données de l’espace.',
              'medecin':'Dossiers patients, consultations, prescriptions et rendez-vous de suivi.',
              'chercheur':'Consultation des données, recherche sémantique et analyse en lecture seule.'}

def logout():
    try:request('auth/logout','POST')
    except ValueError:pass
    st.session_state.clear()

def login_screen(initialized):
    st.markdown('''<style>[data-testid="stSidebar"]{display:none!important}[data-testid="stHeader"]{display:none!important}.block-container{max-width:1240px;padding-top:2.7rem!important;padding-bottom:2rem}.stApp{background:#f3f7f3}</style>''',unsafe_allow_html=True)
    left,right=st.columns([1.1,1],gap='large')
    with left:
        st.markdown('<div class="auth-story"><div class="auth-brand"><span>✳</span> PharmaGraph</div><span class="auth-tag">LA SANTÉ SE CONSTRUIT ENSEMBLE</span><h1>Des connaissances reliées.<br>Des parcours mieux suivis.</h1><p>Un espace commun pour accompagner les patients, explorer les molécules et donner du sens aux données de santé.</p><div class="hero-art">'+illustration()+'</div><div class="auth-footer">✧ &nbsp; Dossiers &nbsp; · &nbsp; Pharmaceutique &nbsp; · &nbsp; Recherche</div></div>',unsafe_allow_html=True)
    with right:
        st.markdown('<div class="auth-heading"><span class="small-label">VOTRE ESPACE PHARMAGRAPH</span><h2>Heureux de vous retrouver.</h2><p>Connectez-vous ou rejoignez l’équipe en tant que médecin ou chercheur.</p></div>',unsafe_allow_html=True)
        if not initialized:
            st.info('Les inscriptions sont ouvertes aux médecins et chercheurs. Votre compte sera activé par l’administrateur de l’espace.')
        labels=['Se connecter','Créer un compte'] if initialized else ['Créer un compte','Se connecter']
        tabs=st.tabs(labels)
        with tabs[labels.index('Se connecter')]:
            with st.form('login_form'):
                email=st.text_input('Adresse e-mail',placeholder='vous@exemple.tn',key='login_email')
                password=st.text_input('Mot de passe',type='password',placeholder='Votre mot de passe',key='login_password')
                submitted=st.form_submit_button('Se connecter à mon espace →',type='primary',width='stretch')
            if submitted:
                try:
                    session=request('auth/login','POST',{'email':email,'password':password})
                    st.session_state['auth_token']=session['token'];st.session_state['auth_user']=session['user']
                    st.rerun()
                except ValueError as error:st.error(str(error))
            st.caption('Votre espace et vos actions s’adaptent au rôle attribué à votre compte.')
        with tabs[labels.index('Créer un compte')]:
            with st.form('registration_form'):
                full_name=st.text_input('Votre nom complet',placeholder='Prénom et nom',max_chars=100)
                reg_email=st.text_input('Votre adresse e-mail',placeholder='vous@exemple.tn',max_chars=200)
                role=st.selectbox('Votre rôle',['medecin','chercheur'],format_func=lambda value:ROLES[value])
                reg_password=st.text_input('Choisir un mot de passe',type='password',help='Au moins 10 caractères, au maximum 128.')
                confirm=st.text_input('Confirmer le mot de passe',type='password')
                accepted=st.checkbox('Je comprends que cet espace utilise des données fictives pour un projet universitaire.')
                registered=st.form_submit_button('Créer mon compte →',type='primary',width='stretch')
            st.markdown('<div class="auth-role-info">'+html.escape(DESCRIPTIONS[role])+'</div>',unsafe_allow_html=True)
            st.caption('Les nouveaux comptes sont activés par un administrateur avant le premier accès.')
            if registered:
                if not accepted:st.error('Veuillez confirmer le contexte pédagogique de cet espace.')
                elif reg_password!=confirm:st.error('Les deux mots de passe ne correspondent pas.')
                else:
                    try:
                        result=request('auth/register','POST',{'name':full_name,'email':reg_email,'password':reg_password,'role':role})
                        st.success(result['message'])
                        st.info('Ouvrez l’onglet « Se connecter » pour accéder à votre espace.' if not result['requires_approval'] else 'Votre administrateur retrouvera votre demande dans « Mon équipe ».')
                    except ValueError as error:st.error(str(error))
        st.markdown('<div class="auth-trust">✧ &nbsp; Espace local · Accès par rôle · Données pédagogiques</div>',unsafe_allow_html=True)

def require_login():
    if st.session_state.get('auth_token'):
        try:
            user=request('auth/me')
            st.session_state['auth_user']=user
            return user
        except ValueError as error:
            for key in ['auth_token','auth_user']:st.session_state.pop(key,None)
            st.warning(str(error))
    try:status=request('auth/status')
    except ValueError as error:st.error(str(error));st.stop()
    login_screen(status['initialized'])
    st.stop()

def account_menu(user):
    initial=html.escape(user['name'][:1].upper())
    st.markdown('<div class="account-card"><div class="account-avatar">'+initial+'</div><div><b>'+html.escape(user['name'])+'</b><small>'+ROLES[user['role']]+'</small></div></div>',unsafe_allow_html=True)
    st.button('Se déconnecter',on_click=logout,width='stretch',key='sign_out')

def team():
    st.write('Gérez les demandes d’inscription et les accès de votre équipe depuis un seul endroit.')
    notice=st.session_state.pop('team_notice',None)
    if notice:st.success(notice)
    users=request('auth/users')
    pending=[u for u in users if not u['active']]
    cols=st.columns(3)
    cols[0].metric('Membres de l’équipe',len(users))
    cols[1].metric('Comptes actifs',len(users)-len(pending))
    cols[2].metric('Demandes en attente',len(pending))
    st.write('')
    left,right=st.columns([1.3,1],gap='large')
    with left:
        st.subheader('Les membres')
        search_col,status_col=st.columns([1.4,1])
        search=search_col.text_input('Rechercher un membre',placeholder='Nom ou adresse e-mail',key='team_search')
        status=status_col.selectbox('État du compte',['Tous les comptes','En attente','Actifs'],key='team_status')
        filtered=[u for u in users if search.casefold() in (u['name']+' '+u['email']).casefold()
                  and (status=='Tous les comptes' or bool(u['active'])==(status=='Actifs'))]
        st.caption(str(len(filtered))+' membre(s) affiché(s)')
        if not filtered:
            st.info('Aucun membre ne correspond à ces critères.')
            return
        ids=[u['id'] for u in filtered]
        if st.session_state.get('team_selected') not in ids:st.session_state['team_selected']=ids[0]
        selected=st.selectbox('Membre à gérer',ids,format_func=lambda value:next(u['name']+' · '+u['email'] for u in filtered if u['id']==value),key='team_selected')
        for user in filtered:
            active=bool(user['active'])
            badge='Actif' if active else 'En attente'
            selected_class=' selected' if user['id']==selected else ''
            st.markdown('<div class="member-card'+selected_class+'"><div class="account-avatar">'+html.escape(user['name'][:1].upper())+'</div><div class="member-info"><b>'+html.escape(user['name'])+'</b><small>'+html.escape(user['email'])+' · '+ROLES[user['role']]+'</small></div><span class="member-status'+('' if active else ' pending')+'">'+badge+'</span></div>',unsafe_allow_html=True)
    with right:
        st.subheader('Gérer les accès')
        user=next(u for u in filtered if u['id']==selected)
        self_account=user['id']==st.session_state.get('auth_user',{}).get('id')
        with st.form('account_'+user['id']):
            st.markdown('**'+html.escape(user['name'])+'**')
            st.caption(user['email'])
            role=st.selectbox('Rôle',list(ROLES),index=list(ROLES).index(user['role']),format_func=lambda value:ROLES[value],key='role_'+user['id'],disabled=self_account)
            active=st.checkbox('Autoriser l’accès',value=bool(user['active']),key='active_'+user['id'],disabled=self_account)
            st.caption('Votre compte administrateur conserve ses accès.' if self_account else 'Un changement de rôle ou une désactivation ferme les sessions de ce membre.')
            saved=st.form_submit_button('Enregistrer les accès',type='primary',width='stretch',disabled=self_account)
        if saved:
            try:
                request('auth/users/'+user['id'],'PATCH',{'role':role,'active':active})
                st.session_state['team_notice']='Les accès de '+user['name']+' ont été mis à jour.'
                st.rerun()
            except ValueError as error:st.error(str(error))
