from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
import secrets
import string
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria token JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtém usuário atual do token"""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """Verifica se usuário está ativo"""
    if current_user.get("is_active") is False:
        raise HTTPException(status_code=400, detail="Usuário inativo")
    return current_user

def require_permission(modulo: str, acao: str):
    """Decorator para verificar permissões"""
    def permission_decorator(func):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            
            if not current_user:
                # Tentar obter current_user dos args
                for arg in args:
                    if isinstance(arg, dict) and "sub" in arg:
                        current_user = arg
                        break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Autenticação necessária"
                )
            
            # Verificar se é admin (tem todas as permissões)
            if current_user.get("is_admin"):
                return await func(*args, **kwargs)
            
            # Verificar permissões específicas
            permissoes = current_user.get("permissoes", [])
            if any(p["modulo"] == modulo and p["acao"] == acao and p["permitido"] for p in permissoes):
                return await func(*args, **kwargs)
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão necessária: {modulo}.{acao}"
            )
        
        return wrapper
    
    return permission_decorator

def generate_license_key(length: int = 25) -> str:
    """Gera chave de licença"""
    alphabet = string.ascii_uppercase + string.digits
    key = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # Formatar como grupos
    formatted_key = '-'.join([key[i:i+5] for i in range(0, len(key), 5)])
    return formatted_key

def generate_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """Gera hash de arquivo"""
    import hashlib
    
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()
