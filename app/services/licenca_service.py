from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging

from app.models.licenca import Licenca, Assinatura, Bloqueio, Pagamento, StatusLicenca, TipoLicenca
from app.models.cliente import Cliente
from app.schemas.licenca import LicencaCreate, AssinaturaCreate, BloqueioCreate, PagamentoCreate
from app.utils.security import generate_license_key
from app.events.alertas import enviar_alerta_licenca_expirada, enviar_alerta_pagamento_pendente

logger = logging.getLogger(__name__)

class LicencaService:
    @staticmethod
    def gerar_chave_licenca() -> str:
        """Gera uma chave de licença única"""
        return generate_license_key()
    
    @staticmethod
    def criar_licenca(db: Session, licenca_data: LicencaCreate) -> Licenca:
        """Cria uma nova licença"""
        # Verificar se cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == licenca_data.cliente_id).first()
        if not cliente:
            raise ValueError("Cliente não encontrado")
        
        # Verificar limite de máquinas
        if licenca_data.maquina_id:
            licencas_cliente = db.query(func.count(Licenca.id)).filter(
                and_(
                    Licenca.cliente_id == licenca_data.cliente_id,
                    Licenca.status == StatusLicenca.ATIVA
                )
            ).scalar()
            
            if licencas_cliente >= cliente.limite_maquinas:
                raise ValueError("Limite de máquinas atingido para este cliente")
        
        # Criar licença
        db_licenca = Licenca(
            cliente_id=licenca_data.cliente_id,
            maquina_id=licenca_data.maquina_id,
            chave_licenca=LicencaService.gerar_chave_licenca(),
            tipo=licenca_data.tipo,
            modulo_acesso=licenca_data.modulo_acesso or [],
            recursos_extra=licenca_data.recursos_extra or {},
            limite_usos=licenca_data.limite_usos,
            status=StatusLicenca.PENDENTE
        )
        
        # Definir datas baseadas no tipo
        if licenca_data.tipo == TipoLicenca.DEMONSTRACAO:
            db_licenca.data_expiracao = datetime.utcnow() + timedelta(days=15)
        elif licenca_data.tipo == TipoLicenca.TEMPORARIA:
            db_licenca.data_expiracao = datetime.utcnow() + timedelta(days=30)
        
        db.add(db_licenca)
        db.commit()
        db.refresh(db_licenca)
        
        logger.info(f"Nova licença criada: {db_licenca.chave_licenca} (Cliente: {cliente.email})")
        return db_licenca
    
    @staticmethod
    def ativar_licenca(db: Session, chave_licenca: str, maquina_id: Optional[int] = None) -> bool:
        """Ativa uma licença"""
        licenca = db.query(Licenca).filter(Licenca.chave_licenca == chave_licenca).first()
        if not licenca:
            return False
        
        # Verificar se licença já está ativa
        if licenca.status == StatusLicenca.ATIVA:
            return True
        
        # Verificar se está expirada
        if licenca.data_expiracao and licenca.data_expiracao < datetime.utcnow():
            licenca.status = StatusLicenca.EXPIRADA
            db.commit()
            enviar_alerta_licenca_expirada(licenca)
            return False
        
        # Verificar limite de usos
        if licenca.limite_usos > 0 and licenca.usos_atuais >= licenca.limite_usos:
            return False
        
        # Atualizar licença
        licenca.status = StatusLicenca.ATIVA
        licenca.data_ativacao = datetime.utcnow()
        licenca.usos_atuais += 1
        
        if maquina_id:
            licenca.maquina_id = maquina_id
        
        db.commit()
        
        logger.info(f"Licença ativada: {chave_licenca}")
        return True
    
    @staticmethod
    def verificar_licenca(db: Session, chave_licenca: str) -> Optional[Licenca]:
        """Verifica status de uma licença"""
        licenca = db.query(Licenca).filter(Licenca.chave_licenca == chave_licenca).first()
        if not licenca:
            return None
        
        # Verificar expiração
        if licenca.data_expiracao and licenca.data_expiracao < datetime.utcnow():
            licenca.status = StatusLicenca.EXPIRADA
            db.commit()
            enviar_alerta_licenca_expirada(licenca)
        
        return licenca
    
    @staticmethod
    def renovar_licenca(db: Session, licenca_id: int, meses: int = 1) -> bool:
        """Renova uma licença"""
        licenca = db.query(Licenca).filter(Licenca.id == licenca_id).first()
        if not licenca:
            return False
        
        # Calcular nova data de expiração
        nova_data = licenca.data_expiracao or datetime.utcnow()
        nova_data = nova_data + timedelta(days=30 * meses)
        
        licenca.data_expiracao = nova_data
        licenca.data_renovacao = datetime.utcnow()
        licenca.status = StatusLicenca.ATIVA
        
        db.commit()
        
        logger.info(f"Licença renovada: {licenca.chave_licenca} até {nova_data}")
        return True
    
    @staticmethod
    def bloquear_licenca(db: Session, licenca_id: int, motivo: str) -> bool:
        """Bloqueia uma licença"""
        licenca = db.query(Licenca).filter(Licenca.id == licenca_id).first()
        if not licenca:
            return False
        
        licenca.status = StatusLicenca.SUSPENSA
        db.commit()
        
        # Registrar bloqueio
        bloqueio = Bloqueio(
            cliente_id=licenca.cliente_id,
            maquina_id=licenca.maquina_id,
            motivo=motivo,
            tipo="licenca",
            severidade="alta"
        )
        db.add(bloqueio)
        db.commit()
        
        logger.warning(f"Licença bloqueada: {licenca.chave_licenca} - Motivo: {motivo}")
        return True
    
    @staticmethod
    def get_licencas_expirando(db: Session, dias: int = 7) -> List[Licenca]:
        """Retorna licenças prestes a expirar"""
        data_limite = datetime.utcnow() + timedelta(days=dias)
        
        licencas = db.query(Licenca).filter(
            and_(
                Licenca.status == StatusLicenca.ATIVA,
                Licenca.data_expiracao <= data_limite,
                Licenca.data_expiracao > datetime.utcnow()
            )
        ).all()
        
        return licencas

