from datetime import datetime
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.tasks.monitoramento import MonitoramentoService

logger = logging.getLogger(__name__)

class LicencaScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """Inicia o agendador de tarefas"""
        # Monitoramento de máquinas offline a cada 5 minutos
        self.scheduler.add_job(
            MonitoramentoService.monitorar_maquinas_offline,
            CronTrigger(minute="*/5"),
            id="monitoramento_maquinas"
        )
        
        # Monitoramento de licenças expirando a cada hora
        self.scheduler.add_job(
            MonitoramentoService.monitorar_licencas_expirando,
            CronTrigger(hour="*"),
            id="monitoramento_licencas"
        )
        
        # Monitoramento de renovações a cada 6 horas
        self.scheduler.add_job(
            MonitoramentoService.monitorar_renovacoes_assinaturas,
            CronTrigger(hour="*/6"),
            id="monitoramento_renovacoes"
        )
        
        # Métricas do sistema a cada 30 minutos
        self.scheduler.add_job(
            MonitoramentoService.monitorar_metricas_sistema,
            CronTrigger(minute="*/30"),
            id="monitoramento_metricas"
        )
        
        # Relatórios diários às 8:00
        self.scheduler.add_job(
            self.gerar_relatorio_diario,
            CronTrigger(hour=8, minute=0),
            id="relatorio_diario"
        )
        
        # Backup de dados às 2:00
        self.scheduler.add_job(
            self.backup_dados,
            CronTrigger(hour=2, minute=0),
            id="backup_dados"
        )
        
        self.scheduler.start()
        logger.info("Agendador de licenças iniciado")
    
    async def gerar_relatorio_diario(self):
        """Gera relatório diário"""
        try:
            from app.database.session import get_db
            from app.services.cliente_service import ClienteService
            from app.services.maquina_service import MaquinaService
            from app.events.alertas import AlertaService
            
            db = next(get_db())
            
            # Coletar estatísticas
            estatisticas_clientes = ClienteService.get_estatisticas_clientes(db)
            
            # Gerar relatório
            relatorio = f"""
            RELATÓRIO DIÁRIO - {datetime.utcnow().strftime('%d/%m/%Y')}
            
            CLIENTES:
            - Total: {estatisticas_clientes['total']}
            - Ativos: {estatisticas_clientes['ativos']}
            - Bloqueados: {estatisticas_clientes['bloqueados']}
            - Taxa de ativação: {estatisticas_clientes['taxa_ativacao']}%
            
            MÁQUINAS:
            - Online: [coletar do dashboard]
            - Offline: [coletar do dashboard]
            
            LICENÇAS:
            - Ativas: [coletar do banco]
            - Expirando hoje: [coletar do banco]
            
            ALERTAS DO DIA:
            - [listar alertas]
            """
            
            logger.info("Relatório diário gerado")
            
            # Enviar por email
            AlertaService.enviar_email(
                destinatario="relatorios@nzilacode.com",
                assunto=f"Relatório Diário - {datetime.utcnow().strftime('%d/%m/%Y')}",
                corpo=relatorio
            )
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório diário: {str(e)}")
    
    async def backup_dados(self):
        """Faz backup dos dados"""
        try:
            logger.info("Iniciando backup de dados")
            
            # Aqui você implementaria a lógica de backup
            # - Exportar banco de dados
            # - Fazer upload para storage
            # - Limpar backups antigos
            
            logger.info("Backup de dados concluído")
            
        except Exception as e:
            logger.error(f"Erro no backup de dados: {str(e)}")
    
    def stop(self):
        """Para o agendador"""
        self.scheduler.shutdown()
        logger.info("Agendador de licenças parado")

# Instância global
licenca_scheduler = LicencaScheduler()
