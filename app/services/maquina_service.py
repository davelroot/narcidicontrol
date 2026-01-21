#maquina_service.py

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.models.maquina import Maquina, MaquinaMetrica, StatusMaquina
from app.models.cliente import Cliente
from app.schemas.maquina import MaquinaCreate, MaquinaMetricaCreate, HeartbeatRequest
from app.events.alertas import enviar_alerta_maquina_offline, enviar_alerta_maquina_suspeita

logger = logging.getLogger(__name__)

class MaquinaService:
    @staticmethod
    def registrar_maquina(db: Session, maquina_data: MaquinaCreate) -> Maquina:
        """Registra uma nova máquina"""
        # Verificar se cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == maquina_data.cliente_id).first()
        if not cliente:
            raise ValueError("Cliente não encontrado")
        
        # Verificar se identificador já existe
        if db.query(Maquina).filter(Maquina.identificador_unico == maquina_data.identificador_unico).first():
            raise ValueError("Identificador único já registrado")
        
        # Criar máquina
        db_maquina = Maquina(
            cliente_id=maquina_data.cliente_id,
            nome=maquina_data.nome,
            identificador_unico=maquina_data.identificador_unico,
            descricao=maquina_data.descricao,
            ip_publico=maquina_data.ip_publico,
            ip_interno=maquina_data.ip_interno,
            sistema_operacional=maquina_data.sistema_operacional,
            versao_sistema=maquina_data.versao_sistema,
            processador=maquina_data.processador,
            memoria_ram=maquina_data.memoria_ram,
            armazenamento=maquina_data.armazenamento,
            status=StatusMaquina.OFFLINE,
            ultima_conexao=datetime.utcnow()
        )
        
        db.add(db_maquina)
        db.commit()
        db.refresh(db_maquina)
        
        logger.info(f"Nova máquina registrada: {maquina_data.nome} (Cliente: {cliente.email})")
        return db_maquina
    
    @staticmethod
    def processar_heartbeat(db: Session, heartbeat: HeartbeatRequest) -> Optional[Maquina]:
        """Processa heartbeat de uma máquina"""
        maquina = db.query(Maquina).filter(
            Maquina.identificador_unico == heartbeat.identificador_unico
        ).first()
        
        if not maquina:
            return None
        
        # Atualizar status e última conexão
        status_anterior = maquina.status
        maquina.status = heartbeat.status
        maquina.ultima_conexao = datetime.utcnow()
        
        if heartbeat.versao_app:
            maquina.versao_app = heartbeat.versao_app
        
        # Se estava offline e voltou online, incrementar tempo de atividade
        if status_anterior == StatusMaquina.OFFLINE and heartbeat.status == StatusMaquina.ONLINE:
            maquina.tempo_atividade += 300  # Adiciona 5 minutos
        
        # Registrar métricas se fornecidas
        if heartbeat.metricas:
            metrica = MaquinaMetrica(
                maquina_id=maquina.id,
                cpu_uso=heartbeat.metricas.cpu_uso,
                memoria_uso=heartbeat.metricas.memoria_uso,
                disco_uso=heartbeat.metricas.disco_uso,
                temperatura=heartbeat.metricas.temperatura,
                rede_upload=heartbeat.metricas.rede_upload,
                rede_download=heartbeat.metricas.rede_download,
                latencia=heartbeat.metricas.latencia,
                processos_ativos=heartbeat.metricas.processos_ativos
            )
            db.add(metrica)
            
            # Verificar métricas suspeitas
            if heartbeat.metricas.cpu_uso and heartbeat.metricas.cpu_uso > 90:
                enviar_alerta_maquina_suspeita(maquina, "Uso de CPU muito alto")
            if heartbeat.metricas.memoria_uso and heartbeat.metricas.memoria_uso > 90:
                enviar_alerta_maquina_suspeita(maquina, "Uso de memória muito alto")
        
        db.commit()
        db.refresh(maquina)
        
        # Se voltou online após estar offline, enviar notificação
        if status_anterior == StatusMaquina.OFFLINE and heartbeat.status == StatusMaquina.ONLINE:
            logger.info(f"Máquina voltou online: {maquina.nome} (ID: {maquina.id})")
        
        return maquina
    
    @staticmethod
    def verificar_maquinas_offline(db: Session, minutos_offline: int = 5) -> List[Maquina]:
        """Retorna máquinas offline há mais de X minutos"""
        limite_offline = datetime.utcnow() - timedelta(minutes=minutos_offline)
        
        maquinas = db.query(Maquina).filter(
            and_(
                Maquina.status != StatusMaquina.OFFLINE,
                Maquina.ultima_conexao < limite_offline
            )
        ).all()
        
        # Atualizar status para offline
        for maquina in maquinas:
            if maquina.status != StatusMaquina.OFFLINE:
                maquina.status = StatusMaquina.OFFLINE
                enviar_alerta_maquina_offline(maquina)
        
        db.commit()
        return maquinas
    
    @staticmethod
    def bloquear_maquina(db: Session, maquina_id: int, motivo: str) -> bool:
        """Bloqueia uma máquina remotamente"""
        maquina = db.query(Maquina).filter(Maquina.id == maquina_id).first()
        if not maquina:
            return False
        
        maquina.status = StatusMaquina.BLOQUEADA
        db.commit()
        
        logger.warning(f"Máquina bloqueada: {maquina.nome} (ID: {maquina.id}) - Motivo: {motivo}")
        return True
    
    @staticmethod
    def desbloquear_maquina(db: Session, maquina_id: int) -> bool:
        """Desbloqueia uma máquina"""
        maquina = db.query(Maquina).filter(Maquina.id == maquina_id).first()
        if not maquina:
            return False
        
        maquina.status = StatusMaquina.ONLINE
        db.commit()
        
        logger.info(f"Máquina desbloqueada: {maquina.nome} (ID: {maquina.id})")
        return True
    
    @staticmethod
    def get_estatisticas_maquinas(db: Session, cliente_id: Optional[int] = None) -> Dict[str, Any]:
        """Retorna estatísticas das máquinas"""
        query = db.query(Maquina)
        if cliente_id:
            query = query.filter(Maquina.cliente_id == cliente_id)
        
        total = query.count()
        
        # Contar por status
        status_counts = {}
        for status in [StatusMaquina.ONLINE, StatusMaquina.OFFLINE, StatusMaquina.BLOQUEADA, StatusMaquina.MANUTENCAO]:
            count = query.filter(Maquina.status == status).count()
            status_counts[status.value] = count
        
        # Métricas médias das últimas 24 horas
        limite = datetime.utcnow() - timedelta(hours=24)
        
        metricas = db.query(
            func.avg(MaquinaMetrica.cpu_uso).label('cpu_medio'),
            func.avg(MaquinaMetrica.memoria_uso).label('memoria_medio'),
            func.avg(MaquinaMetrica.disco_uso).label('disco_medio')
        ).filter(MaquinaMetrica.created_at >= limite).first()
        
        return {
            "total": total,
            "status": status_counts,
            "metricas_medias": {
                "cpu": round(metricas.cpu_medio or 0, 2),
                "memoria": round(metricas.memoria_medio or 0, 2),
                "disco": round(metricas.disco_medio or 0, 2)
            },
            "uptime_24h": round((status_counts.get('online', 0) / total * 100) if total > 0 else 0, 2)
        }
    
    @staticmethod
    def get_maquinas_por_cliente(db: Session, cliente_id: int) -> List[Maquina]:
        """Retorna máquinas de um cliente"""
        return db.query(Maquina).filter(
            Maquina.cliente_id == cliente_id
        ).order_by(Maquina.ultima_conexao.desc()).all()
    
    @staticmethod
    def get_metricas_recentes(db: Session, maquina_id: int, limite: int = 100) -> List[MaquinaMetrica]:
        """Retorna métricas recentes de uma máquina"""
        return db.query(MaquinaMetrica).filter(
            MaquinaMetrica.maquina_id == maquina_id
        ).order_by(MaquinaMetrica.timestamp.desc()).limit(limite).all()
