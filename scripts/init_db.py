#!/usr/bin/env python3
"""Script para inicializar banco de dados"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import engine, Base
from app.models.cliente import Cliente, PerfilCliente, PermissaoCliente
from app.models.maquina import Maquina, MaquinaMetrica
from app.models.licenca import Licenca, Assinatura, Bloqueio, Pagamento
from app.models.upload import UploadVersao, HistoricoUpload

def init_db():
    """Cria todas as tabelas"""
    print("Criando tabelas...")
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")

if __name__ == "__main__":
    init_db()
