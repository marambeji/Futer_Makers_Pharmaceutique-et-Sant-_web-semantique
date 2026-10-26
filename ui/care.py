"""Human-centered pages: welcome, patient dossier and guided consultation."""
from datetime import date, timedelta
import html
import re
import uuid
import pandas as pd
import streamlit as st
from ui.client import request
from ui.theme import illustration, card

def can_write():
    return st.session_state.get('auth_user',{}).get('role') in ('admin','medecin')

def name(value):
    return re.sub(r'\s*\((?:patient )?ficti[fv]e?\)', '', str(value),flags=re.I).strip()

def text(value):
    return html.escape(str(value))

def human_date(value):
    try:
        d=date.fromisoformat(value)
        months=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
        return f'{d.day} {months[d.month-1]} {d.year}'
    except (ValueError,TypeError):return str(value)

def render(view):
    try:
        view()
    except ValueError as error:
        st.error(str(error))
        st.caption('Le dossier n’a pas pu être chargé. Vérifiez que le serveur est lancé, puis actualisez la page.')

def joined(records,empty='Non renseigné'):
    return ', '.join(name(r['label']) for r in records) or empty

def navigate(page,patient=None):
    st.session_state['pending_navigation']=page
    if patient:
        st.session_state['pending_patient']=patient

def start_visit(patient):
    for key in ['care_draft','care_saved','care_step','care_operation']:
        st.session_state.pop(key,None)
    navigate('Parcours de soins',patient)

def patient_selector(key):
    records=request('entities/Patient')
    if not records:
        st.info('Aucun dossier pour le moment. Vous pouvez accueillir un premier patient ci-dessous.')
        return None
    names={r['id']:name(r['label']) for r in records}
    if st.session_state.get(key) not in names:
        preferred=st.session_state.get('selected_patient','Nour')
        st.session_state[key]=preferred if preferred in names else next(iter(names))
    selected=st.selectbox('Choisir un patient',list(names),format_func=lambda value:names[value],key=key)
    st.session_state['selected_patient']=selected
    return selected

def home():
    summary=request('care/overview')
    st.markdown('<div class="welcome-banner"><div><span class="small-label">PRENDRE SOIN, C’EST AUSSI RELIER.</span><h2>La bonne information.<br>Au bon moment.</h2><p>Des dossiers connectés, une équipe réunie et une vision claire de chaque parcours. Retrouvez ici ce qui compte pour votre journée.</p><div class="welcome-note">✧ &nbsp; Votre espace pharmaceutique et clinique</div></div><div class="hero-art">'+illustration()+'</div></div>',unsafe_allow_html=True)
    cols=st.columns(3)
    for col,(key,title) in zip(cols,[('patients','Dossiers patients'),('medecins','Médecins dans l’équipe'),('consultations','Consultations enregistrées')]):
        col.metric(title,summary['counts'][key])
    st.write('')
    main,side=st.columns([1.65,1],gap='large')
    with main:
        with card():
            st.markdown('<div class="small-label">LE PARCOURS GUIDÉ</div>',unsafe_allow_html=True)
            patients=request('entities/Patient')
            patient=next((p for p in patients if p['id']=='Nour'),patients[0] if patients else None)
            if patient:
                details=request('care/patients/'+patient['id'])
                patient_name=name(patient['label']);age=patient['data'].get('age',['—'])[0]
                st.subheader('Faisons le chemin avec '+patient_name+'.')
                st.write(f"{patient_name}, {age} ans, possède déjà un dossier. Retrouvez son équipe, préparez sa prochaine consultation et organisez la suite de son accompagnement.")
                st.caption('Équipe de soins : '+joined(details['doctors']))
                steps=[('01','Comprendre son histoire','Lire le dossier et retrouver les personnes qui l’accompagnent.'),
                       ('02','Préparer la consultation','Choisir le médecin et consigner le motif du rendez-vous.'),
                       ('03','Relier les informations','Enregistrer la consultation et les médicaments sélectionnés.'),
                       ('04','Garder le fil','Planifier un suivi et retrouver le tout dans son historique.')]
                for number,title,description in steps:
                    st.markdown(f'<div class="story-step"><span>{number}</span><div><b>{title}</b><p>{description}</p></div></div>',unsafe_allow_html=True)
                st.button('Ouvrir le dossier de '+patient_name+' →',type='primary',on_click=navigate,args=('Dossiers patients',patient['id']),width='stretch')
            else:
                st.subheader('Tout commence par un premier dossier.')
                st.button('Accueillir un patient →',type='primary',on_click=navigate,args=('Dossiers patients',))
    with side:
        with card():
            st.markdown('<div class="small-label">UNE ACTION, UN POINT DE DÉPART</div>',unsafe_allow_html=True)
            st.subheader('De quoi avez-vous besoin ?')
            st.button('Retrouver un patient',on_click=navigate,args=('Dossiers patients',),width='stretch')
            st.button('Préparer une consultation',on_click=navigate,args=('Parcours de soins',),width='stretch',disabled=not can_write(),help='Réservé aux médecins et administrateurs.')
            st.button('Poser une question sur les dossiers',on_click=navigate,args=('Explorateur IA',),width='stretch')
        with card():
            st.markdown('<div class="small-label">LES PROCHAINS RENDEZ-VOUS</div>',unsafe_allow_html=True)
            for row in summary['appointments']:
                st.markdown('**'+name(row['patient'])+'** · '+human_date(row['date']))
                st.caption(name(row['medecin']))
            if not summary['appointments']:
                st.caption('Aucun rendez-vous à venir. Vous pouvez en planifier un à la fin d’une consultation.')
        st.caption('Espace de démonstration : tous les dossiers et protocoles sont fictifs.')

