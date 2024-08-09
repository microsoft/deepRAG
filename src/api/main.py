import uvicorn
from models import Settings
from api import Server

settings: Settings = Settings(_env_file=".env")  # type: ignore
server = Server(settings=settings)
uvicorn.run(app=server, host=settings.api_host, port=settings.api_port)
