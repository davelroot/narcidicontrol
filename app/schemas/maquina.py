from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class StatusMaquina(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MANUTENCAO = "manutencao"
    BLOQUEADA = "bloqueada"

class SistemaOperacional(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"

class MaquinaBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    identificador_unico: str = Field(..., min_length=5)
    descricao: Optional[str] = None
    sistema_operacional: Optional[SistemaOperacional] = None
    versao_sistema: Optional[str] = None
    processador: Optional[str] = None
    memoria_ram: Optional[float] = None
    armazenamento: Optional[float] = None

class MaquinaCreate(MaquinaBase):
    cliente_id: int
    ip_publico: Optional[str] = None
    ip_interno: Optional[str] = None

class MaquinaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    status: Optional[StatusMaquina] = None

class MaquinaResponse(MaquinaBase):
    id: int
    cliente_id: int
    ip_publico: Optional[str]
    ip_interno: Optional[str]
    status: StatusMaquina
    ultima_conexao: Optional[datetime]
    tempo_atividade: int
    versao_app: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class MaquinaMetricaBase(BaseModel):
    cpu_uso: Optional[float] = Field(None, ge=0, le=100)
    memoria_uso: Optional[float] = Field(None, ge=0, le=100)
    disco_uso: Optional[float] = Field(None, ge=0, le=100)
    temperatura: Optional[float] = None
    rede_upload: Optional[float] = None
    rede_download: Optional[float] = None
    latencia: Optional[float] = None
    processos_ativos: Optional[int] = None

class MaquinaMetricaCreate(MaquinaMetricaBase):
    maquina_id: int

class MaquinaMetricaResponse(MaquinaMetricaBase):
    id: int
    maquina_id: int
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class HeartbeatRequest(BaseModel):
    identificador_unico: str
    status: StatusMaquina
    metricas: Optional[MaquinaMetricaBase] = None
    versao_app: Optional[str] = None

class MachineDashboard(BaseModel):
    total_maquinas: int
    online: int
    offline: int
    bloqueadas: int
    uso_cpu_medio: float
    uso_memoria_medio: float
    atividade_24h: List[Dict[str, Any]]
