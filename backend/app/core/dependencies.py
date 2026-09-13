from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.modules.auth.model import Usuario
from app.modules.auth.repository import UsuarioRepository
from app.modules.auth.service import PerfilService, UsuarioService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_usuario_service(db: AsyncSession = Depends(get_db)) -> UsuarioService:
    return UsuarioService(db)


async def get_perfil_service(db: AsyncSession = Depends(get_db)) -> PerfilService:
    return PerfilService(db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    user_id = decode_access_token(token)
    if user_id is None:
        raise UnauthorizedError("Token inválido o expirado")

    usuario = await UsuarioRepository(db).get_by_id(int(user_id))
    if usuario is None:
        raise UnauthorizedError("Usuario no encontrado")

    return usuario
