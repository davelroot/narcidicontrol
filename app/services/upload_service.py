import hashlib
import os
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, BinaryIO
from datetime import datetime
import logging
from fastapi import UploadFile, HTTPException
import boto3
from botocore.exceptions import ClientError

from app.models.upload import UploadVersao, HistoricoUpload, StatusUpload, TipoVersao
from app.models.cliente import Cliente
from app.schemas.upload import UploadVersaoCreate, VersionCheckRequest, VersionCheckResponse
from app.config import settings
from app.utils.security import generate_file_hash

logger = logging.getLogger(__name__)

class UploadService:
    # Configuração S3
    _s3_client = None
    
    @property
    def s3_client(self):
        if self._s3_client is None and settings.AWS_ACCESS_KEY_ID:
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.S3_REGION
            )
        return self._s3_client
    
    @staticmethod
    def salvar_arquivo_local(file: UploadFile, cliente_id: int, versao: str) -> tuple[str, str, int]:
        """Salva arquivo localmente"""
        # Criar diretório se não existir
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(cliente_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Gerar nome de arquivo único
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{versao}_{timestamp}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)
        
        # Salvar arquivo e calcular hash
        file_hash = hashlib.sha256()
        file_size = 0
        
        with open(filepath, "wb") as buffer:
            while content := file.file.read(8192):
                file_size += len(content)
                file_hash.update(content)
                buffer.write(content)
        
        hash_hex = file_hash.hexdigest()
        return filepath, hash_hex, file_size
    
    async def salvar_arquivo_s3(self, file: UploadFile, cliente_id: int, versao: str) -> tuple[str, str, int]:
        """Salva arquivo no S3"""
        if not self.s3_client:
            raise HTTPException(status_code=500, detail="S3 não configurado")
        
        # Gerar nome de arquivo único
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        s3_key = f"clientes/{cliente_id}/{versao}/{timestamp}_{file.filename}"
        
        # Upload para S3
        try:
            file.file.seek(0)
            file_size = 0
            file_hash = hashlib.sha256()
            
            # Para calcular hash e tamanho, precisamos ler o arquivo
            while content := file.file.read(8192):
                file_size += len(content)
                file_hash.update(content)
            
            # Reset para upload
            file.file.seek(0)
            
            self.s3_client.upload_fileobj(
                file.file,
                settings.S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={'ContentType': file.content_type}
            )
            
            hash_hex = file_hash.hexdigest()
            filepath = f"s3://{settings.S3_BUCKET_NAME}/{s3_key}"
            
            return filepath, hash_hex, file_size
            
        except ClientError as e:
            logger.error(f"Erro ao fazer upload para S3: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erro ao fazer upload: {str(e)}")
    
    async def fazer_upload_versao(
        self, 
        db: Session, 
        cliente_id: int, 
        file: UploadFile, 
        upload_data: UploadVersaoCreate
    ) -> UploadVersao:
        """Processa upload de nova versão"""
        # Verificar se cliente existe
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise ValueError("Cliente não encontrado")
        
        # Verificar se versão já existe
        existing = db.query(UploadVersao).filter(
            UploadVersao.cliente_id == cliente_id,
            UploadVersao.versao == upload_data.versao
        ).first()
        
        if existing:
            raise ValueError(f"Versão {upload_data.versao} já existe para este cliente")
        
        # Salvar arquivo
        if settings.AWS_ACCESS_KEY_ID and settings.S3_BUCKET_NAME:
            filepath, file_hash, file_size = await self.salvar_arquivo_s3(file, cliente_id, upload_data.versao)
        else:
            filepath, file_hash, file_size = self.salvar_arquivo_local(file, cliente_id, upload_data.versao)
        
        # Verificar hash se fornecido
        if upload_data.arquivo_hash and upload_data.arquivo_hash != file_hash:
            raise ValueError("Hash do arquivo não corresponde")
        
        # Criar registro de upload
        db_upload = UploadVersao(
            cliente_id=cliente_id,
            versao=upload_data.versao,
            tipo=upload_data.tipo,
            arquivo_path=filepath,
            arquivo_hash=file_hash,
            arquivo_tamanho=file_size,
            descricao=upload_data.descricao,
            notas_release=upload_data.notas_release,
            status=StatusUpload.PROCESSANDO,
            compatibilidade=upload_data.compatibilidade,
            requisitos=upload_data.requisitos,
            changelog=upload_data.changelog
        )
        
        db.add(db_upload)
        db.commit()
        db.refresh(db_upload)
        
        # Registrar histórico
        historico = HistoricoUpload(
            upload_id=db_upload.id,
            acao="upload_inicial",
            detalhes=f"Upload da versão {upload_data.versao}",
            usuario=f"cliente_{cliente_id}",
            ip_address="localhost"  # TODO: Obter IP real
        )
        db.add(historico)
        db.commit()
        
        logger.info(f"Novo upload registrado: {upload_data.versao} (Cliente: {cliente.email})")
        return db_upload
    
    @staticmethod
    def verificar_atualizacao(
        db: Session, 
        versao_atual: str, 
        sistema_operacional: str,
        cliente_id: Optional[int] = None
    ) -> VersionCheckResponse:
        """Verifica se há atualizações disponíveis"""
        # Converter versão para números
        def parse_version(version: str) -> tuple:
            return tuple(map(int, version.split('.')))
        
        current_version = parse_version(versao_atual)
        
        # Buscar versões disponíveis
        query = db.query(UploadVersao).filter(
            UploadVersao.status == StatusUpload.CONCLUIDO,
            UploadVersao.data_disponibilidade <= datetime.utcnow()
        )
        
        if cliente_id:
            # Versões específicas do cliente
            query = query.filter(UploadVersao.cliente_id == cliente_id)
        else:
            # Versões globais (cliente_id NULL ou específico)
            query = query.filter(UploadVersao.cliente_id.is_(None))
        
        # Filtrar por compatibilidade
        # TODO: Implementar filtro por sistema operacional
        
        versoes = query.order_by(UploadVersao.created_at.desc()).all()
        
        latest_version = None
        latest_parsed = (0, 0, 0)
        
        for versao in versoes:
            try:
                versao_parsed = parse_version(versao.versao)
                if versao_parsed > latest_parsed:
                    latest_parsed = versao_parsed
                    latest_version = versao
            except ValueError:
                continue
        
        if latest_version and latest_parsed > current_version:
            # Determinar tipo de atualização
            if latest_parsed[0] > current_version[0]:
                tipo_atualizacao = TipoVersao.MAJOR
                forcada = True
            elif latest_parsed[1] > current_version[1]:
                tipo_atualizacao = TipoVersao.MINOR
                forcada = True
            else:
                tipo_atualizacao = TipoVersao.PATCH
                forcada = False
            
            return VersionCheckResponse(
                atualizacao_disponivel=True,
                versao_latest=latest_version.versao,
                tipo_atualizacao=tipo_atualizacao,
                url_download=latest_version.arquivo_path,
                tamanho=latest_version.arquivo_tamanho,
                hash_verificacao=latest_version.arquivo_hash,
                forcada=forcada,
                notas=latest_version.notas_release
            )
        
        return VersionCheckResponse(
            atualizacao_disponivel=False,
            versao_latest=versao_atual,
            tipo_atualizacao=None,
            url_download=None,
            tamanho=None,
            hash_verificacao=None,
            forcada=False,
            notas=None
        )
    
    @staticmethod
    def listar_versoes(db: Session, cliente_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> List[UploadVersao]:
        """Lista versões disponíveis"""
        query = db.query(UploadVersao)
        
        if cliente_id:
            query = query.filter(UploadVersao.cliente_id == cliente_id)
        
        return query.order_by(UploadVersao.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def atualizar_status_upload(db: Session, upload_id: int, status: StatusUpload) -> bool:
        """Atualiza status de um upload"""
        upload = db.query(UploadVersao).filter(UploadVersao.id == upload_id).first()
        if not upload:
            return False
        
        upload.status = status
        
        # Se concluído, definir data de publicação
        if status == StatusUpload.CONCLUIDO and not upload.data_publicacao:
            upload.data_publicacao = datetime.utcnow()
        
        db.commit()
        
        # Registrar histórico
        historico = HistoricoUpload(
            upload_id=upload_id,
            acao=f"status_alterado_{status.value}",
            detalhes=f"Status alterado para {status.value}",
            usuario="sistema",
            ip_address="localhost"
        )
        db.add(historico)
        db.commit()
        
        logger.info(f"Status do upload {upload_id} alterado para {status.value}")
        return True
