from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.models.cliente import Cliente, PerfilCliente, PermissaoCliente, StatusCliente
from app.schemas.cliente import ClienteCreate, ClienteUpdate, PerfilClienteCreate, PermissaoClienteCreate
from app.utils.security import get_password_hash, verify_password
from app.events.alertas import enviar_alerta_novo_cliente

logger = logging.getLogger(__name__)

class ClienteService:
    @staticmethod
    def criar_cliente(db: Session, cliente_data: ClienteCreate) -> Cliente:
        """Cria um novo cliente"""
        # Verificar se email já existe
        if db.query(Cliente).filter(Cliente.email == cliente_data.email).first():
            raise ValueError("Email já cadastrado")
        
        # Verificar CPF/CNPJ se fornecido
        if cliente_data.cpf_cnpj:
            if db.query(Cliente).filter(Cliente.cpf_cnpj == cliente_data.cpf_cnpj).first():
                raise ValueError("CPF/CNPJ já cadastrado")
        
        # Criar cliente
        db_cliente = Cliente(
            nome=cliente_data.nome,
            email=cliente_data.email,
            cpf_cnpj=cliente_data.cpf_cnpj,
            telefone=cliente_data.telefone,
            empresa=cliente_data.empresa,
            tipo=cliente_data.tipo,
            limite_maquinas=cliente_data.limite_maquinas,
            status=StatusCliente.PENDENTE
        )
        
        db.add(db_cliente)
        db.commit()
        db.refresh(db_cliente)
        
        # Criar perfil padrão
        perfil_padrao = PerfilCliente(
            cliente_id=db_cliente.id,
            nome_perfil="Administrador",
            tema_interface="dark",
            notificacoes_email=True,
            notificacoes_push=True
        )
        db.add(perfil_padrao)
        db.commit()
        
        # Criar permissões padrão
        permissoes_padrao = [
            PermissaoCliente(perfil_id=perfil_padrao.id, modulo="dashboard", acao="view", permitido=True),
            PermissaoCliente(perfil_id=perfil_padrao.id, modulo="maquinas", acao="manage", permitido=True),
            PermissaoCliente(perfil_id=perfil_padrao.id, modulo="licencas", acao="manage", permitido=True),
            PermissaoCliente(perfil_id=perfil_padrao.id, modulo="configuracoes", acao="manage", permitido=True),
        ]
        db.add_all(permissoes_padrao)
        db.commit()
        
        # Enviar alerta de novo cliente
        enviar_alerta_novo_cliente(db_cliente)
        
        logger.info(f"Novo cliente criado: {db_cliente.email} (ID: {db_cliente.id})")
        return db_cliente
    
    @staticmethod
    def atualizar_cliente(db: Session, cliente_id: int, update_data: ClienteUpdate) -> Optional[Cliente]:
        """Atualiza dados do cliente"""
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(cliente, key, value)
        
        cliente.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(cliente)
        
        logger.info(f"Cliente atualizado: {cliente.email} (ID: {cliente.id})")
        return cliente
    
    @staticmethod
    def obter_cliente(db: Session, cliente_id: int) -> Optional[Cliente]:
        """Obtém cliente por ID"""
        return db.query(Cliente).filter(Cliente.id == cliente_id).first()
    
    @staticmethod
    def obter_cliente_por_email(db: Session, email: str) -> Optional[Cliente]:
        """Obtém cliente por email"""
        return db.query(Cliente).filter(Cliente.email == email).first()
    
    @staticmethod
    def listar_clientes(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        tipo: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Cliente]:
        """Lista clientes com filtros"""
        query = db.query(Cliente)
        
        if tipo:
            query = query.filter(Cliente.tipo == tipo)
        if status:
            query = query.filter(Cliente.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def bloquear_cliente(db: Session, cliente_id: int, motivo: str) -> bool:
        """Bloqueia um cliente"""
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            return False
        
        cliente.status = StatusCliente.BLOQUEADO
        cliente.updated_at = datetime.utcnow()
        db.commit()
        
        # TODO: Adicionar registro de bloqueio
        logger.warning(f"Cliente bloqueado: {cliente.email} (ID: {cliente.id}) - Motivo: {motivo}")
        return True
    
    @staticmethod
    def ativar_cliente(db: Session, cliente_id: int) -> bool:
        """Ativa um cliente"""
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            return False
        
        cliente.status = StatusCliente.ATIVO
        cliente.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Cliente ativado: {cliente.email} (ID: {cliente.id})")
        return True
    
    @staticmethod
    def get_clientes_em_risco(db: Session, dias_para_expiracao: int = 7) -> List[Cliente]:
        """Retorna clientes com assinatura prestes a expirar"""
        data_limite = datetime.utcnow() + timedelta(days=dias_para_expiracao)
        
        clientes = db.query(Cliente).filter(
            and_(
                Cliente.status == StatusCliente.ATIVO,
                Cliente.data_expiracao <= data_limite,
                Cliente.data_expiracao > datetime.utcnow()
            )
        ).all()
        
        return clientes
    
    @staticmethod
    def get_estatisticas_clientes(db: Session) -> Dict[str, Any]:
        """Retorna estatísticas dos clientes"""
        total = db.query(func.count(Cliente.id)).scalar()
        ativos = db.query(func.count(Cliente.id)).filter(Cliente.status == StatusCliente.ATIVO).scalar()
        bloqueados = db.query(func.count(Cliente.id)).filter(Cliente.status == StatusCliente.BLOQUEADO).scalar()
        
        # Distribuição por tipo
        tipos = {}
        for tipo in ['free', 'basic', 'pro', 'enterprise']:
            count = db.query(func.count(Cliente.id)).filter(Cliente.tipo == tipo).scalar()
            tipos[tipo] = count
        
        return {
            "total": total,
            "ativos": ativos,
            "bloqueados": bloqueados,
            "distribuicao_tipo": tipos,
            "taxa_ativacao": round((ativos / total * 100) if total > 0 else 0, 2)
        }
