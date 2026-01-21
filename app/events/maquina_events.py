from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class MaquinaConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.maquina_subscriptions: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, cliente_id: int):
        """Conecta um cliente ao WebSocket"""
        await websocket.accept()
        
        if cliente_id not in self.active_connections:
            self.active_connections[cliente_id] = []
        
        self.active_connections[cliente_id].append(websocket)
        logger.info(f"Cliente {cliente_id} conectado via WebSocket")
    
    def disconnect(self, websocket: WebSocket, cliente_id: int):
        """Desconecta um cliente"""
        if cliente_id in self.active_connections:
            self.active_connections[cliente_id].remove(websocket)
            if not self.active_connections[cliente_id]:
                del self.active_connections[cliente_id]
        
        # Remover de todas as assinaturas
        for maquina_id in list(self.maquina_subscriptions.keys()):
            self.maquina_subscriptions[maquina_id].discard(websocket)
            if not self.maquina_subscriptions[maquina_id]:
                del self.maquina_subscriptions[maquina_id]
    
    async def subscribe(self, websocket: WebSocket, maquina_id: int):
        """Assina uma máquina específica"""
        if maquina_id not in self.maquina_subscriptions:
            self.maquina_subscriptions[maquina_id] = set()
        
        self.maquina_subscriptions[maquina_id].add(websocket)
        
        await websocket.send_json({
            "type": "subscription_confirmed",
            "maquina_id": maquina_id
        })
    
    async def broadcast_heartbeat(self, maquina_id: int, heartbeat_data: dict):
        """Transmite heartbeat para assinantes"""
        if maquina_id not in self.maquina_subscriptions:
            return
        
        message = {
            "type": "heartbeat",
            "maquina_id": maquina_id,
            "data": heartbeat_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        disconnected = set()
        for websocket in self.maquina_subscriptions[maquina_id]:
            try:
                await websocket.send_json(message)
            except:
                disconnected.add(websocket)
        
        # Remover conexões desconectadas
        for websocket in disconnected:
            self.maquina_subscriptions[maquina_id].discard(websocket)
    
    async def broadcast_bloqueio(self, maquina_id: int, motivo: str):
        """Transmite notificação de bloqueio"""
        if maquina_id not in self.maquina_subscriptions:
            return
        
        message = {
            "type": "bloqueio",
            "maquina_id": maquina_id,
            "motivo": motivo,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        disconnected = set()
        for websocket in self.maquina_subscriptions[maquina_id]:
            try:
                await websocket.send_json(message)
            except:
                disconnected.add(websocket)
        
        for websocket in disconnected:
            self.maquina_subscriptions[maquina_id].discard(websocket)
    
    async def broadcast_desbloqueio(self, maquina_id: int):
        """Transmite notificação de desbloqueio"""
        if maquina_id not in self.maquina_subscriptions:
            return
        
        message = {
            "type": "desbloqueio",
            "maquina_id": maquina_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        disconnected = set()
        for websocket in self.maquina_subscriptions[maquina_id]:
            try:
                await websocket.send_json(message)
            except:
                disconnected.add(websocket)
        
        for websocket in disconnected:
            self.maquina_subscriptions[maquina_id].discard(websocket)

manager = MaquinaConnectionManager()

def setup_maquina_events(app: FastAPI):
    """Configura eventos de máquina"""
    @app.on_event("startup")
    async def startup_event():
        logger.info("Eventos de máquina configurados")
