from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TipoCliente(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class StatusCliente(str, Enum):
    ATIVO = "ativo"
    PENDENTE = "pendente"
    BLOQUEADO = "bloqueado"
    CANCELADO = "cancelado"

class ClienteBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    cpf_cnpj: Optional[str] = None
    telefone: Optional[str] = None
    empresa: Optional[str] = None
    tipo: TipoCliente = TipoCliente.FREE
    limite_maquinas: int = 1

class ClienteCreate(ClienteBase):
    senha: str = Field(..., min_length=6)

class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    empresa: Optional[str] = None
    tipo: Optional[TipoCliente] = None
    status: Optional[StatusCliente] = None

class ClienteResponse(ClienteBase):
    id: int
    status: StatusCliente
    data_assinatura: Optional[datetime]
    data_expiracao: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True

class PerfilClienteBase(BaseModel):
    nome_perfil: str = Field(..., min_length=2, max_length=100)
    avatar_url: Optional[str] = None
    tema_interface: str = "light"
    idioma: str = "pt-BR"
    notificacoes_email: bool = True
    notificacoes_push: bool = True

class PerfilClienteCreate(PerfilClienteBase):
    cliente_id: int

class PerfilClienteResponse(PerfilClienteBase):
    id: int
    cliente_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class PermissaoClienteBase(BaseModel):
    modulo: str
    acao: str
    permitido: bool = True

class PermissaoClienteCreate(PermissaoClienteBase):
    perfil_id: int

class PermissaoClienteResponse(PermissaoClienteBase):
    id: int
    perfil_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
