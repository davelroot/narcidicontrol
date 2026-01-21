from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.schemas.licenca import (
    LicencaCreate, LicencaResponse, LicencaUpdate,
    AssinaturaCreate, AssinaturaResponse, AssinaturaUpdate,
    BloqueioCreate, BloqueioResponse,
    PagamentoCreate, PagamentoResponse
)
from app.services.licenca_service import LicencaService, AssinaturaService
from app.utils.security import get_current_active_user, require_permission

router = APIRouter(prefix="/licencas", tags=["licencas"])

@router.post("/", response_model=LicencaResponse, status_code=status.HTTP_201_CREATED)
@require_permission("licencas", "manage")
async def criar_licenca(
    licenca_data: LicencaCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cria uma nova licença"""
    try:
        licenca = LicencaService.criar_licenca(db, licenca_data)
        return licenca
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/ativar/{chave_licenca}")
async def ativar_licenca(
    chave_licenca: str,
    maquina_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Ativa uma licença (pública para máquinas)"""
    sucesso = LicencaService.ativar_licenca(db, chave_licenca, maquina_id)
    if not sucesso:
        raise HTTPException(status_code=400, detail="Falha ao ativar licença")
    return {"message": "Licença ativada com sucesso"}

@router.get("/verificar/{chave_licenca}", response_model=LicencaResponse)
async def verificar_licenca(
    chave_licenca: str,
    db: Session = Depends(get_db)
):
    """Verifica status de uma licença (pública)"""
    licenca = LicencaService.verificar_licenca(db, chave_licenca)
    if not licenca:
        raise HTTPException(status_code=404, detail="Licença não encontrada")
    return licenca

@router.get("/", response_model=List[LicencaResponse])
@require_permission("licencas", "view")
async def listar_licencas(
    cliente_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista licenças"""
    from app.models.licenca import Licenca
    
    query = db.query(Licenca)
    
    if cliente_id:
        query = query.filter(Licenca.cliente_id == cliente_id)
    if status:
        query = query.filter(Licenca.status == status)
    
    licencas = query.offset(skip).limit(limit).all()
    return licencas

@router.post("/{licenca_id}/renovar")
@require_permission("licencas", "manage")
async def renovar_licenca(
    licenca_id: int,
    meses: int = Query(1, ge=1, le=24),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Renova uma licença"""
    sucesso = LicencaService.renovar_licenca(db, licenca_id, meses)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Licença não encontrada")
    return {"message": f"Licença renovada por {meses} meses"}

@router.post("/{licenca_id}/bloquear")
@require_permission("licencas", "manage")
async def bloquear_licenca(
    licenca_id: int,
    motivo: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bloqueia uma licença"""
    sucesso = LicencaService.bloquear_licenca(db, licenca_id, motivo)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Licença não encontrada")
    return {"message": "Licença bloqueada com sucesso"}

@router.get("/expirando")
@require_permission("dashboard", "view")
async def licencas_expirando(
    dias: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista licenças prestes a expirar"""
    licencas = LicencaService.get_licencas_expirando(db, dias)
    
    return [
        {
            "id": l.id,
            "chave_licenca": l.chave_licenca,
            "cliente_id": l.cliente_id,
            "data_expiracao": l.data_expiracao,
            "dias_restantes": (l.data_expiracao - datetime.utcnow()).days if l.data_expiracao else None,
            "status": l.status
        }
        for l in licencas
    ]

@router.post("/assinaturas/", response_model=AssinaturaResponse, status_code=status.HTTP_201_CREATED)
@require_permission("assinaturas", "manage")
async def criar_assinatura(
    assinatura_data: AssinaturaCreate,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cria uma nova assinatura"""
    try:
        assinatura = AssinaturaService.criar_assinatura(db, assinatura_data)
        return assinatura
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/assinaturas/{assinatura_id}/renovar")
@require_permission("assinaturas", "manage")
async def renovar_assinatura(
    assinatura_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Renova uma assinatura"""
    sucesso = AssinaturaService.renovar_assinatura(db, assinatura_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    return {"message": "Assinatura renovada com sucesso"}

@router.get("/assinaturas/renovacoes-pendentes")
@require_permission("dashboard", "view")
async def renovacoes_pendentes(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista assinaturas que precisam ser renovadas"""
    assinaturas = AssinaturaService.verificar_renovacoes(db)
    
    return [
        {
            "id": a.id,
            "cliente_id": a.cliente_id,
            "plano": a.plano,
            "data_fim": a.data_fim,
            "dias_restantes": (a.data_fim - datetime.utcnow()).days if a.data_fim else None,
            "valor": a.valor
        }
        for a in assinaturas
    ]

@router.post("/bloqueios/", response_model=BloqueioResponse, status_code=status.HTTP_201_CREATED)
@require_permission("bloqueios", "manage")
async def criar_bloqueio(
    bloqueio_data: BloqueioCreate,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cria um novo registro de bloqueio"""
    from app.models.licenca import Bloqueio
    
    bloqueio = Bloqueio(
        cliente_id=bloqueio_data.cliente_id,
        maquina_id=bloqueio_data.maquina_id,
        motivo=bloqueio_data.motivo,
        tipo=bloqueio_data.tipo,
        severidade=bloqueio_data.severidade
    )
    
    db.add(bloqueio)
    db.commit()
    db.refresh(bloqueio)
    
    return bloqueio

@router.get("/bloqueios/", response_model=List[BloqueioResponse])
@require_permission("bloqueios", "view")
async def listar_bloqueios(
    cliente_id: Optional[int] = None,
    ativos: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista bloqueios"""
    from app.models.licenca import Bloqueio
    
    query = db.query(Bloqueio)
    
    if cliente_id:
        query = query.filter(Bloqueio.cliente_id == cliente_id)
    if ativos:
        query = query.filter(Bloqueio.data_desbloqueio.is_(None))
    
    bloqueios = query.order_by(Bloqueio.created_at.desc()).offset(skip).limit(limit).all()
    return bloqueios
