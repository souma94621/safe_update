from endpoint import app
import uvicorn
from pathlib import Path

DIR = Path(__file__).parent.parent / 'keys'

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="localhost", 
        port=8000, 
        ssl_certfile = DIR / 'server.crt', 
        ssl_keyfile = DIR / 'server.key'
        )