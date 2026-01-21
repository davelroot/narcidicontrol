from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class TipoVersao(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    HOTFIX = "hotfix"

class StatusUpload(str, Enum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    FALHOU = "falhou"
    VALIDANDO = "validando"

class UploadVersaoBase(BaseModel):
    versao: str = Field(..., regex=r'^\d+\.\d+\.\d+$')
    tipo: TipoVersao = TipoVersao.PATCH
    descricao: Optional[str] = None
    notas_release: Optional[str] = None
    compatibilidade: Optional[Dict[str, Any]] = None
    requisitos: Optional[Dict[str, Any]] = None
    changelog: Optional[str] = None

class UploadVersaoCreate(UploadVersaoBase):
    cliente_id: int
    arquivo_hash: str
    arquivo_tamanho: int

class UploadVersaoUpdate(BaseModel):
    status: Optional[StatusUpload] = None
    data_publicacao: Optional[datetime] = None
    data_disponibilidade: Optional[datetime] = None

class UploadVersaoResponse(UploadVersaoBase):
    id: int
    cliente_id: int
    arquivo_path: str
    arquivo_hash: str
    arquivo_tamanho: int
    status: StatusUpload
    data_publicacao: Optional[datetime]
    data_disponibilidade: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class HistoricoUploadBase(BaseModel):
    acao: str
    detalhes: Optional[str] = None
    usuario: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class HistoricoUploadCreate(HistoricoUploadBase):
    upload_id: int

class HistoricoUploadResponse(HistoricoUploadBase):
    id: int
    upload_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class VersionCheckRequest(BaseModel):
    versao_atual: str = Field(..., regex=r'^\d+\.\d+\.\d+$')
    sistema_operacional: str
    arquitetura: str = "x64"

class VersionCheckResponse(BaseModel):
    atualizacao_disponivel: bool
    versao_latest: str
    tipo_atualizacao: Optional[TipoVersao]
    url_download: Optional[str]
    tamanho: Optional[int]
    hash_verificacao: Optional[str]
    forcada: bool = False
    notas: Optional[str]
