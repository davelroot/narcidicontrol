from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

class TipoLicenca(str, Enum):
    DEMONSTRACAO = "demonstracao"
    TEMPORARIA = "temporaria"
    PERPETUA = "perpetua"
    ASSINATURA = "assinatura"

class StatusLicenca(str, Enum):
    ATIVA = "ativa"
    EXPIRADA = "expirada"
    SUSPENSA = "suspensa"
    CANCELADA = "cancelada"
    PENDENTE = "pendente"

class CicloFaturamento(str, Enum):
    MENSAL = "mensal"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"
    BIANUAL = "bianual"

class LicencaBase(BaseModel):
    tipo: TipoLicenca = TipoLicenca.ASSINATURA
    limite_usos: int = 0
    modulo_acesso: Optional[List[str]] = None
    recursos_extra: Optional[Dict[str, Any]] = None

class LicencaCreate(LicencaBase):
    cliente_id: int
    maquina_id: Optional[int] = None

class LicencaUpdate(BaseModel):
    status: Optional[StatusLicenca] = None
    data_expiracao: Optional[datetime] = None
    limite_usos: Optional[int] = None
    usos_atuais: Optional[int] = None

class LicencaResponse(LicencaBase):
    id: int
    cliente_id: int
    maquina_id: Optional[int]
    chave_licenca: str
    status: StatusLicenca
    data_ativacao: Optional[datetime]
    data_expiracao: Optional[datetime]
    data_renovacao: Optional[datetime]
    usos_atuais: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class AssinaturaBase(BaseModel):
    plano: str
    ciclo: CicloFaturamento = CicloFaturamento.MENSAL
    valor: Decimal = Field(..., gt=0)
    renovacao_automatica: bool = True
    limite_microservicos: int = 5
    limite_storage: int = 10
    limite_api_calls: int = 1000

class AssinaturaCreate(AssinaturaBase):
    cliente_id: int
    licenca_id: int
    data_inicio: datetime

class AssinaturaUpdate(BaseModel):
    plano: Optional[str] = None
    ciclo: Optional[CicloFaturamento] = None
    renovacao_automatica: Optional[bool] = None
    status: Optional[str] = None

class AssinaturaResponse(AssinaturaBase):
    id: int
    cliente_id: int
    licenca_id: int
    data_inicio: datetime
    data_fim: Optional[datetime]
    status: str
    metodo_pagamento: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class BloqueioBase(BaseModel):
    motivo: str
    tipo: str
    severidade: str = "media"

class BloqueioCreate(BloqueioBase):
    cliente_id: int
    maquina_id: Optional[int] = None

class BloqueioResponse(BloqueioBase):
    id: int
    cliente_id: int
    maquina_id: Optional[int]
    data_bloqueio: datetime
    data_desbloqueio: Optional[datetime]
    desbloqueado_por: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class PagamentoBase(BaseModel):
    valor: Decimal = Field(..., gt=0)
    moeda: str = "BRL"
    metodo: str
    status: str = "pendente"

class PagamentoCreate(PagamentoBase):
    assinatura_id: int
    referencia: str
    data_vencimento: Optional[datetime] = None

class PagamentoResponse(PagamentoBase):
    id: int
    assinatura_id: int
    referencia: str
    data_pagamento: Optional[datetime]
    data_vencimento: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
