from fastapi import FastAPI
from app.events.maquina_events import setup_maquina_events
from app.events.licenca_events import setup_licenca_events
from app.events.upload_events import setup_upload_events

def setup_events(app: FastAPI):
    """Configura todos os eventos do sistema"""
    setup_maquina_events(app)
    setup_licenca_events(app)
    setup_upload_events(app)
