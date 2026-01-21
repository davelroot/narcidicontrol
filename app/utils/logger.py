import logging
import sys
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from typing import Dict, Any

def setup_logging():
    """Configura logging"""
    # Formatar
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Handler para arquivo
    file_handler = RotatingFileHandler(
        'logs/nzilacode_control.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Loggers específicos
    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn").addHandler(console_handler)
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").addHandler(console_handler)

class JsonLogger:
    """Logger que gera logs em formato JSON"""
    
    @staticmethod
    def log_event(event_type: str, data: Dict[str, Any], level: str = "info"):
        """Log de eventos em formato JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data,
            "level": level
        }
        
        logger = logging.getLogger("json_logger")
        
        if level == "info":
            logger.info(json.dumps(log_data))
        elif level == "warning":
            logger.warning(json.dumps(log_data))
        elif level == "error":
            logger.error(json.dumps(log_data))
        elif level == "critical":
            logger.critical(json.dumps(log_data))
    
    @staticmethod
    def log_audit(action: str, user: str, resource: str, details: Dict[str, Any]):
        """Log de auditoria"""
        JsonLogger.log_event(
            "audit",
            {
                "action": action,
                "user": user,
                "resource": resource,
                "details": details
            },
            level="info"
        )
    
    @staticmethod
    def log_security_event(event: str, severity: str, details: Dict[str, Any]):
        """Log de eventos de segurança"""
        JsonLogger.log_event(
            "security",
            {
                "event": event,
                "severity": severity,
                "details": details
            },
            level="warning" if severity in ["medium", "high"] else "info"
        )
