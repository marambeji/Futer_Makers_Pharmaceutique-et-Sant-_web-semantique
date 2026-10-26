"""One shared visual system for authentication and every application page."""
from pathlib import Path
import streamlit as st

ROOT=Path(__file__).resolve().parent

def illustration():
    return (ROOT/'assets/pharma-care.svg').read_text(encoding='utf-8')

def render():
    st.session_state['_pg_card_index']=0
    css=(ROOT/'assets/theme.css').read_text(encoding='utf-8')
    st.markdown('<style>'+css+'</style>',unsafe_allow_html=True)

def card():
    """Give bordered surfaces a stable CSS hook without generated class names."""
    index=st.session_state.get('_pg_card_index',0)
    st.session_state['_pg_card_index']=index+1
    return st.container(border=True,key='pg_card_'+str(index))
