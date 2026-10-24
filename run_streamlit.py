"""Launch the Python UI; the FastAPI backend must be running (python run.py)."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.deps'))
if __name__=='__main__':
    from streamlit.web import cli
    sys.argv=['streamlit','run',str(ROOT/'ui/app.py'),'--global.developmentMode=false','--server.address=127.0.0.1','--server.port=8501','--browser.gatherUsageStats=false','--server.headless=true']
    raise SystemExit(cli.main())
