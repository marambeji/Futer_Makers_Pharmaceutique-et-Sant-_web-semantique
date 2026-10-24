import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / '.deps'))
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
    import uvicorn
    uvicorn.run('backend.app:app', host='127.0.0.1', port=int(os.getenv('PHARMAGRAPH_PORT','8000')))
