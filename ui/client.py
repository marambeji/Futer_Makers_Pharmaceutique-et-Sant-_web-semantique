"""All UI operations go through the backend HTTP API, including charts and CRUD."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/'.env')

def request(path,method='GET',body=None,params=None):
    base=os.getenv('PHARMAGRAPH_API_URL','http://127.0.0.1:8000').rstrip('/')
    try:
        import streamlit as st
        token=st.session_state.get('auth_token')
        headers={'Authorization':'Bearer '+token} if token else {}
        response=httpx.request(method,base+'/api/'+path,json=body,params=params,headers=headers,timeout=45)
    except httpx.RequestError as exc:
        raise ValueError('API indisponible. Lancez d’abord « python run.py » dans un terminal.') from exc
    if response.status_code>=400:
        if response.status_code==401 and path not in ('auth/login','auth/register'):
            for key in ('auth_token','auth_user'):st.session_state.pop(key,None)
        try: detail=response.json().get('detail',response.text)
        except ValueError: detail=response.text
        raise ValueError(str(detail))
    if path.startswith('ontology'): return response.content
    return response.json()
