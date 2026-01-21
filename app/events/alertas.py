import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

class AlertaService:
    @staticmethod
    def enviar_email(destinatario: str, assunto: str, corpo: str, html: Optional[str] = None) -> bool:
        """Envia email usando SMTP"""
        if not all([settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER, settings.SMTP_PASSWORD]):
            logger.warning("SMTP não configurado, email não enviado")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = assunto
            msg['From'] = settings.EMAIL_FROM
            msg['To'] = destinatario
            
            # Parte texto
            part1 = MIMEText(corpo, 'plain')
            msg.attach(part1)
            
            # Parte HTML se fornecida
            if html:
                part2 = MIMEText(html, 'html')
                msg.attach(part2)
            
            # Enviar email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email enviado para {destinatario}: {assunto}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {str(e)}")
            return False
    
    @staticmethod
    def enviar_webhook(url: str, data: Dict[str, Any]) -> bool:
        """Envia alerta via webhook"""
        try:
            import httpx
            response = httpx.post(url, json=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Webhook enviado para {url}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar webhook: {str(e)}")
            return False
    
    @staticmethod
    def criar_alerta_sistema(tipo: str, severidade: str, mensagem: str, dados: Dict[str, Any] = None):
        """Cria um alerta no sistema"""
        alerta = {
            "tipo": tipo,
            "severidade": severidade,
            "mensagem": mensagem,
            "dados": dados or {},
            "timestamp": datetime.utcnow().isoformat(),
            "sistema": "nzilacode_control"
        }
        
        # Aqui você pode salvar no banco de dados, enviar para um serviço de mensagens, etc.
        logger.info(f"Alerta criado: {tipo} - {mensagem}")
        return alerta

# Funções de alerta específicas
def enviar_alerta_novo_cliente(cliente):
    """Envia alerta de novo cliente"""
    assunto = f"Novo Cliente: {cliente.nome}"
    corpo = f"""
    Novo cliente registrado no sistema:
    
    Nome: {cliente.nome}
    Email: {cliente.email}
    Empresa: {cliente.empresa or 'N/A'}
    Tipo: {cliente.tipo}
    
    Data: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}
    """
    
    AlertaService.enviar_email(
        destinatario="admin@nzilacode.com",
        assunto=assunto,
        corpo=corpo
    )
    
    AlertaService.criar_alerta_sistema(
        tipo="novo_cliente",
        severidade="info",
        mensagem=f"Novo cliente registrado: {cliente.email}",
        dados={"cliente_id": cliente.id, "email": cliente.email}
    )

def enviar_alerta_licenca_expirada(licenca):
    """Envia alerta de licença expirada"""
    assunto = f"Licença Expirada: {licenca.chave_licenca}"
    corpo = f"""
    Licença expirada:
    
    Chave: {licenca.chave_licenca}
    Cliente ID: {licenca.cliente_id}
    Data de expiração: {licenca.data_expiracao}
    
    Data: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}
    """
    
    AlertaService.enviar_email(
        destinatario="suporte@nzilacode.com",
        assunto=assunto,
        corpo=corpo
    )
    
    # Enviar para o cliente também
    # Obter email do cliente do banco de dados
    
    AlertaService.criar_alerta_sistema(
        tipo="licenca_expirada",
        severidade="alta",
        mensagem=f"Licença expirada: {licenca.chave_licenca}",
        dados={"licenca_id": licenca.id, "cliente_id": licenca.cliente_id}
    )

def enviar_alerta_maquina_offline(maquina):
    """Envia alerta de máquina offline"""
    assunto = f"Máquina Offline: {maquina.nome}"
    corpo = f"""
    Máquina offline detectada:
    
    Nome: {maquina.nome}
    ID: {maquina.id}
    Cliente ID: {maquina.cliente_id}
    Última conexão: {maquina.ultima_conexao}
    
    Data: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}
    """
    
    AlertaService.enviar_email(
        destinatario="monitoramento@nzilacode.com",
        assunto=assunto,
        corpo=corpo
    )
    
    AlertaService.criar_alerta_sistema(
        tipo="maquina_offline",
        severidade="media",
        mensagem=f"Máquina offline: {maquina.nome}",
        dados={"maquina_id": maquina.id, "cliente_id": maquina.cliente_id}
    )

def enviar_alerta_maquina_suspeita(maquina, motivo: str):
    """Envia alerta de atividade suspeita na máquina"""
    assunto = f"Atividade Suspeita: {maquina.nome}"
    corpo = f"""
    Atividade suspeita detectada na máquina:
    
    Nome: {maquina.nome}
    ID: {maquina.id}
    Cliente ID: {maquina.cliente_id}
    Motivo: {motivo}
    
    Data: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}
    """
    
    AlertaService.enviar_email(
        destinatario="seguranca@nzilacode.com",
        assunto=assunto,
        corpo=corpo
    )
    
    AlertaService.criar_alerta_sistema(
        tipo="atividade_suspeita",
        severidade="alta",
        mensagem=f"Atividade suspeita na máquina {maquina.nome}: {motivo}",
        dados={"maquina_id": maquina.id, "cliente_id": maquina.cliente_id, "motivo": motivo}
    )

def enviar_alerta_pagamento_pendente(assinatura):
    """Envia alerta de pagamento pendente"""
    assunto = f"Pagamento Pendente: Assinatura {assinatura.plano}"
    corpo = f"""
    Pagamento pendente detectado:
    
    Assinatura ID: {assinatura.id}
    Cliente ID: {assinatura.cliente_id}
    Plano: {assinatura.plano}
    Valor: {assinatura.valor}
    Data de vencimento: {assinatura.data_fim}
    
    Data: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}
    """
    
    AlertaService.enviar_email(
        destinatario="financeiro@nzilacode.com",
        assunto=assunto,
        corpo=corpo
    )
    
    AlertaService.criar_alerta_sistema(
        tipo="pagamento_pendente",
        severidade="media",
        mensagem=f"Pagamento pendente para assinatura {assinatura.plano}",
        dados={"assinatura_id": assinatura.id, "cliente_id": assinatura.cliente_id}
    )
