# narcidicontrol

Sistema completo de controle SaaS para gerenciamento de licenças, assinaturas, máquinas e versões.

## Funcionalidades

### 🎯 Gestão de Clientes
- Cadastro e gestão de clientes
- Perfis e permissões
- Status (ativo, bloqueado, cancelado)
- Tipos (free, basic, pro, enterprise)

### 🔐 Sistema de Licenças
- Geração automática de chaves
- Tipos (demonstração, temporária, perpétua, assinatura)
- Ativação/validação remota
- Bloqueio e desbloqueio
- Renovação automática

### 💻 Controle de Máquinas
- Registro automático de máquinas
- Heartbeat para monitoramento
- Métricas em tempo real (CPU, memória, disco)
- Bloqueio remoto
- Dashboard de status

### 📦 Gestão de Versões
- Upload de novas versões
- Controle de compatibilidade
- Download automático
- Histórico de versões
- Verificação de atualizações

### 🚨 Sistema de Alertas
- Email automático
- Webhooks
- Alertas de segurança
- Notificações em tempo real

### 📊 Dashboards
- Estatísticas de uso
- Monitoramento em tempo real
- Previsão de churn (ML)
- Sugestões de upgrade
- Detecção de comportamento suspeito

### 🤖 Automações
- Monitoramento contínuo
- Renovação automática
- Backup de dados
- Relatórios automáticos

## Arquitetura

- **FastAPI**: Framework web assíncrono
- **PostgreSQL**: Banco de dados principal
- **Redis**: Cache e mensageria
- **SQLAlchemy**: ORM
- **Celery**: Tarefas em background
- **Docker**: Containerização
- **ML Engine**: Previsões e análises

## Instalação

### Requisitos
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (opcional)

### Configuração

1. Clone o repositório
```bash


cp .env.example .env
# Edite .env com suas configurações



pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload
docker-compose -f docker/docker-compose.yml up -d


API Endpoints
Clientes

    POST /api/v1/clientes/ - Criar cliente

    GET /api/v1/clientes/ - Listar clientes

    GET /api/v1/clientes/{id} - Obter cliente

    PUT /api/v1/clientes/{id} - Atualizar cliente

    POST /api/v1/clientes/{id}/bloquear - Bloquear cliente

    POST /api/v1/clientes/{id}/ativar - Ativar cliente

Máquinas

    POST /api/v1/maquinas/ - Registrar máquina

    POST /api/v1/maquinas/heartbeat - Enviar heartbeat

    GET /api/v1/maquinas/ - Listar máquinas

    POST /api/v1/maquinas/{id}/bloquear - Bloquear máquina

    POST /api/v1/maquinas/{id}/desbloquear - Desbloquear máquina

    GET /api/v1/maquinas/{id}/dashboard - Dashboard da máquina

Licenças

    POST /api/v1/licencas/ - Criar licença

    POST /api/v1/licencas/ativar/{chave} - Ativar licença

    GET /api/v1/licencas/verificar/{chave} - Verificar licença

    POST /api/v1/licencas/{id}/renovar - Renovar licença

    POST /api/v1/licencas/{id}/bloquear - Bloquear licença

Uploads

    POST /api/v1/uploads/versao - Upload de versão

    GET /api/v1/uploads/versao - Listar versões

    POST /api/v1/uploads/versao/check - Verificar atualização

    GET /api/v1/uploads/download/{id} - Download de versão

Monitoramento
Tarefas Automáticas

    Verificação de máquinas offline (5 min)

    Monitoramento de licenças expirando (1 hora)

    Renovação de assinaturas (6 horas)

    Relatórios diários (8:00)

    Backup de dados (2:00)

Alertas Automáticos

    Novo cliente registrado

    Licença expirada

    Máquina offline

    Atividade suspeita

    Pagamento pendente

Machine Learning
Previsão de Churn

    Análise de padrões de uso

    Identificação de fatores de risco

    Classificação de risco (baixo, médio, alto, crítico)

    Sugestões de retenção

Detecção de Comportamento Suspeito

    Múltiplas máquinas offline

    Uso anormal de recursos

    Tentativas de acesso suspeitas

    Alterações frequentes de configuração

Segurança
Autenticação

    JWT Tokens

    OAuth2 compatível

    Tokens de expiração configurável

Autorização

    Sistema de permissões granulares

    Controle por módulo e ação

    Perfis de acesso

Auditoria

    Log de todas as ações

    Histórico de alterações

    Rastreabilidade completa

Escalabilidade
Arquitetura

    Microsserviços prontos

    API-first design

    Banco de dados otimizado

    Cache Redis

Performance

    Consultas otimizadas

    Paginação em todos endpoints

    WebSockets para tempo real

    Background tasks para operações pesadas

Integração
Webhooks

    Eventos em tempo real

    Customização completa

    Retry automático

API Externa

    Documentação Swagger

    Compatível com OpenAPI

    SDKs disponíveis

Manutenção
Logs

    Logs estruturados em JSON

    Rotação automática

    Níveis configuráveis

Monitoramento

    Health checks

    Métricas de performance

    Alertas de erro

Backup

    Backup automático

    Restauração fácil

    Versionamento de dados

Suporte
Documentação

    API Documentation

    Guia de Integração