def new_patient():
    if not can_write():return
    with st.expander('Accueillir un nouveau patient'):
        st.write('Quelques informations pour ouvrir un dossier. Vous pourrez le compléter ensuite.')
        doctors=request('entities/Medecin');hospitals=request('entities/Hopital')
        doctor_names={r['id']:name(r['label']) for r in doctors}
        hospital_names={r['id']:name(r['label']) for r in hospitals}
        if 'welcome_patient_id' not in st.session_state:st.session_state['welcome_patient_id']='Patient_'+uuid.uuid4().hex[:20]
        with st.form('welcome_patient'):
            full_name=st.text_input('Prénom et nom du patient fictif',max_chars=100)
            left,right=st.columns(2)
            age=left.number_input('Âge',min_value=0,max_value=120,value=30,step=1)
            sex=right.selectbox('Sexe',['Non précisé','F','M','Autre'])
            doctor=st.selectbox('Médecin référent (facultatif)',['']+list(doctor_names),format_func=lambda value:doctor_names.get(value,'À renseigner plus tard'))
            hospital=st.selectbox('Établissement (facultatif)',['']+list(hospital_names),format_func=lambda value:hospital_names.get(value,'À renseigner plus tard'))
            submitted=st.form_submit_button('Ouvrir ce dossier',type='primary')
        if submitted:
            try:
                relations={}
                if doctor:relations['suitPar']=[doctor]
                if hospital:relations['accueilliDans']=[hospital]
                identifier=st.session_state['welcome_patient_id']
                request('entities/Patient','POST',{'id':identifier,'label':full_name,'data':{'age':[str(age)],'sexe':[sex]},'relations':relations})
                st.session_state['welcome_patient_id']='Patient_'+uuid.uuid4().hex[:20]
                st.session_state['care_notice']='Le dossier de '+full_name+' est ouvert. Vous pouvez préparer sa première consultation.'
                navigate('Dossiers patients',identifier);st.rerun()
            except ValueError as error:st.error(str(error))

