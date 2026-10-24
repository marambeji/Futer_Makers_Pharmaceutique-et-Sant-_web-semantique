"""All UI operations go through the backend HTTP API, including charts and CRUD."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/'.env')

def request(path,method='GET',body=None,params=None):
    base=os.getenv('PHARMAGRAPH_API_URL','http://127.0.0.1:8000').rstrip('/')
    try:
        response=httpx.request(method,base+'/api/'+path,json=body,params=params,timeout=45)
    except httpx.RequestError as exc:
        raise ValueError('API indisponible. Lancez d’abord « python run.py » dans un terminal.') from exc
    if response.status_code>=400:
        try: detail=response.json().get('detail',response.text)
        except ValueError: detail=response.text
        raise ValueError(str(detail))
    if path.startswith('ontology'): return response.content
    return response.json()
