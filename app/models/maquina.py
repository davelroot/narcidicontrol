from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Float, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database.base import BaseModel

class StatusMaquina(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MANUTENCAO = "manutencao"
    BLOQUEADA = "bloqueada"

class SistemaOperacional(str, enum.Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"

class Maquina(BaseModel):
    __tablename__ = "maquinas"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"))
    nome = Column(String(100), nullable=False)
    identificador_unico = Column(String(100), unique=True, index=True, nullable=False)
    descricao = Column(Text)
    ip_publico = Column(String(50))
    ip_interno = Column(String(50))
    sistema_operacional = Column(Enum(SistemaOperacional))
    versao_sistema = Column(String(50))
    processador = Column(String(100))
    memoria_ram = Column(Float)  # GB
    armazenamento = Column(Float)  # GB
    ultima_conexao = Column(DateTime(timezone=True))
    status = Column(Enum(StatusMaquina), default=StatusMaquina.OFFLINE)
    tempo_atividade = Column(Integer, default=0)  # segundos
    versao_app = Column(String(20))
    
    # Relationships
    cliente = relationship("Cliente", back_populates="maquinas")
    metricas = relationship("MaquinaMetrica", back_populates="maquina")
    licenca = relationship("Licenca", back_populates="maquina", uselist=False)

class MaquinaMetrica(BaseModel):
    __tablename__ = "maquinas_metricas"
    
    maquina_id = Column(Integer, ForeignKey("maquinas.id", ondelete="CASCADE"))
    cpu_uso = Column(Float)  # porcentagem
    memoria_uso = Column(Float)  # porcentagem
    disco_uso = Column(Float)  # porcentagem
    temperatura = Column(Float)  # celsius
    rede_upload = Column(Float)  # Mbps
    rede_download = Column(Float)  # Mbps
    latencia = Column(Float)  # ms
    processos_ativos = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    maquina = relationship("Maquina", back_populates="metricas")