def dossiers():
    selected=patient_selector('dossier_patient')
    new_patient()
    if not selected:return
    dossier=request('care/patients/'+selected)
    patient=dossier['patient'];patient_name=name(patient['label'])
    age=patient['data'].get('age',['Non renseigné'])[0]
    hospitals=joined(dossier['hospitals'],'Établissement non renseigné')
    st.markdown(f'<div class="patient-banner"><div class="avatar">{text(patient_name[:1])}</div><div><span class="small-label">LE DOSSIER DE</span><h2>{text(patient_name)}</h2><p>{text(age)} ans · {text(hospitals)}</p></div></div>',unsafe_allow_html=True)
    left,right=st.columns([2,1])
    left.caption('Ce dossier réunit les informations enregistrées et les liens entre les différents intervenants.')
    right.button('Préparer sa consultation →',type='primary',on_click=start_visit,args=(selected,),width='stretch',disabled=not can_write())
    tabs=st.tabs(['En bref','Consultations & prescriptions','Historique','Médicaments & molécules'])
    with tabs[0]:
        cols=st.columns([1.2,1])
        with cols[0]:
            with card():
                st.subheader('Les personnes qui l’accompagnent')
                for doctor in dossier['doctors']:
                    st.markdown('**'+name(doctor['label'])+'**')
                    st.caption(doctor['specialty']+' · '+joined(doctor['hospitals']))
                if not dossier['doctors']:st.caption('Aucun médecin référent n’a encore été renseigné.')
            with card():
                st.subheader('Ce qui figure dans son dossier')
                st.write('**Maladies renseignées :** '+joined(dossier['conditions'],'Aucune maladie renseignée'))
                st.write('**Assurance :** '+joined(dossier['insurance'],'Aucune assurance renseignée'))
                st.caption('Une information absente du dossier ne signifie pas qu’elle est absente dans la réalité.')
        with cols[1]:
            upcoming=[row for row in dossier['appointments'] if row['date']>=dossier['today'] and row.get('statut')!='Annulé']
            with card():
                st.subheader('Le prochain rendez-vous')
                if upcoming:
                    row=upcoming[0]
                    st.markdown('### '+human_date(row['date']))
                    st.write(name(row['medecin']));st.caption(row.get('statut','Prévu'))
                else:st.caption('Aucun rendez-vous à venir. Le parcours de consultation permet d’en prévoir un.')
            cols2=st.columns(2)
            cols2[0].metric('Consultations',len(dossier['consultations']))
            cols2[1].metric('Prescriptions',len(dossier['prescriptions']))
    with tabs[1]:
        st.subheader('Les consultations')
        for row in dossier['consultations']:
            with card():
                st.markdown('**'+human_date(row['date'])+' · '+name(row['medecin'])+'**')
                if row.get('motif'):st.write(row['motif'])
                st.caption('Maladies renseignées : '+joined(row['diagnoses'],'Non renseignées'))
                if row['treatments']:st.caption('Protocole enregistré : '+joined(row['treatments']))
        if not dossier['consultations']:st.info('Aucune consultation enregistrée pour ce patient.')
        st.subheader('Les prescriptions enregistrées')
        for row in dossier['prescriptions']:
            with card():
                st.markdown('**'+human_date(row['date'])+' · '+name(row['medecin'])+'**')
                st.write(joined(row['medicines']))
                if row.get('duree'):st.caption('Durée enregistrée : '+row['duree']+' jours')
        if not dossier['prescriptions']:st.caption('Aucune prescription enregistrée.')
    with tabs[2]:
        st.subheader('Une histoire que l’on peut retrouver')
        for row in dossier['timeline']:
            title=row['type']+' · '+human_date(row['date'])
            description=name(row['medecin'])
            if row.get('motif'):description+=' · '+row['motif']
            st.markdown(f'<div class="history-event"><div class="history-dot"></div><div><b>{text(title)}</b><p>{text(description)}</p></div></div>',unsafe_allow_html=True)
        if not dossier['timeline']:st.caption('L’historique commencera avec la première consultation.')
    with tabs[3]:
        st.write('Retrouvez les molécules associées aux médicaments du dossier et les informations qui les accompagnent.')
        for med in dossier['medicines']:
            with st.expander(name(med['label'])):
                st.caption('Prise déclarée dans le dossier' if med['declared_taken'] else 'Présent dans une prescription ; la prise effective n’est pas confirmée')
                for molecule in med['molecules']:
                    st.markdown('**Molécule :** '+name(molecule['label']))
                    st.write('Effets secondaires renseignés : '+joined(molecule['effects'],'Aucun renseigné'))
                    st.write('Contre-indications de la molécule : '+joined(molecule['contraindications'],'Aucune renseignée'))
                if not med['molecules']:st.caption('Aucune molécule associée dans le graphe.')
        if not dossier['medicines']:st.caption('Aucun médicament renseigné pour le moment.')
        st.caption('Ces liens décrivent des données fictives. L’application ne détermine pas si un médicament convient au patient.')
    with st.expander('Comment les informations de ce dossier sont-elles reliées ?'):
        st.write('Le patient est relié à ses médecins, aux consultations, puis aux prescriptions. Les mêmes données alimentent le dossier, les recherches et les statistiques.')
        for key,query in dossier['queries'].items():st.code(query,language='sparql')

