from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Float, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database.base import BaseModel

class StatusUpload(str, enum.Enum):
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    FALHOU = "falhou"
    VALIDANDO = "validando"

class TipoVersao(str, enum.Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    HOTFIX = "hotfix"

class UploadVersao(BaseModel):
    __tablename__ = "uploads_versao"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"))
    versao = Column(String(20), nullable=False)
    tipo = Column(Enum(TipoVersao), default=TipoVersao.PATCH)
    arquivo_path = Column(String(500), nullable=False)
    arquivo_hash = Column(String(100), nullable=False)
    arquivo_tamanho = Column(Integer)  # bytes
    descricao = Column(Text)
    notas_release = Column(Text)
    status = Column(Enum(StatusUpload), default=StatusUpload.PENDENTE)
    data_publicacao = Column(DateTime(timezone=True))
    data_disponibilidade = Column(DateTime(timezone=True))
    compatibilidade = Column(JSON)  # Sistemas compatíveis
    requisitos = Column(JSON)  # Requisitos do sistema
    changelog = Column(Text)
    
    # Relationships
    cliente = relationship("Cliente", back_populates="uploads")
    historico = relationship("HistoricoUpload", back_populates="upload")

class HistoricoUpload(BaseModel):
    __tablename__ = "historico_uploads"
    
    upload_id = Column(Integer, ForeignKey("uploads_versao.id", ondelete="CASCADE"))
    acao = Column(String(100), nullable=False)
    detalhes = Column(Text)
    usuario = Column(String(100))
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    # Relationships
    upload = relationship("UploadVersao", back_populates="historico")
