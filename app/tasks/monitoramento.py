from datetime import datetime, timedelta
import asyncio
import logging
from typing import List, Dict, Any

from app.database.session import get_db
from app.services.maquina_service import MaquinaService
from app.services.licenca_service import LicencaService, AssinaturaService
from app.events.alertas import enviar_alerta_licenca_expirada, enviar_alerta_maquina_offline

logger = logging.getLogger(__name__)

class MonitoramentoService:
    @staticmethod
    async def monitorar_maquinas_offline():
        """Monitora máquinas offline"""
        logger.info("Iniciando monitoramento de máquinas offline")
        
        try:
            db = next(get_db())
            
            # Verificar máquinas offline há mais de 5 minutos
            maquinas_offline = MaquinaService.verificar_maquinas_offline(db, minutos_offline=5)
            
            for maquina in maquinas_offline:
                logger.warning(f"Máquina offline detectada: {maquina.nome} (ID: {maquina.id})")
                # Alerta já enviado pelo serviço
            
            logger.info(f"Monitoramento concluído: {len(maquinas_offline)} máquinas offline")
            
        except Exception as e:
            logger.error(f"Erro no monitoramento de máquinas: {str(e)}")
    
    @staticmethod
    async def monitorar_licencas_expirando():
        """Monitora licenças prestes a expirar"""
        logger.info("Iniciando monitoramento de licenças expirando")
        
        try:
            db = next(get_db())
            
            # Verificar licenças expirando em 7 dias
            licencas = LicencaService.get_licencas_expirando(db, dias=7)
            
            for licenca in licencas:
                dias_restantes = (licenca.data_expiracao - datetime.utcnow()).days
                logger.warning(
                    f"Licença expirando em {dias_restantes} dias: "
                    f"{licenca.chave_licenca} (Cliente: {licenca.cliente_id})"
                )
                
                # Enviar alerta se faltar menos de 3 dias
                if dias_restantes <= 3:
                    enviar_alerta_licenca_expirada(licenca)
            
            logger.info(f"Monitoramento concluído: {len(licencas)} licenças expirando")
            
        except Exception as e:
            logger.error(f"Erro no monitoramento de licenças: {str(e)}")
    
    @staticmethod
    async def monitorar_renovacoes_assinaturas():
        """Monitora renovações de assinaturas"""
        logger.info("Iniciando monitoramento de renovações")
        
        try:
            db = next(get_db())
            
            # Verificar assinaturas para renovação
            assinaturas = AssinaturaService.verificar_renovacoes(db)
            
            for assinatura in assinaturas:
                logger.info(
                    f"Assinatura para renovação: {assinatura.plano} "
                    f"(Cliente: {assinatura.cliente_id})"
                )
                
                # Tentar renovação automática se configurada
                if assinatura.renovacao_automatica:
                    AssinaturaService.renovar_assinatura(db, assinatura.id)
            
            logger.info(f"Monitoramento concluído: {len(assinaturas)} assinaturas para renovação")
            
        except Exception as e:
            logger.error(f"Erro no monitoramento de renovações: {str(e)}")
    
    @staticmethod
    async def monitorar_metricas_sistema():
        """Monitora métricas do sistema"""
        logger.info("Iniciando monitoramento de métricas")
        
        try:
            db = next(get_db())
            
            # Coletar métricas
            from sqlalchemy import func
            from app.models.maquina import MaquinaMetrica
            
            # Última hora
            limite = datetime.utcnow() - timedelta(hours=1)
            
            metricas = db.query(
                func.avg(MaquinaMetrica.cpu_uso).label('cpu_medio'),
                func.avg(MaquinaMetrica.memoria_uso).label('memoria_medio'),
                func.avg(MaquinaMetrica.disco_uso).label('disco_medio'),
                func.count(MaquinaMetrica.id).label('total_metricas')
            ).filter(MaquinaMetrica.created_at >= limite).first()
            
            logger.info(
                f"Métricas do sistema (última hora): "
                f"CPU: {metricas.cpu_medio:.2f}%, "
                f"Memória: {metricas.memoria_medio:.2f}%, "
                f"Disco: {metricas.disco_medio:.2f}%, "
                f"Total de métricas: {metricas.total_metricas}"
            )
            
        except Exception as e:
            logger.error(f"Erro no monitoramento de métricas: {str(e)}")

async def executar_monitoramento_continuo():
    """Executa monitoramento contínuo"""
    while True:
        try:
            # Executar todos os monitoramentos
            await MonitoramentoService.monitorar_maquinas_offline()
            await MonitoramentoService.monitorar_licencas_expirando()
            await MonitoramentoService.monitorar_renovacoes_assinaturas()
            await MonitoramentoService.monitorar_metricas_sistema()
            
            # Esperar 1 minuto antes da próxima execução
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Erro no monitoramento contínuo: {str(e)}")
            await asyncio.sleep(60)  # Esperar mesmo em caso de erro