class AssinaturaService:
    @staticmethod
    def criar_assinatura(db: Session, assinatura_data: AssinaturaCreate) -> Assinatura:
        """Cria uma nova assinatura"""
        # Verificar se cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == assinatura_data.cliente_id).first()
        if not cliente:
            raise ValueError("Cliente não encontrado")
        
        # Verificar se licença existe
        licenca = db.query(Licenca).filter(Licenca.id == assinatura_data.licenca_id).first()
        if not licenca:
            raise ValueError("Licença não encontrada")
        
        # Calcular data de fim
        data_fim = assinatura_data.data_inicio
        if assinatura_data.ciclo == "mensal":
            data_fim += timedelta(days=30)
        elif assinatura_data.ciclo == "trimestral":
            data_fim += timedelta(days=90)
        elif assinatura_data.ciclo == "semestral":
            data_fim += timedelta(days=180)
        elif assinatura_data.ciclo == "anual":
            data_fim += timedelta(days=365)
        elif assinatura_data.ciclo == "bianual":
            data_fim += timedelta(days=730)
        
        # Criar assinatura
        db_assinatura = Assinatura(
            cliente_id=assinatura_data.cliente_id,
            licenca_id=assinatura_data.licenca_id,
            plano=assinatura_data.plano,
            ciclo=assinatura_data.ciclo,
            valor=assinatura_data.valor,
            data_inicio=assinatura_data.data_inicio,
            data_fim=data_fim,
            renovacao_automatica=assinatura_data.renovacao_automatica,
            status="ativa",
            limite_microservicos=assinatura_data.limite_microservicos,
            limite_storage=assinatura_data.limite_storage,
            limite_api_calls=assinatura_data.limite_api_calls
        )
        
        db.add(db_assinatura)
        db.commit()
        db.refresh(db_assinatura)
        
        # Atualizar cliente
        cliente.tipo = assinatura_data.plano.lower()
        cliente.data_assinatura = assinatura_data.data_inicio
        cliente.data_expiracao = data_fim
        cliente.status = "ativo"
        db.commit()
        
        logger.info(f"Nova assinatura criada: {assinatura_data.plano} (Cliente: {cliente.email})")
        return db_assinatura
    
    @staticmethod
    def verificar_renovacoes(db: Session) -> List[Assinatura]:
        """Verifica assinaturas que precisam ser renovadas"""
        data_limite = datetime.utcnow() + timedelta(days=3)
        
        assinaturas = db.query(Assinatura).filter(
            and_(
                Assinatura.status == "ativa",
                Assinatura.data_fim <= data_limite,
                Assinatura.data_fim > datetime.utcnow(),
                Assinatura.renovacao_automatica == True
            )
        ).all()
        
        for assinatura in assinaturas:
            enviar_alerta_pagamento_pendente(assinatura)
        
        return assinaturas
    
    @staticmethod
    def renovar_assinatura(db: Session, assinatura_id: int) -> bool:
        """Renova uma assinatura automaticamente"""
        assinatura = db.query(Assinatura).filter(Assinatura.id == assinatura_id).first()
        if not assinatura:
            return False
        
        # Calcular nova data de fim baseada no ciclo
        nova_data_fim = assinatura.data_fim
        if assinatura.ciclo == "mensal":
            nova_data_fim += timedelta(days=30)
        elif assinatura.ciclo == "trimestral":
            nova_data_fim += timedelta(days=90)
        elif assinatura.ciclo == "semestral":
            nova_data_fim += timedelta(days=180)
        elif assinatura.ciclo == "anual":
            nova_data_fim += timedelta(days=365)
        elif assinatura.ciclo == "bianual":
            nova_data_fim += timedelta(days=730)
        
        assinatura.data_fim = nova_data_fim
        
        # Atualizar cliente
        cliente = db.query(Cliente).filter(Cliente.id == assinatura.cliente_id).first()
        if cliente:
            cliente.data_expiracao = nova_data_fim
        
        db.commit()
        
        logger.info(f"Assinatura renovada: {assinatura.plano} (ID: {assinatura.id})")
        return True
