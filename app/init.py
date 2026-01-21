
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import logging

from app.config import settings
from app.database.session import engine, Base
from app.utils.logger import setup_logging

# Setup logging
setup_logging()

# Import all models to ensure they are registered with SQLAlchemy
from app.models.cliente import Cliente, PerfilCliente, PermissaoCliente
from app.models.maquina import Maquina, MaquinaStatus, MaquinaMetrica
from app.models.licenca import Licenca, Assinatura, Bloqueio, Pagamento
from app.models.upload import UploadVersao, HistoricoUpload

# Import API routes
from app.api.cliente_api import router as cliente_router
from app.api.maquina_api import router as maquina_router
from app.api.licenca_api import router as licenca_router
from app.api.upload_api import router as upload_router

# Import events
from app.events import setup_events

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        debug=settings.DEBUG,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else ["https://nzilacode.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.DEBUG else ["nzilacode.com", "*.nzilacode.com"]
    )
    
    # Include routers
    app.include_router(cliente_router, prefix=settings.API_V1_PREFIX)
    app.include_router(maquina_router, prefix=settings.API_V1_PREFIX)
    app.include_router(licenca_router, prefix=settings.API_V1_PREFIX)
    app.include_router(upload_router, prefix=settings.API_V1_PREFIX)
    
    # Setup events
    setup_events(app)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize on startup"""
        Base.metadata.create_all(bind=engine)
        logging.info(f"{settings.APP_NAME} started in {settings.ENVIRONMENT} mode")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logging.info(f"{settings.APP_NAME} shutting down")
    
    @app.get("/")
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "status": "operational"
        }
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return app
