#licenca.py

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Float, Text, Enum, JSON, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime, timedelta

from app.database.base import BaseModel

class TipoLicenca(str, enum.Enum):
    DEMONSTRACAO = "demonstracao"
    TEMPORARIA = "temporaria"
    PERPETUA = "perpetua"
    ASSINATURA = "assinatura"

class StatusLicenca(str, enum.Enum):
    ATIVA = "ativa"
    EXPIRADA = "expirada"
    SUSPENSA = "suspensa"
    CANCELADA = "cancelada"
    PENDENTE = "pendente"

class CicloFaturamento(str, enum.Enum):
    MENSAL = "mensal"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"
    BIANUAL = "bianual"

class Licenca(BaseModel):
    __tablename__ = "licencas"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"))
    maquina_id = Column(Integer, ForeignKey("maquinas.id", ondelete="CASCADE"), nullable=True)
    chave_licenca = Column(String(100), unique=True, index=True, nullable=False)
    tipo = Column(Enum(TipoLicenca), default=TipoLicenca.ASSINATURA)
    status = Column(Enum(StatusLicenca), default=StatusLicenca.PENDENTE)
    data_ativacao = Column(DateTime(timezone=True))
    data_expiracao = Column(DateTime(timezone=True))
    data_renovacao = Column(DateTime(timezone=True))
    limite_usos = Column(Integer, default=0)  # 0 = ilimitado
    usos_atuais = Column(Integer, default=0)
    modulo_acesso = Column(JSON)  # Lista de módulos permitidos
    recursos_extra = Column(JSON)  # Recursos adicionais
    
    # Relationships
    cliente = relationship("Cliente", back_populates="licencas")
    maquina = relationship("Maquina", back_populates="licenca")
    assinatura = relationship("Assinatura", back_populates="licenca", uselist=False)

class Assinatura(BaseModel):
    __tablename__ = "assinaturas"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"))
    licenca_id = Column(Integer, ForeignKey("licencas.id", ondelete="CASCADE"))
    plano = Column(String(100), nullable=False)
    ciclo = Column(Enum(CicloFaturamento), default=CicloFaturamento.MENSAL)
    valor = Column(Numeric(10, 2), nullable=False)
    data_inicio = Column(DateTime(timezone=True), nullable=False)
    data_fim = Column(DateTime(timezone=True))
    renovacao_automatica = Column(Boolean, default=True)
    status = Column(String(50), default="ativa")
    metodo_pagamento = Column(String(50))
    dados_pagamento = Column(JSON)  # Dados sensíveis do pagamento
    limite_microservicos = Column(Integer, default=5)
    limite_storage = Column(Integer, default=10)  # GB
    limite_api_calls = Column(Integer, default=1000)
    
    # Relationships
    cliente = relationship("Cliente", back_populates="assinaturas")
    licenca = relationship("Licenca", back_populates="assinatura")
    pagamentos = relationship("Pagamento", back_populates="assinatura")

class Bloqueio(BaseModel):
    __tablename__ = "bloqueios"
    
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"))
    maquina_id = Column(Integer, ForeignKey("maquinas.id", ondelete="CASCADE"), nullable=True)
    motivo = Column(Text, nullable=False)
    tipo = Column(String(50))  # pagamento, uso_abusivo, violacao_termos
    severidade = Column(String(20))  # baixa, media, alta, critica
    data_bloqueio = Column(DateTime(timezone=True), server_default=func.now())
    data_desbloqueio = Column(DateTime(timezone=True), nullable=True)
    desbloqueado_por = Column(String(100), nullable=True)
    
    # Relationships
    cliente = relationship("Cliente", back_populates="bloqueios")
    maquina = relationship("Maquina")

class Pagamento(BaseModel):
    __tablename__ = "pagamentos"
    
    assinatura_id = Column(Integer, ForeignKey("assinaturas.id", ondelete="CASCADE"))
    referencia = Column(String(100), unique=True, index=True, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    moeda = Column(String(10), default="BRL")
    metodo = Column(String(50))  # cartao, boleto, pix, transferencia
    status = Column(String(50))  # pendente, pago, falhou, estornado
    data_pagamento = Column(DateTime(timezone=True))
    data_vencimento = Column(DateTime(timezone=True))
    dados_transacao = Column(JSON)
    
    # Relationships
    assinatura = relationship("Assinatura", back_populates="pagamentos")
