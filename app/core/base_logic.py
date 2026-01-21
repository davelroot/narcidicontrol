from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

from app.config import settings
from app.models.cliente import Cliente, StatusCliente
from app.models.maquina import Maquina
from app.models.licenca import Licenca, Assinatura
from app.events.alertas import AlertaService

logger = logging.getLogger(__name__)

class MLEngine:
    """Motor de Machine Learning para previsões"""
    
    def __init__(self):
        self.model_path = os.path.join(settings.ML_MODEL_PATH, "churn_model.pkl")
        self.scaler_path = os.path.join(settings.ML_MODEL_PATH, "scaler.pkl")
        self.model = None
        self.scaler = None
        
        # Carregar modelo se existir
        self._load_model()
    
    def _load_model(self):
        """Carrega modelo treinado"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                logger.info("Modelo ML carregado com sucesso")
            else:
                logger.info("Modelo ML não encontrado, será treinado quando necessário")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo ML: {str(e)}")
    
    def prepare_features(self, db: Session, cliente_id: int) -> Optional[Dict[str, float]]:
        """Prepara features para previsão de churn"""
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                return None
            
            # Coletar dados do cliente
            assinatura = db.query(Assinatura).filter(
                Assinatura.cliente_id == cliente_id,
                Assinatura.status == "ativa"
            ).first()
            
            maquinas = db.query(Maquina).filter(Maquina.cliente_id == cliente_id).all()
            
            licencas = db.query(Licenca).filter(Licenca.cliente_id == cliente_id).all()
            
            # Calcular features
            features = {
                # Dados do cliente
                "tempo_assinatura_dias": (
                    (datetime.utcnow() - cliente.data_assinatura).days 
                    if cliente.data_assinatura else 0
                ),
                "tipo_cliente_numeric": self._map_tipo_cliente(cliente.tipo),
                
                # Uso
                "total_maquinas": len(maquinas),
                "maquinas_online": sum(1 for m in maquinas if m.status == "online"),
                "licencas_ativas": sum(1 for l in licencas if l.status == "ativa"),
                
                # Pagamentos
                "valor_medio_mensal": float(assinatura.valor) if assinatura else 0,
                "atraso_pagamento_dias": self._calcular_atraso_pagamento(db, cliente_id),
                
                # Suporte
                "tickets_suporte_30d": self._contar_tickets_suporte(db, cliente_id, 30),
                "tickets_suporte_abertos": self._contar_tickets_abertos(db, cliente_id),
                
                # Uso do sistema
                "uso_diario_medio_horas": self._calcular_uso_medio(db, cliente_id),
                "dias_sem_conexao": self._calcular_dias_sem_conexao(db, cliente_id),
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Erro ao preparar features: {str(e)}")
            return None
    
    def predict_churn_risk(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Previsão de risco de churn"""
        try:
            if not self.model or not self.scaler:
                # Se não há modelo, usar regras simples
                return self._predict_simple(features)
            
            # Preparar dados para modelo
            feature_names = [
                'tempo_assinatura_dias', 'tipo_cliente_numeric', 'total_maquinas',
                'maquinas_online', 'licencas_ativas', 'valor_medio_mensal',
                'atraso_pagamento_dias', 'tickets_suporte_30d', 'tickets_suporte_abertos',
                'uso_diario_medio_horas', 'dias_sem_conexao'
            ]
            
            # Garantir que todas as features existem
            input_data = [features.get(f, 0) for f in feature_names]
            
            # Normalizar
            input_scaled = self.scaler.transform([input_data])
            
            # Prever
            proba = self.model.predict_proba(input_scaled)[0]
            prediction = self.model.predict(input_scaled)[0]
            
            return {
                "risco_churn": bool(prediction),
                "probabilidade": float(proba[1]),  # Probabilidade de churn
                "nivel_risco": self._classificar_risco(float(proba[1])),
                "features_importantes": self._get_important_features(features)
            }
            
        except Exception as e:
            logger.error(f"Erro na previsão de churn: {str(e)}")
            return self._predict_simple(features)
    
    def train_model(self, db: Session):
        """Treina modelo com dados históricos"""
        try:
            logger.info("Iniciando treinamento do modelo de churn")
            
            # Coletar dados históricos
            data = self._collect_training_data(db)
            
            if len(data) < 50:  # Mínimo de exemplos
                logger.warning(f"Dados insuficientes para treinamento: {len(data)} exemplos")
                return
            
            # Separar features e target
            df = pd.DataFrame(data)
            X = df.drop('churn', axis=1)
            y = df['churn']
            
            # Normalizar
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Treinar modelo
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            
            self.model.fit(X_scaled, y)
            
            # Salvar modelo
            os.makedirs(settings.ML_MODEL_PATH, exist_ok=True)
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            logger.info(f"Modelo treinado com {len(data)} exemplos e salvo")
            
        except Exception as e:
            logger.error(f"Erro no treinamento do modelo: {str(e)}")
    
    def _predict_simple(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Previsão simples baseada em regras"""
        risco = 0.0
        fatores = []
        
        # Regras básicas
        if features.get("atraso_pagamento_dias", 0) > 15:
            risco += 0.4
            fatores.append("Atraso no pagamento")
        
        if features.get("dias_sem_conexao", 0) > 30:
            risco += 0.3
            fatores.append("Inatividade prolongada")
        
        if features.get("tickets_suporte_30d", 0) > 5:
            risco += 0.2
            fatores.append("Muitos tickets de suporte")
        
        if features.get("maquinas_online", 0) == 0 and features.get("total_maquinas", 0) > 0:
            risco += 0.3
            fatores.append("Todas máquinas offline")
        
        return {
            "risco_churn": risco > 0.5,
            "probabilidade": min(risco, 1.0),
            "nivel_risco": self._classificar_risco(risco),
            "fatores_risco": fatores,
            "metodo": "regras"
        }
    
    def _classificar_risco(self, probabilidade: float) -> str:
        """Classifica nível de risco"""
        if probabilidade >= 0.8:
            return "critico"
        elif probabilidade >= 0.6:
            return "alto"
        elif probabilidade >= 0.4:
            return "medio"
        elif probabilidade >= 0.2:
            return "baixo"
        else:
            return "muito_baixo"
    
    def _map_tipo_cliente(self, tipo: str) -> int:
        """Mapeia tipo de cliente para número"""
        mapping = {
            "free": 1,
            "basic": 2,
            "pro": 3,
            "enterprise": 4
        }
        return mapping.get(tipo, 0)
    
    def _calcular_atraso_pagamento(self, db: Session, cliente_id: int) -> int:
        """Calcula dias de atraso no pagamento"""
        from app.models.licenca import Pagamento
        
        ultimo_pagamento = db.query(Pagamento).filter(
            Pagamento.assinatura.has(cliente_id=cliente_id),
            Pagamento.status == "pago"
        ).order_by(Pagamento.data_pagamento.desc()).first()
        
        if not ultimo_pagamento:
            return 0
        
        dias_atraso = (datetime.utcnow() - ultimo_pagamento.data_pagamento).days
        return max(0, dias_atraso - 30)  # Considerar atraso após 30 dias
    
    def _contar_tickets_suporte(self, db: Session, cliente_id: int, dias: int) -> int:
        """Conta tickets de suporte"""
        # TODO: Implementar quando tiver modelo de tickets
        return 0
    
    def _contar_tickets_abertos(self, db: Session, cliente_id: int) -> int:
        """Conta tickets abertos"""
        # TODO: Implementar quando tiver modelo de tickets
        return 0
    
    def _calcular_uso_medio(self, db: Session, cliente_id: int) -> float:
        """Calcula uso médio diário em horas"""
        from app.models.maquina import MaquinaMetrica
        
        # Últimos 7 dias
        limite = datetime.utcnow() - timedelta(days=7)
        
        metricas = db.query(MaquinaMetrica).filter(
            MaquinaMetrica.maquina.has(cliente_id=cliente_id),
            MaquinaMetrica.created_at >= limite
        ).count()
        
        # Estimativa: cada métrica representa 5 minutos de atividade
        horas = (metricas * 5) / 60 / 7  # Horas por dia
        return round(horas, 2)
    
    def _calcular_dias_sem_conexao(self, db: Session, cliente_id: int) -> int:
        """Calcula dias desde a última conexão"""
        ultima_maquina = db.query(Maquina).filter(
            Maquina.cliente_id == cliente_id
        ).order_by(Maquina.ultima_conexao.desc()).first()
        
        if not ultima_maquina or not ultima_maquina.ultima_conexao:
            return 999  # Nunca conectou
        
        dias = (datetime.utcnow() - ultima_maquina.ultima_conexao).days
        return dias
    
    def _collect_training_data(self, db: Session) -> List[Dict]:
        """Coleta dados históricos para treinamento"""
        # TODO: Implementar coleta de dados históricos
        # Isso requer dados históricos de clientes que cancelaram
        return []
    
    def _get_important_features(self, features: Dict[str, float]) -> List[Dict]:
        """Identifica features mais importantes para a previsão"""
        if not self.model:
            return []
        
        feature_names = [
            'tempo_assinatura_dias', 'tipo_cliente_numeric', 'total_maquinas',
            'maquinas_online', 'licencas_ativas', 'valor_medio_mensal',
            'atraso_pagamento_dias', 'tickets_suporte_30d', 'tickets_suporte_abertos',
            'uso_diario_medio_horas', 'dias_sem_conexao'
        ]
        
        importances = []
        if hasattr(self.model, 'feature_importances_'):
            for name, importance in zip(feature_names, self.model.feature_importances_):
                importances.append({
                    "feature": name,
                    "importance": float(importance),
                    "value": features.get(name, 0)
                })
        
        # Ordenar por importância
        importances.sort(key=lambda x: x["importance"], reverse=True)
        return importances[:5]  # Top 5

class SistemaCore:
    """Classe core do sistema"""
    
    def __init__(self):
        self.ml_engine = MLEngine()
        self.alerta_service = AlertaService()
    
    def analisar_cliente(self, db: Session, cliente_id: int) -> Dict[str, Any]:
        """Analisa cliente completo"""
        try:
            # Preparar features
            features = self.ml_engine.prepare_features(db, cliente_id)
            if not features:
                return {"error": "Cliente não encontrado"}
            
            # Prever churn
            churn_prediction = self.ml_engine.predict_churn_risk(features)
            
            # Analisar uso
            uso_analysis = self._analisar_uso(db, cliente_id)
            
            # Sugerir upgrades
            upgrade_suggestion = self._sugerir_upgrade(db, cliente_id)
            
            # Verificar comportamento suspeito
            comportamento = self._verificar_comportamento(db, cliente_id)
            
            return {
                "cliente_id": cliente_id,
                "churn_analysis": churn_prediction,
                "uso_analysis": uso_analysis,
                "upgrade_suggestion": upgrade_suggestion,
                "comportamento_suspeito": comportamento,
                "features": features,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro na análise do cliente {cliente_id}: {str(e)}")
            return {"error": str(e)}
    
    def _analisar_uso(self, db: Session, cliente_id: int) -> Dict[str, Any]:
        """Analisa padrão de uso do cliente"""
        from app.models.maquina import MaquinaMetrica
        from sqlalchemy import func
        
        # Últimos 30 dias
        limite = datetime.utcnow() - timedelta(days=30)
        
        # Coletar métricas
        metricas = db.query(
            func.avg(MaquinaMetrica.cpu_uso).label('cpu_medio'),
            func.avg(MaquinaMetrica.memoria_uso).label('memoria_medio'),
            func.avg(MaquinaMetrica.disco_uso).label('disco_medio'),
            func.count(MaquinaMetrica.id).label('total_metricas')
        ).filter(
            MaquinaMetrica.maquina.has(cliente_id=cliente_id),
            MaquinaMetrica.created_at >= limite
        ).first()
        
        # Calcular padrão
        padrao = "baixo"
        if metricas.total_metricas > 1000:
            padrao = "alto"
        elif metricas.total_metricas > 500:
            padrao = "medio"
        
        # Verificar picos
        picos = self._detectar_picos_uso(db, cliente_id)
        
        return {
            "padrao_uso": padrao,
            "cpu_medio": round(metricas.cpu_medio or 0, 2),
            "memoria_medio": round(metricas.memoria_medio or 0, 2),
            "disco_medio": round(metricas.disco_medio or 0, 2),
            "total_metricas": metricas.total_metricas or 0,
            "picos_detectados": picos,
            "recomendacao": self._gerar_recomendacao_uso(padrao, metricas)
        }
    
    def _sugerir_upgrade(self, db: Session, cliente_id: int) -> Dict[str, Any]:
        """Sugere upgrade de assinatura"""
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            return {"sugestao": None, "motivo": "Cliente não encontrado"}
        
        # Verificar uso vs limite
        maquinas = db.query(Maquina).filter(Maquina.cliente_id == cliente_id).count()
        
        # Verificar recursos utilizados
        from app.models.maquina import MaquinaMetrica
        from sqlalchemy import func
        
        uso_recursos = db.query(
            func.avg(MaquinaMetrica.cpu_uso).label('cpu'),
            func.avg(MaquinaMetrica.memoria_uso).label('memoria')
        ).filter(
            MaquinaMetrica.maquina.has(cliente_id=cliente_id)
        ).first()
        
        sugerir_upgrade = False
        motivos = []
        
        # Verificar limites
        if maquinas >= cliente.limite_maquinas * 0.8:  # 80% do limite
            sugerir_upgrade = True
            motivos.append(f"Usando {maquinas}/{cliente.limite_maquinas} máquinas")
        
        if uso_recursos.cpu and uso_recursos.cpu > 70:
            sugerir_upgrade = True
            motivos.append(f"Uso médio de CPU: {uso_recursos.cpu:.1f}%")
        
        # Determinar próximo plano
        planos = ["free", "basic", "pro", "enterprise"]
        try:
            indice_atual = planos.index(cliente.tipo.value if hasattr(cliente.tipo, 'value') else cliente.tipo)
            proximo_plano = planos[indice_atual + 1] if indice_atual + 1 < len(planos) else None
        except (ValueError, IndexError):
            proximo_plano = "pro"
        
        return {
            "sugerir_upgrade": sugerir_upgrade,
            "plano_atual": cliente.tipo.value if hasattr(cliente.tipo, 'value') else cliente.tipo,
            "proximo_plano": proximo_plano,
            "motivos": motivos,
            "limites_atingidos": {
                "maquinas": maquinas,
                "limite_maquinas": cliente.limite_maquinas,
                "percentual_uso": round((maquinas / cliente.limite_maquinas * 100) if cliente.limite_maquinas > 0 else 0, 1)
            }
        }
    
    def _verificar_comportamento(self, db: Session, cliente_id: int) -> Dict[str, Any]:
        """Verifica comportamento suspeito"""
        suspeitas = []
        
        # Verificar múltiplas máquinas offline
        maquinas_offline = db.query(Maquina).filter(
            Maquina.cliente_id == cliente_id,
            Maquina.status == "offline"
        ).count()
        
        if maquinas_offline >= 3:
            suspeitas.append(f"{maquinas_offline} máquinas offline simultaneamente")
        
        # Verificar tentativas de acesso
        # TODO: Implementar quando tiver logs de acesso
        
        # Verificar alterações frequentes de configuração
        # TODO: Implementar quando tiver histórico de alterações
        
        return {
            "suspeito": len(suspeitas) > 0,
            "suspeitas": suspeitas,
            "nivel_severidade": "alto" if len(suspeitas) > 2 else "medio" if len(suspeitas) > 0 else "baixo"
        }
    
    def _detectar_picos_uso(self, db: Session, cliente_id: int) -> List[Dict]:
        """Detecta picos de uso"""
        # TODO: Implementar detecção de picos
        return []
    
    def _gerar_recomendacao_uso(self, padrao: str, metricas) -> str:
        """Gera recomendação baseada no padrão de uso"""
        if padrao == "alto":
            return "Considerar otimização de recursos ou upgrade"
        elif padrao == "medio":
            return "Uso adequado, monitorar crescimento"
        else:
            return "Uso baixo, considerar treinamento ou suporte"
    
    def monitorar_todos_clientes(self, db: Session):
        """Monitora todos os clientes ativos"""
        try:
            clientes = db.query(Cliente).filter(Cliente.status == StatusCliente.ATIVO).all()
            
            for cliente in clientes:
                analise = self.analisar_cliente(db, cliente.id)
                
                # Verificar se precisa alertar
                if analise.get("churn_analysis", {}).get("nivel_risco") in ["alto", "critico"]:
                    self.alerta_service.criar_alerta_sistema(
                        tipo="risco_churn_alto",
                        severidade="alta",
                        mensagem=f"Alto risco de churn detectado para cliente {cliente.email}",
                        dados={"cliente_id": cliente.id, "analise": analise}
                    )
                
                if analise.get("comportamento_suspeito", {}).get("suspeito"):
                    self.alerta_service.criar_alerta_sistema(
                        tipo="comportamento_suspeito",
                        severidade="alta",
                        mensagem=f"Comportamento suspeito detectado para cliente {cliente.email}",
                        dados={"cliente_id": cliente.id, "analise": analise}
                    )
            
            logger.info(f"Monitoramento concluído para {len(clientes)} clientes")
            
        except Exception as e:
            logger.error(f"Erro no monitoramento de clientes: {str(e)}")

# Instância global do sistema
sistema_core = SistemaCore()
