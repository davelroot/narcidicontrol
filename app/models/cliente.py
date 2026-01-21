from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database.base import BaseModel

class TipoCliente(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class StatusCliente(str, enum.Enum):
    ATIVO = "ativo"
    PENDENTE = "pendente"
    BLOQUEADO = "bloqueado"
    CANCELADO = "cancelado"

class Cliente(BaseModel):
    __tablename__ = "clientes"
    
    nome = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    cpf_cnpj = Column(String(20), unique=True, index=True)
    telefone = Column(String(20))
    empresa = Column(String(200))
    tipo = Column(Enum(TipoCliente), default=TipoCliente.FREE)
    status = Column(Enum(StatusCliente), default=StatusCliente.PENDENTE)
    data_assinatura = Column(DateTime(timezone=True))
    data_expiracao = Column(DateTime(timezone=True))
    limite_maquinas = Column(Integer, default=1)
    
    # Relationships
    perfis = relationship("PerfilCliente", back_populates="cliente")
    maquinas = relationship("Maquina", back_populates="cliente")
    licencas = relationship("Licenca", back_populates="cliente")
    assinaturas = relationship("Assinatura", back_populates="cliente")
    bloqueios = relationship("Bloqueio", back_populates="cliente")
    uploads = relationship("UploadVersao", back_populates="cliente")

class PerfilCliente(BaseModel):
    __tablename__ = "perfis_cliente"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"))
    nome_perfil = Column(String(100), nullable=False)
    avatar_url = Column(String(500))
    tema_interface = Column(String(50), default="light")
    idioma = Column(String(10), default="pt-BR")
    notificacoes_email = Column(Boolean, default=True)
    notificacoes_push = Column(Boolean, default=True)
    
    # Relationships
    cliente = relationship("Cliente", back_populates="perfis")
    permissoes = relationship("PermissaoCliente", back_populates="perfil")

class PermissaoCliente(BaseModel):
    __tablename__ = "permissoes_cliente"
    
    perfil_id = Column(Integer, ForeignKey("perfis_cliente.id", ondelete="CASCADE"))
    modulo = Column(String(100), nullable=False)
    acao = Column(String(50), nullable=False)
    permitido = Column(Boolean, default=True)
    
    # Relationships
    perfil = relationship("PerfilCliente", back_populates="permissoes")
