from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import asyncio

from app.database.session import get_db
from app.schemas.maquina import (
    MaquinaCreate, MaquinaResponse, MaquinaUpdate,
    MaquinaMetricaCreate, MaquinaMetricaResponse,
    HeartbeatRequest, MachineDashboard
)
from app.services.maquina_service import MaquinaService
from app.utils.security import get_current_active_user, require_permission
from app.events.maquina_events import manager as maquina_manager

router = APIRouter(prefix="/maquinas", tags=["maquinas"])

@router.post("/", response_model=MaquinaResponse, status_code=status.HTTP_201_CREATED)
@require_permission("maquinas", "manage")
async def registrar_maquina(
    maquina_data: MaquinaCreate,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Registra uma nova máquina"""
    try:
        maquina = MaquinaService.registrar_maquina(db, maquina_data)
        return maquina
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/heartbeat")
async def receber_heartbeat(
    heartbeat: HeartbeatRequest,
    db: Session = Depends(get_db)
):
    """Recebe heartbeat de uma máquina (pública para máquinas)"""
    maquina = MaquinaService.processar_heartbeat(db, heartbeat)
    if not maquina:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    
    # Notificar via WebSocket
    await maquina_manager.broadcast_heartbeat(maquina.id, heartbeat)
    
    return {"status": "ok", "maquina_id": maquina.id}

@router.get("/", response_model=List[MaquinaResponse])
@require_permission("maquinas", "view")
async def listar_maquinas(
    cliente_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista máquinas"""
    query = db.query(Maquina)
    
    if cliente_id:
        query = query.filter(Maquina.cliente_id == cliente_id)
    if status:
        query = query.filter(Maquina.status == status)
    
    maquinas = query.offset(skip).limit(limit).all()
    return maquinas

@router.get("/{maquina_id}", response_model=MaquinaResponse)
@require_permission("maquinas", "view")
async def obter_maquina(
    maquina_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtém uma máquina específica"""
    maquina = db.query(Maquina).filter(Maquina.id == maquina_id).first()
    if not maquina:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    return maquina

@router.post("/{maquina_id}/bloquear")
@require_permission("maquinas", "manage")
async def bloquear_maquina(
    maquina_id: int,
    motivo: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bloqueia uma máquina remotamente"""
    sucesso = MaquinaService.bloquear_maquina(db, maquina_id, motivo)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    
    # Notificar bloqueio via WebSocket
    await maquina_manager.broadcast_bloqueio(maquina_id, motivo)
    
    return {"message": "Máquina bloqueada com sucesso"}

@router.post("/{maquina_id}/desbloquear")
@require_permission("maquinas", "manage")
async def desbloquear_maquina(
    maquina_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Desbloqueia uma máquina"""
    sucesso = MaquinaService.desbloquear_maquina(db, maquina_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    
    # Notificar desbloqueio via WebSocket
    await maquina_manager.broadcast_desbloqueio(maquina_id)
    
    return {"message": "Máquina desbloqueada com sucesso"}

@router.get("/{maquina_id}/metricas", response_model=List[MaquinaMetricaResponse])
@require_permission("maquinas", "view")
async def obter_metricas_maquina(
    maquina_id: int,
    limite: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtém métricas recentes de uma máquina"""
    metricas = MaquinaService.get_metricas_recentes(db, maquina_id, limite)
    return metricas

@router.get("/{maquina_id}/dashboard")
@require_permission("dashboard", "view")
async def dashboard_maquina(
    maquina_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Dashboard de uma máquina específica"""
    maquina = db.query(Maquina).filter(Maquina.id == maquina_id).first()
    if not maquina:
        raise HTTPException(status_code=404, detail="Máquina não encontrada")
    
    metricas = MaquinaService.get_metricas_recentes(db, maquina_id, 100)
    
    return {
        "maquina": maquina,
        "metricas_recentes": metricas,
        "estatisticas": {
            "uptime": maquina.tempo_atividade,
            "status": maquina.status,
            "ultima_conexao": maquina.ultima_conexao
        }
    }

@router.get("/cliente/{cliente_id}/dashboard", response_model=MachineDashboard)
@require_permission("dashboard", "view")
async def dashboard_cliente(
    cliente_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Dashboard de todas as máquinas de um cliente"""
    estatisticas = MaquinaService.get_estatisticas_maquinas(db, cliente_id)
    maquinas = MaquinaService.get_maquinas_por_cliente(db, cliente_id)
    
    # Atividade das últimas 24 horas
    from datetime import datetime, timedelta
    limite = datetime.utcnow() - timedelta(hours=24)
    
    atividade = []
    for hora in range(24):
        hora_inicio = limite + timedelta(hours=hora)
        hora_fim = hora_inicio + timedelta(hours=1)
        
        # Contar máquinas online nessa hora
        online_count = sum(
            1 for m in maquinas 
            if m.ultima_conexao and hora_inicio <= m.ultima_conexao <= hora_fim
        )
        
        atividade.append({
            "hora": hora_inicio.strftime("%H:00"),
            "online": online_count,
            "total": len(maquinas)
        })
    
    return MachineDashboard(
        total_maquinas=estatisticas["total"],
        online=estatisticas["status"].get("online", 0),
        offline=estatisticas["status"].get("offline", 0),
        bloqueadas=estatisticas["status"].get("bloqueada", 0),
        uso_cpu_medio=estatisticas["metricas_medias"]["cpu"],
        uso_memoria_medio=estatisticas["metricas_medias"]["memoria"],
        atividade_24h=atividade
    )

@router.websocket("/ws/{cliente_id}")
async def websocket_maquinas(websocket: WebSocket, cliente_id: int, db: Session = Depends(get_db)):
    """WebSocket para atualizações em tempo real das máquinas"""
    await maquina_manager.connect(websocket, cliente_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Processar mensagens do cliente (se necessário)
            if message.get("type") == "subscribe":
                maquina_id = message.get("maquina_id")
                if maquina_id:
                    await maquina_manager.subscribe(websocket, maquina_id)
                    
    except WebSocketDisconnect:
        maquina_manager.disconnect(websocket, cliente_id)
