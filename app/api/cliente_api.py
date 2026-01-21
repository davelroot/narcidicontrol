
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db
from app.schemas.cliente import (
    ClienteCreate, ClienteResponse, ClienteUpdate,
    PerfilClienteCreate, PerfilClienteResponse,
    PermissaoClienteCreate, PermissaoClienteResponse
)
from app.services.cliente_service import ClienteService
from app.utils.security import get_current_active_user, require_permission

router = APIRouter(prefix="/clientes", tags=["clientes"])

@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
async def criar_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db)
):
    """Cria um novo cliente"""
    try:
        cliente = ClienteService.criar_cliente(db, cliente_data)
        return cliente
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/", response_model=List[ClienteResponse])
@require_permission("clientes", "view")
async def listar_clientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista todos os clientes"""
    clientes = ClienteService.listar_clientes(db, skip, limit, tipo, status)
    return clientes

@router.get("/{cliente_id}", response_model=ClienteResponse)
@require_permission("clientes", "view")
async def obter_cliente(
    cliente_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtém um cliente específico"""
    cliente = ClienteService.obter_cliente(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente

@router.put("/{cliente_id}", response_model=ClienteResponse)
@require_permission("clientes", "manage")
async def atualizar_cliente(
    cliente_id: int,
    cliente_data: ClienteUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Atualiza dados do cliente"""
    cliente = ClienteService.atualizar_cliente(db, cliente_id, cliente_data)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente

@router.post("/{cliente_id}/bloquear")
@require_permission("clientes", "manage")
async def bloquear_cliente(
    cliente_id: int,
    motivo: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bloqueia um cliente"""
    sucesso = ClienteService.bloquear_cliente(db, cliente_id, motivo)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"message": "Cliente bloqueado com sucesso"}

@router.post("/{cliente_id}/ativar")
@require_permission("clientes", "manage")
async def ativar_cliente(
    cliente_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Ativa um cliente"""
    sucesso = ClienteService.ativar_cliente(db, cliente_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"message": "Cliente ativado com sucesso"}

@router.get("/{cliente_id}/estatisticas")
@require_permission("dashboard", "view")
async def estatisticas_cliente(
    cliente_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtém estatísticas do cliente"""
    from app.services.maquina_service import MaquinaService
    from app.services.licenca_service import LicencaService
    
    cliente = ClienteService.obter_cliente(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    estatisticas_maquinas = MaquinaService.get_estatisticas_maquinas(db, cliente_id)
    
    # Contar licenças
    licencas_ativas = db.query(Licenca).filter(
        Licenca.cliente_id == cliente_id,
        Licenca.status == "ativa"
    ).count()
    
    # Próxima renovação
    assinatura = db.query(Assinatura).filter(
        Assinatura.cliente_id == cliente_id,
        Assinatura.status == "ativa"
    ).first()
    
    return {
        "cliente": {
            "nome": cliente.nome,
            "tipo": cliente.tipo,
            "status": cliente.status,
            "data_expiracao": cliente.data_expiracao
        },
        "maquinas": estatisticas_maquinas,
        "licencas_ativas": licencas_ativas,
        "proxima_renovacao": assinatura.data_fim if assinatura else None,
        "dias_para_expiracao": (
            (cliente.data_expiracao - datetime.utcnow()).days 
            if cliente.data_expiracao else None
        )
    }

@router.get("/risco/expiracao")
@require_permission("dashboard", "view")
async def clientes_em_risco_expiracao(
    dias: int = Query(7, ge=1, le=30),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista clientes com assinatura prestes a expirar"""
    clientes = ClienteService.get_clientes_em_risco(db, dias)
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "email": c.email,
            "data_expiracao": c.data_expiracao,
            "dias_restantes": (c.data_expiracao - datetime.utcnow()).days
        }
        for c in clientes
    ]

@router.get("/estatisticas/geral")
@require_permission("dashboard", "view")
async def estatisticas_gerais(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Estatísticas gerais do sistema"""
    return ClienteService.get_estatisticas_clientes(db)
