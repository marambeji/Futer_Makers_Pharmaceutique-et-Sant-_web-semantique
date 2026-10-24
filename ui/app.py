from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'.deps'))
import json
import html
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from ui.client import request
from ui import care

st.set_page_config(page_title='PharmaGraph · Le fil des soins',page_icon='✳',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
.block-container{padding-top:2.6rem;max-width:1450px}h1{letter-spacing:-1.4px;font-weight:750}h2{letter-spacing:-.6px}
[data-testid="stSidebar"]{border-right:1px solid #dce5d9;background:white}
[data-testid="stMetric"]{border:1px solid #dce5d9;border-radius:12px;padding:18px;background:white}
[data-testid="stForm"]{background:white;border-radius:12px;border:1px solid #dce5d9}
.kicker{color:#648570;font-size:11px;letter-spacing:2px;font-weight:700}.hero{background:#e9f1e5;border:1px solid #d8e4d1;border-radius:14px;padding:22px 26px;margin:8px 0 24px}
.hero b{font-size:20px}.hero p{color:#6a7d6f;margin:8px 0 0;font-size:13px}
.welcome-banner{background:#e8efe2;border:1px solid #d9e4d2;border-radius:18px;padding:32px 38px;margin:8px 0 25px;position:relative;overflow:hidden}
.welcome-banner:after{content:'✳';position:absolute;right:24px;top:10px;font-size:170px;line-height:1;color:#d2dfc6;opacity:.5;pointer-events:none}
.welcome-banner h2{font-size:32px;max-width:620px;position:relative;z-index:1;margin:12px 0;font-weight:750;letter-spacing:-1px}
.welcome-banner p{font-size:15px;line-height:1.8;max-width:680px;color:#5d7563;position:relative;z-index:1}.welcome-note{font-size:12px;margin-top:24px;color:#758769}
.small-label{font-size:10px;letter-spacing:1.8px;font-weight:700;color:#6a8264}
.story-step{display:flex;gap:16px;margin:21px 0;align-items:flex-start}.story-step>span{display:flex;align-items:center;justify-content:center;flex-shrink:0;width:32px;height:32px;border-radius:50%;background:#eff4e9;border:1px solid #dde7d5;font-size:11px;color:#59815e}.story-step b{font-size:14px;font-weight:650}.story-step p{font-size:13px;color:#7b8779;margin:5px 0;line-height:1.6}
.patient-banner{display:flex;align-items:center;gap:22px;border-radius:16px;padding:24px 28px;background:#eef3e9;border:1px solid #dce5d6;margin:24px 0 14px}.patient-banner h2{margin:4px 0;font-size:28px}.patient-banner p{margin:0;font-size:13px;color:#6c7b65}.avatar{width:64px;height:64px;display:flex;align-items:center;justify-content:center;background:#d6e4cb;color:#46633d;font-size:28px;border-radius:50%;flex-shrink:0}
.history-event{position:relative;display:flex;gap:18px;padding:0 0 28px;margin-left:8px;border-left:1px solid #dbe4d5}.history-dot{width:11px;height:11px;flex-shrink:0;background:#87a779;border:3px solid #edf3e8;border-radius:50%;margin-left:-6px;margin-top:5px}.history-event p{font-size:13px;line-height:1.7;color:#75816e;margin:5px 0}.history-event b{font-size:14px}
.journey-context{display:flex;gap:14px;justify-content:space-between;align-items:center;background:#edf2e8;border:1px solid #dce5d5;border-radius:10px;padding:15px 20px;margin:20px 0}.journey-context b{font-size:14px}.journey-context span{color:#73806b;font-size:11px}.journey-progress{display:flex;gap:12px;margin:26px 0 10px}.journey-step{display:flex;align-items:center;gap:9px;flex:1;color:#9aa18f}.journey-step span{width:27px;height:27px;display:flex;align-items:center;justify-content:center;border-radius:50%;border:1px solid #d9e0d2;font-size:11px;flex-shrink:0}.journey-step b{font-size:11px;font-weight:500}.journey-step.current{color:#235b42}.journey-step.current span{background:#235b42;color:white;border-color:#235b42}.journey-step.done{color:#728d5e}.completed-banner{background:#e8f0e1;border-radius:16px;padding:28px 32px;border:1px solid #d6e3cb;margin:20px 0}.completed-banner h2{margin:12px 0}.completed-banner p{color:#6f7f65;line-height:1.8;font-size:14px}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px}button[kind="primary"]{border-radius:8px}h3{font-size:20px!important}p{line-height:1.7}
@media(max-width:700px){.welcome-banner{padding:23px}.welcome-banner h2{font-size:26px}.welcome-banner:after{right:4px;font-size:120px;opacity:.3}.journey-context{align-items:flex-start;flex-direction:column;gap:6px}.journey-progress{gap:5px}.journey-step{flex-direction:column;align-items:flex-start;gap:7px}.journey-step b{font-size:10px}.patient-banner{padding:18px;gap:14px}.patient-banner h2{font-size:24px}}
</style>''',unsafe_allow_html=True)

def result_table(result,key):
    st.caption(f"{len(result['rows'])} résultat(s)"+(' · limite de 1 000 lignes atteinte' if result.get('truncated') else ''))
    if result['rows']:
        readable=pd.DataFrame(result['rows'],columns=result['columns'])
        if 'nom' in readable.columns and 'resultat' in readable.columns:readable=readable.drop(columns=['resultat'])
        labels={'nom':'Nom','age':'Âge','maladieNom':'Maladie','nombreMedecins':'Médecins consultés','medecin':'Médecin','patient':'Patient','medicament':'Médicament','participants':'Participants','phase':'Phase','nombre':'Nombre','date':'Date','sexe':'Sexe'}
        readable=readable.rename(columns=labels)
        for column in readable.columns:
            if readable[column].dtype=='object':readable[column]=readable[column].map(lambda value:care.name(value) if isinstance(value,str) else value)
        st.dataframe(readable,width='stretch',hide_index=True)
        st.download_button('Télécharger les résultats CSV',pd.DataFrame(result['rows']).to_csv(index=False).encode('utf-8-sig'),key+'.csv','text/csv',key=key+'_csv')
    else: st.info('Aucun résultat pour ces critères dans le graphe.')

def show_query(query,title='Requête SPARQL exécutée'):
    with st.expander(title): st.code(query,language='sparql')

pending=st.session_state.pop('pending_navigation',None)
if pending:st.session_state['main_navigation']=pending
pending_patient=st.session_state.pop('pending_patient',None)
if pending_patient:
    for key in ['selected_patient','dossier_patient','care_patient']:st.session_state[key]=pending_patient
main_pages=['Accueil','Dossiers patients','Parcours de soins','Explorateur IA','Tableau de bord','Atelier sémantique']
nav_labels={'Accueil':'Accueil','Dossiers patients':'Les patients','Parcours de soins':'Nouvelle consultation','Explorateur IA':'Poser une question','Tableau de bord':'Vue d’ensemble','Atelier sémantique':'Atelier sémantique'}
with st.sidebar:
    st.markdown('## ✳ PharmaGraph')
    st.caption('LE FIL DES SOINS')
    st.divider()
    page=st.radio('VOTRE ESPACE',main_pages,key='main_navigation',format_func=lambda value:nav_labels[value],label_visibility='visible')
    if page=='Atelier sémantique':
        st.caption('Pour comprendre le modèle et préparer la soutenance.')
        page=st.selectbox('Choisir un outil',['Ontologie','Console SPARQL','Données & CRUD','Relations','Qualité des données'])
    st.divider()
    st.caption('Dossiers fictifs · Espace pédagogique')
    with st.expander('À propos du projet'):
        st.caption('Les informations sont reliées par une ontologie. Le moteur de recherche utilise NLTK et SPARQL, sans service LLM externe.')
        st.link_button('Interface pharmaceutique initiale','http://127.0.0.1:8000')

st.markdown('<div class="kicker">PHARMAGRAPH · LE FIL DES SOINS</div>',unsafe_allow_html=True)
st.title({'Accueil':'Bienvenue dans votre espace.','Dossiers patients':'Derrière chaque dossier, une personne.','Parcours de soins':'Préparons la suite du parcours.','Explorateur IA':'Une question sur vos dossiers ?','Tableau de bord':'L’activité, en un regard.','Données & CRUD':'Gérer les données du projet.','Relations':'Comprendre et ajuster les liens.','Ontologie':'Le modèle qui relie les informations.','Console SPARQL':'Explorer les données en profondeur.','Qualité des données':'Vérifier la cohérence des dossiers.'}[page])
st.caption('Démonstration universitaire · Données et identités entièrement fictives')
notice=st.session_state.pop('care_notice',None)
if notice:st.success(notice)

try:
    schema=request('schema')
    by_class={c['id']:c for c in schema['classes']}
    examples=request('examples')
except ValueError as error:
    st.error(str(error));st.stop()

if page=='Accueil':
    care.render(care.home)
elif page=='Dossiers patients':
    care.render(care.dossiers)
elif page=='Parcours de soins':
    care.render(care.journey)
elif page=='Explorateur IA':
    left,right=st.columns([2.2,1])
    with left:
        st.markdown('<div class="hero"><b>Retrouvez une information, avec vos mots.</b><p>Qui accompagne un patient ? Quels médicaments figurent dans les prescriptions ? Posez votre question et retrouvez une réponse fondée sur les dossiers enregistrés.</p></div>',unsafe_allow_html=True)
        choice=st.selectbox('Exemples de questions',['Écrire ma question']+examples['questions'])
        if choice!='Écrire ma question':
            st.session_state['question_text']=choice
        with st.form('ask'):
            question=st.text_area('Votre question',key='question_text',placeholder='Quels patients sont suivis par le docteur Ahmed ?',height=110,max_chars=500)
            submitted=st.form_submit_button('Explorer le graphe ↗',type='primary')
        if submitted:
            try:
                st.session_state['answer']=request('ask','POST',{'question':question})
                st.session_state.pop('ask_error',None)
            except ValueError as error:
                st.session_state.pop('answer',None);st.session_state['ask_error']=str(error)
        if st.session_state.get('ask_error'):st.error(st.session_state['ask_error'])
        if 'answer' in st.session_state:
            answer=st.session_state['answer']
            st.subheader('Voici ce que les dossiers nous indiquent')
            st.success(answer['answer'])
            result_table(answer,'nlp')
            st.write(answer['explanation'])
            show_query(answer['sparql'],'Comprendre la traduction et consulter SPARQL')
            with st.expander('Trace du traitement NLP'):
                st.json({key:answer.get(key) for key in ['intent','tokens','stems','entities','schema_properties','method']})
    with right:
        with st.container(border=True):
            st.markdown('### Pour commencer simplement')
            st.write('Essayez « Affiche les patients suivis par le docteur Ahmed ». Vous retrouverez les personnes qui lui sont associées dans les dossiers.')
            st.caption('Utilisez les noms présents dans le projet. Si une question n’est pas comprise, choisissez un exemple et adaptez-le.')
            st.button('Revenir aux dossiers patients →',on_click=care.navigate,args=('Dossiers patients',),width='stretch')
            with st.expander('Comment la réponse est-elle trouvée ?'):
                st.write('Les mots et entités sont reconnus avec NLTK et le lexique de l’ontologie. Des règles composent une requête SPARQL, qui est validée puis exécutée sur les données locales.')
                st.caption('Ce moteur comprend les formulations prévues par sa grammaire ; il ne comprend pas tout le langage libre.')
elif page=='Tableau de bord':
    with st.expander('Choisir les patients et la période à observer',expanded=True):
        cols=st.columns(3)
        ages=cols[0].slider('Âge des patients',0,120,(0,120))
        sex=cols[1].selectbox('Sexe',['Tous','F','M','Autre','Non précisé'])
        use_dates=cols[2].checkbox('Filtrer les consultations / prescriptions par date')
        dates=cols[2].date_input('Période',(date(2026,1,1),date.today()),disabled=not use_dates)
    params={'min_age':ages[0],'max_age':ages[1],'sex':'' if sex=='Tous' else sex}
    if use_dates and isinstance(dates,tuple) and len(dates)==2:params.update(start=dates[0].isoformat(),end=dates[1].isoformat())
    try: stats=request('dashboard',params=params)
    except ValueError as error:st.error(str(error));st.stop()
    columns=st.columns(4)
    for column,(name,value) in zip(columns,stats['metrics'].items()):column.metric({'patients':'Patients','medecins':'Médecins référents','consultations':'Consultations','prescriptions':'Prescriptions'}[name],value)
    st.caption(stats['scope'])
    charts=[('maladies','Patients par maladie','nom','bar'),('par_medecin','Consultations par médecin','nom','bar'),('medicaments','Médicaments les plus prescrits','nom','bar'),('sexes','Répartition par sexe','sexe','pie'),('ages','Distribution des âges','age','bar'),('periode','Consultations au fil du temps','date','line')]
    columns=st.columns(2)
    for index,(key,title,x,kind) in enumerate(charts):
        with columns[index%2]:
            with st.container(border=True):
                st.subheader(title)
                data=stats['datasets'][key]
                if data['rows']:
                    df=pd.DataFrame(data['rows']);df['nombre']=pd.to_numeric(df['nombre'])
                    if x=='age':df[x]=pd.to_numeric(df[x])
                    if kind=='pie':fig=px.pie(df,names=x,values='nombre',hole=.65,color_discrete_sequence=['#176653','#88aa7b','#c5d7b5'])
                    elif kind=='line':fig=px.line(df,x=x,y='nombre',markers=True,color_discrete_sequence=['#176653'])
                    else:fig=px.bar(df,x=x,y='nombre',color_discrete_sequence=['#57896c'])
                    fig.update_layout(height=310,margin=dict(l=10,r=10,t=15,b=10),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig,width='stretch',key='chart_'+key)
                else:st.info('Aucune donnée pour les filtres choisis.')
                show_query(data['sparql'])
    with st.expander('Coûts : somme, moyenne, minimum, maximum'):
        result_table(stats['datasets']['couts'],'costs');st.code(stats['datasets']['couts']['sparql'],language='sparql')
elif page=='Données & CRUD':
    cls=st.selectbox('Classe à gérer',list(by_class),format_func=lambda key:f"{by_class[key]['label']} · {by_class[key]['count']} individu(s)",index=list(by_class).index('Patient'))
    metadata=by_class[cls];records=request('entities/'+cls)
    search=st.text_input('Rechercher dans les libellés et les valeurs')
    visible=[r for r in records if search.casefold() in json.dumps(r,ensure_ascii=False).casefold()]
    st.dataframe(pd.DataFrame([{'Identifiant':r['id'],'Libellé':r['label'],**{k:', '.join(v) for k,v in r['data'].items()},**{k:', '.join(v) for k,v in r['relations'].items()}} for r in visible]),width='stretch',hide_index=True)
    left,right=st.columns([2,1])
    with left:
        mode=st.radio('Action',['Ajouter','Modifier'],horizontal=True)
        existing=None
        if mode=='Modifier':
            if not records:st.info('Cette classe ne contient pas encore d’individu.');st.stop()
            chosen=st.selectbox('Individu à modifier',[r['id'] for r in records],format_func=lambda key:next(r['label'] for r in records if r['id']==key))
            existing=next(r for r in records if r['id']==chosen)
        form_key=cls+'_'+(existing['id'] if existing else 'new')
        # Prepare compatible targets before entering the form: choices come from OWL ranges.
        targets={f['id']:request('entities/'+f['range']) for f in metadata['fields'] if f['kind']=='object' and f['range'] in by_class}
        with st.form('entity_'+form_key):
            identity=st.text_input('Identifiant sans espace',value=existing['id'] if existing else '',disabled=existing is not None,max_chars=60)
            name=st.text_input('Libellé',value=existing['label'] if existing else '',max_chars=150)
            data={};relations={}
            for field in metadata['fields']:
                key=field['id'];caption=key+(' *' if field['required'] else '')+' · '+field['range']
                if field['kind']=='data':
                    current=existing['data'].get(key,[]) if existing else []
                    raw=st.text_input(caption,value=' | '.join(current),help='Pour plusieurs valeurs : séparer avec |. Dates au format AAAA-MM-JJ.')
                    if raw.strip():data[key]=[v.strip() for v in raw.split('|')]
                else:
                    options={r['id']:r['label'] for r in targets.get(key,[])}
                    defaults=[v for v in (existing['relations'].get(key,[]) if existing else []) if v in options]
                    if field['multiple']:
                        selected=st.multiselect(caption,list(options),default=defaults,format_func=lambda value,opts=options:opts[value])
                    else:
                        selected_value=st.selectbox(caption,['']+list(options),index=(['']+list(options)).index(defaults[0]) if defaults else 0,format_func=lambda value,opts=options:opts.get(value,'— Aucune relation —'))
                        selected=[selected_value] if selected_value else []
                    if selected:relations[key]=selected
            save=st.form_submit_button('Enregistrer dans le graphe RDF',type='primary')
        if save:
            try:
                body={'id':identity,'label':name,'data':data,'relations':relations}
                result=request('entities/'+cls+('/'+identity if existing else ''),'PUT' if existing else 'POST',body)
                st.success('Individu enregistré. Le catalogue sera actualisé au prochain rafraîchissement.')
                st.session_state['last_mutation']=result['sparql']
            except ValueError as error:st.error(str(error))
    with right:
        with st.container(border=True):
            st.subheader('Supprimer un individu')
            if records:
                doomed=st.selectbox('Individu à supprimer',[r['id'] for r in records],key='delete_'+cls)
                confirm=st.checkbox('Confirmer la suppression et le retrait des liens non obligatoires',key='confirm_'+cls)
                if st.button('Supprimer',disabled=not confirm):
                    try:
                        result=request('entities/'+cls+'/'+doomed,'DELETE');st.session_state['last_mutation']=result['sparql'];st.success('Individu supprimé.');st.rerun()
                    except ValueError as error:st.error(str(error))
            st.caption('Une relation obligatoire entrante bloque la suppression. Les types, cardinalités et références sont contrôlés côté serveur.')
    if st.button('Actualiser le catalogue'):st.rerun()
    if 'last_mutation' in st.session_state:show_query(st.session_state['last_mutation'],'Dernière écriture SPARQL')
elif page=='Relations':
    st.write('Ajouter ou retirer une relation sans supprimer les individus.')
    cls=st.selectbox('Classe source',list(by_class),index=list(by_class).index('Patient'))
    sources=request('entities/'+cls)
    fields=[f for f in by_class[cls]['fields'] if f['kind']=='object']
    if not sources or not fields:st.info('Cette classe nécessite des individus et des propriétés objet.');st.stop()
    source=st.selectbox('Individu source',[r['id'] for r in sources],format_func=lambda k:next(r['label'] for r in sources if r['id']==k))
    prop=st.selectbox('Relation',[f['id'] for f in fields])
    field=next(f for f in fields if f['id']==prop)
    targets=request('entities/'+field['range'])
    if not targets:st.info('Aucune cible compatible. Créez d’abord un individu de type '+field['range']);st.stop()
    target=st.selectbox('Individu cible',[r['id'] for r in targets],format_func=lambda k:next(r['label'] for r in targets if r['id']==k))
    current=next(r for r in sources if r['id']==source)['relations'].get(prop,[])
    st.caption('Relations actuelles : '+(', '.join(current) or 'aucune'))
    action=st.radio('Opération',['Ajouter la relation','Retirer la relation'],horizontal=True)
    if st.button('Appliquer la relation',type='primary'):
        try:
            result=request('relations','POST' if action.startswith('Ajouter') else 'DELETE',{'source':source,'predicate':prop,'target':target})
            st.success('Relation mise à jour.');show_query(result['sparql'])
        except ValueError as error:st.error(str(error))
elif page=='Ontologie':
    columns=st.columns(3)
    columns[0].metric('Classes OWL',len(by_class))
    all_fields={f['id']:f for c in by_class.values() for f in c['fields']}
    columns[1].metric('Propriétés objet',sum(f['kind']=='object' for f in all_fields.values()))
    columns[2].metric('Propriétés de données',sum(f['kind']=='data' for f in all_fields.values()))
    cls=st.selectbox('Explorer une classe',list(by_class),index=list(by_class).index('Patient'))
    st.write('Parents : '+', '.join(by_class[cls]['parents']))
    st.dataframe(pd.DataFrame(by_class[cls]['fields']),width='stretch',hide_index=True)
    mode=st.radio('Vue du graphe',['Schéma des classes','Voisinage d’un individu'],horizontal=True)
    nodes=[];edges=[]
    if mode=='Schéma des classes':
        for c in by_class.values():
            for field in c['fields']:
                if field['kind']=='object':edges.append((c['id'],field['range'],field['id']))
        nodes=list(by_class)
    else:
        records=request('entities/'+cls)
        if records:
            selected=st.selectbox('Individu',[r['id'] for r in records])
            entity=next(r for r in records if r['id']==selected)
            edges=[(selected,target,prop) for prop,targets in entity['relations'].items() for target in targets]
            nodes=sorted({selected}|{t for _,t,_ in edges})
    if nodes:
        import math
        positions={node:(math.cos(2*math.pi*i/len(nodes)),math.sin(2*math.pi*i/len(nodes))) for i,node in enumerate(nodes)}
        fig=go.Figure()
        annotations=[]
        for s,t,p in edges:
            if s not in positions or t not in positions:continue
            a,b=positions[s],positions[t]
            fig.add_trace(go.Scatter(x=[a[0],b[0]],y=[a[1],b[1]],mode='lines',line=dict(color='#c6d9c4',width=1),text=[s+' → '+p+' → '+t]*2,hoverinfo='text',showlegend=False))
        fig.add_trace(go.Scatter(x=[positions[n][0] for n in nodes],y=[positions[n][1] for n in nodes],mode='markers+text',text=nodes,textposition='top center',marker=dict(size=18,color='#337e63'),hoverinfo='text',showlegend=False))
        fig.update_layout(height=560,margin=dict(t=30,b=30,l=70,r=70),xaxis=dict(visible=False),yaxis=dict(visible=False),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig,width='stretch')
        st.caption('Survoler une arête pour lire la relation orientée source → propriété → cible.')
        if edges:st.dataframe(pd.DataFrame(edges,columns=['Source','Cible','Relation'])[['Source','Relation','Cible']],hide_index=True,width='stretch')
    st.download_button('Exporter OWL pour Protégé',request('ontology?format=xml'),'pharmagraph-complet.owl','application/rdf+xml')
    st.download_button('Exporter Turtle',request('ontology'),'pharmagraph-complet.ttl','text/turtle')
    st.info('Protégé reste l’éditeur OWL et le raisonneur. Les exports comprennent le graphe actif complet. L’import depuis Protégé s’effectue avec scripts/protege_data.py, serveur arrêté.')
elif page=='Console SPARQL':
    chosen=st.selectbox('Bibliothèque de requêtes',[q['id'] for q in examples['queries']],format_func=lambda value:next(q['title'] for q in examples['queries'] if q['id']==value))
    example=next(q for q in examples['queries'] if q['id']==chosen)
    st.caption(example['features'])
    with st.form('console'):
        query=st.text_area('Requête SELECT ou ASK',value=example['query'],height=280,key='query_'+chosen)
        submitted=st.form_submit_button('Exécuter SPARQL',type='primary')
    if submitted:
        try:
            result=request('sparql','POST',{'query':query});result_table(result,'console')
        except ValueError as error:st.error(str(error))
    st.caption('SELECT / ASK locaux ; SERVICE et FROM sont refusés. Les écritures passent par le CRUD validé.')
elif page=='Qualité des données':
    st.markdown('<div class="hero"><b>Un audit explicable, basé sur le schéma.</b><p>Repérez les incohérences des données et la règle qui les révèle.</p></div>',unsafe_allow_html=True)
    result=request('quality')
    st.metric('Anomalies détectées',result['count'])
    if result['issues']:st.dataframe(pd.DataFrame(result['issues']),hide_index=True,width='stretch')
    else:st.success('Aucune anomalie détectée par les règles implémentées.')
    st.info(result['method'])
st.divider()
st.caption('PharmaGraph · Le fil des soins · Les informations affichées proviennent des dossiers du projet.')