def set_step(step):st.session_state['care_step']=step

def journey():
    if not can_write():
        st.info('La préparation des consultations est réservée aux médecins et administrateurs.');return
    patient_id=patient_selector('care_patient')
    if not patient_id:
        st.button('Ouvrir un premier dossier',on_click=navigate,args=('Dossiers patients',));return
    dossier=request('care/patients/'+patient_id)
    patient_name=name(dossier['patient']['label'])
    if st.session_state.get('care_draft',{}).get('patient')!=patient_id:
        st.session_state['care_draft']={'patient':patient_id,'doctor':dossier['doctors'][0]['id'] if dossier['doctors'] else '',
            'date':request('care/overview')['today'],'reason':'Consultation de suivi (démonstration)',
            'conditions':[r['id'] for r in dossier['conditions']],'treatment':None,'medicines':[],
            'duration':30,'followup_date':None}
        st.session_state['care_operation']=uuid.uuid4().hex[:24]
        st.session_state['care_step']=0
        st.session_state.pop('care_saved',None)
    draft=st.session_state['care_draft'];operation=st.session_state['care_operation']
    if 'care_saved' in st.session_state:
        result=st.session_state['care_saved']
        st.markdown('<div class="completed-banner"><span class="small-label">LE DOSSIER EST À JOUR</span><h2>La suite du parcours est organisée.</h2><p>La consultation et les informations que vous avez choisies sont maintenant reliées au dossier du patient.</p></div>',unsafe_allow_html=True)
        st.success(result['message'])
        st.write('**Patient :** '+patient_name+' · **Consultation :** '+human_date(draft['date']))
        st.write('**Prescription :** '+('Enregistrée' if result.get('prescription_id') else 'Aucune prescription ajoutée'))
        st.write('**Suivi :** '+(human_date(draft['followup_date']) if draft.get('followup_date') else 'À organiser plus tard'))
        left,right=st.columns(2)
        left.button('Retrouver le dossier et son historique →',type='primary',on_click=navigate,args=('Dossiers patients',patient_id),width='stretch')
        right.button('Commencer une autre consultation',on_click=start_visit,args=(patient_id,),width='stretch')
        with st.expander('Voir ce qui a été enregistré dans le graphe'):
            st.json({k:v for k,v in result.items() if k.endswith('_id')})
            if result.get('sparql'):st.code(result['sparql'],language='sparql')
        return
    step=st.session_state.get('care_step',0)
    titles=['La consultation','La prescription','Le prochain rendez-vous','Relire & enregistrer']
    st.markdown(f'<div class="journey-context"><b>Vous accompagnez {text(patient_name)}</b><span>Étape {step+1} sur 4 · Rien n’est enregistré avant votre validation finale.</span></div>',unsafe_allow_html=True)
    progress=''.join(f'<div class="journey-step {"current" if i==step else "done" if i<step else ""}"><span>{"✓" if i<step else i+1}</span><b>{text(title)}</b></div>' for i,title in enumerate(titles))
    st.markdown('<div class="journey-progress">'+progress+'</div>',unsafe_allow_html=True)
    st.progress((step+1)/4)
    if step==0:
        st.subheader('Préparons la consultation de '+patient_name+'.')
        st.write('Choisissez le médecin et notez ce qui motive cette rencontre. Les informations déjà présentes dans le dossier vous servent de point de départ.')
        doctors=request('entities/Medecin');conditions=request('entities/Maladie')
        doctor_names={r['id']:name(r['label']) for r in doctors}
        condition_names={r['id']:name(r['label']) for r in conditions}
        if not doctors:st.info('Ajoutez d’abord un médecin dans l’atelier sémantique.');return
        with st.form('visit_basics_'+operation):
            doctor=st.selectbox('Avec quel médecin ?',list(doctor_names),index=list(doctor_names).index(draft['doctor']) if draft['doctor'] in doctor_names else 0,format_func=lambda value:doctor_names[value])
            visit_date=st.date_input('Date de la consultation',value=date.fromisoformat(draft['date']))
            reason=st.text_area('Motif de la consultation',value=draft['reason'],max_chars=500,height=90)
            chosen=st.multiselect('Maladies à renseigner pour cette consultation',list(condition_names),default=[v for v in draft['conditions'] if v in condition_names],format_func=lambda value:condition_names[value])
            if st.form_submit_button('Continuer vers la prescription →',type='primary'):
                draft.update(doctor=doctor,date=visit_date.isoformat(),reason=reason,conditions=chosen)
                set_step(1);st.rerun()
    elif step==1:
        st.subheader('Que souhaitez-vous inscrire sur la prescription ?')
        st.write('Vous pouvez ajouter une prescription ou poursuivre sans médicament. Les choix sont enregistrés tels quels ; aucune recommandation médicale n’est générée.')
        medicines=request('entities/Medicament');treatments=request('entities/Traitement')
        med_names={r['id']:name(r['label']) for r in medicines};treatment_names={r['id']:name(r['label']) for r in treatments}
        with st.form('visit_prescription_'+operation):
            meds=st.multiselect('Médicaments à enregistrer',list(med_names),default=[v for v in draft['medicines'] if v in med_names],format_func=lambda value:med_names[value])
            duration=st.number_input('Durée de la prescription, en jours',min_value=1,max_value=365,value=draft['duration'],step=1,help='Utilisée uniquement si vous sélectionnez au moins un médicament.')
            protocol=st.selectbox('Protocole du jeu de démonstration (facultatif)',['']+list(treatment_names),index=(['']+list(treatment_names)).index(draft['treatment']) if draft['treatment'] in treatment_names else 0,format_func=lambda value:treatment_names.get(value,'Aucun protocole'))
            if st.form_submit_button('Continuer vers le suivi →',type='primary'):
                draft.update(medicines=meds,duration=duration,treatment=protocol or None)
                set_step(2);st.rerun()
        st.button('← Revenir à la consultation',on_click=set_step,args=(0,))
    elif step==2:
        st.subheader('Et après cette consultation ?')
        st.write('Un rendez-vous de suivi permet de garder une prochaine étape visible dans le dossier. Vous pouvez aussi l’organiser plus tard.')
        with st.form('visit_followup_'+operation):
            schedule=st.checkbox('Prévoir un rendez-vous de suivi',value=draft.get('followup_date') is not None)
            next_date=st.date_input('Date souhaitée pour le suivi',value=date.fromisoformat(draft['followup_date']) if draft.get('followup_date') else date.fromisoformat(draft['date'])+timedelta(days=30),help='Le rendez-vous sera associé au même patient et au même médecin.')
            if st.form_submit_button('Relire le parcours →',type='primary'):
                if schedule and next_date<=date.fromisoformat(draft['date']):st.error('Choisissez une date de suivi après la consultation.')
                else:
                    draft['followup_date']=next_date.isoformat() if schedule else None
                    set_step(3);st.rerun()
        st.button('← Revenir à la prescription',on_click=set_step,args=(1,))
    else:
        st.subheader('Tout est prêt pour '+patient_name+'.')
        st.write('Relisez les informations. La consultation, la prescription éventuelle et le suivi seront enregistrés ensemble dans le dossier.')
        doctor=request('entities/Medecin/'+draft['doctor'])
        med_names={r['id']:name(r['label']) for r in request('entities/Medicament')}
        condition_names={r['id']:name(r['label']) for r in request('entities/Maladie')}
        with card():
            st.markdown('**La rencontre**')
            st.write(patient_name+' · '+human_date(draft['date'])+' · '+name(doctor['label']))
            st.write(draft['reason'] or 'Aucun motif ajouté')
            st.caption('Maladies renseignées : '+(', '.join(condition_names.get(v,v) for v in draft['conditions']) or 'Aucune'))
            st.divider();st.markdown('**La prescription**')
            st.write(', '.join(med_names.get(v,v) for v in draft['medicines']) or 'Aucune prescription ajoutée')
            if draft['medicines']:st.caption(str(draft['duration'])+' jours · aucune dose médicale renseignée')
            st.divider();st.markdown('**La suite du parcours**')
            st.write('Rendez-vous le '+human_date(draft['followup_date']) if draft.get('followup_date') else 'Le suivi sera organisé plus tard.')
        if st.button('Enregistrer ce parcours dans le dossier',type='primary'):
            try:
                result=request('care/visits','POST',{**draft,'operation_id':operation})
                st.session_state['care_saved']=result
                st.rerun()
            except ValueError as error:st.error(str(error))
        st.button('← Ajuster le suivi',on_click=set_step,args=(2,))
