from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.database.session import get_db
from app.schemas.upload import (
    UploadVersaoCreate, UploadVersaoResponse, UploadVersaoUpdate,
    HistoricoUploadResponse,
    VersionCheckRequest, VersionCheckResponse
)
from app.services.upload_service import UploadService
from app.utils.security import get_current_active_user, require_permission

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/versao", response_model=UploadVersaoResponse, status_code=status.HTTP_201_CREATED)
@require_permission("uploads", "manage")
async def upload_versao(
    file: UploadFile = File(...),
    cliente_id: int = Form(...),
    versao: str = Form(...),
    tipo: str = Form("patch"),
    descricao: Optional[str] = Form(None),
    notas_release: Optional[str] = Form(None),
    compatibilidade: Optional[str] = Form(None),
    requisitos: Optional[str] = Form(None),
    changelog: Optional[str] = Form(None),
    arquivo_hash: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Faz upload de uma nova versão"""
    try:
        # Parse JSON fields
        compatibilidade_dict = json.loads(compatibilidade) if compatibilidade else None
        requisitos_dict = json.loads(requisitos) if requisitos else None
        
        upload_data = UploadVersaoCreate(
            cliente_id=cliente_id,
            versao=versao,
            tipo=tipo,
            descricao=descricao,
            notas_release=notas_release,
            compatibilidade=compatibilidade_dict,
            requisitos=requisitos_dict,
            changelog=changelog,
            arquivo_hash=arquivo_hash,
            arquivo_tamanho=0  # Será calculado
        )
        
        upload_service = UploadService()
        upload = await upload_service.fazer_upload_versao(db, cliente_id, file, upload_data)
        return upload
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Campos JSON inválidos")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/versao", response_model=List[UploadVersaoResponse])
async def listar_versoes(
    cliente_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Lista versões disponíveis"""
    upload_service = UploadService()
    versoes = upload_service.listar_versoes(db, cliente_id, skip, limit)
    return versoes

@router.get("/versao/latest")
async def ultima_versao(
    cliente_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtém a última versão disponível"""
    upload_service = UploadService()
    versoes = upload_service.listar_versoes(db, cliente_id, limit=1)
    
    if not versoes:
        raise HTTPException(status_code=404, detail="Nenhuma versão disponível")
    
    return versoes[0]

@router.post("/versao/check", response_model=VersionCheckResponse)
async def verificar_atualizacao(
    check_request: VersionCheckRequest,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Verifica se há atualizações disponíveis (pública)"""
    upload_service = UploadService()
    return upload_service.verificar_atualizacao(db, check_request.versao_atual, check_request.sistema_operacional, cliente_id)

@router.post("/versao/{upload_id}/status")
@require_permission("uploads", "manage")
async def atualizar_status_upload(
    upload_id: int,
    status: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Atualiza status de um upload"""
    upload_service = UploadService()
    sucesso = upload_service.atualizar_status_upload(db, upload_id, status)
    
    if not sucesso:
        raise HTTPException(status_code=404, detail="Upload não encontrado")
    
    return {"message": f"Status atualizado para {status}"}

@router.get("/versao/{upload_id}/historico", response_model=List[HistoricoUploadResponse])
@require_permission("uploads", "view")
async def historico_upload(
    upload_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtém histórico de um upload"""
    from app.models.upload import HistoricoUpload
    
    historico = db.query(HistoricoUpload).filter(
        HistoricoUpload.upload_id == upload_id
    ).order_by(HistoricoUpload.created_at.desc()).all()
    
    return historico

@router.get("/download/{upload_id}")
async def download_versao(
    upload_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download de uma versão específica"""
    from app.models.upload import UploadVersao
    
    upload = db.query(UploadVersao).filter(UploadVersao.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload não encontrado")
    
    # Verificar permissões
    if upload.cliente_id and upload.cliente_id != current_user.get("cliente_id"):
        require_permission("uploads", "download")(lambda: None)()
    
    # Verificar se está disponível
    if upload.status != "concluido":
        raise HTTPException(status_code=400, detail="Versão não disponível para download")
    
    if upload.data_disponibilidade and upload.data_disponibilidade > datetime.utcnow():
        raise HTTPException(status_code=400, detail="Versão ainda não disponível")
    
    # Retornar URL ou fazer download direto
    return {
        "url": upload.arquivo_path,
        "filename": upload.arquivo_path.split("/")[-1],
        "size": upload.arquivo_tamanho,
        "hash": upload.arquivo_hash
    }
