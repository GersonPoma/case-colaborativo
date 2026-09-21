from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.modules.auth.model import Usuario
from app.modules.auth.repository import UsuarioRepository
from app.modules.auth.service import PerfilService, UsuarioService
from app.modules.canvas.service import CanvasIaService, CanvasService
from app.modules.interoperability.service import (
    ConfiguracionTranspilacionService,
    IaImportService,
    TranspilacionService,
    XmiExportService,
    XmiImportService,
)
from app.modules.workspace.service import (
    ColaboradorService,
    HistorialVersionesService,
    MensajeChatService,
    ProyectoService,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_usuario_service(db: AsyncSession = Depends(get_db)) -> UsuarioService:
    return UsuarioService(db)


async def get_perfil_service(db: AsyncSession = Depends(get_db)) -> PerfilService:
    return PerfilService(db)


async def get_proyecto_service(db: AsyncSession = Depends(get_db)) -> ProyectoService:
    return ProyectoService(db)


async def get_colaborador_service(db: AsyncSession = Depends(get_db)) -> ColaboradorService:
    return ColaboradorService(db)


async def get_historial_versiones_service(
    db: AsyncSession = Depends(get_db),
) -> HistorialVersionesService:
    return HistorialVersionesService(db)


async def get_mensaje_chat_service(db: AsyncSession = Depends(get_db)) -> MensajeChatService:
    return MensajeChatService(db)


async def get_canvas_service(db: AsyncSession = Depends(get_db)) -> CanvasService:
    return CanvasService(db)


async def get_canvas_ia_service(db: AsyncSession = Depends(get_db)) -> CanvasIaService:
    return CanvasIaService(db)


async def get_configuracion_transpilacion_service(
    db: AsyncSession = Depends(get_db),
) -> ConfiguracionTranspilacionService:
    return ConfiguracionTranspilacionService(db)


async def get_xmi_export_service(db: AsyncSession = Depends(get_db)) -> XmiExportService:
    return XmiExportService(db)


async def get_xmi_import_service(db: AsyncSession = Depends(get_db)) -> XmiImportService:
    return XmiImportService(db)


async def get_transpilacion_service(db: AsyncSession = Depends(get_db)) -> TranspilacionService:
    return TranspilacionService(db)


async def get_ia_import_service(db: AsyncSession = Depends(get_db)) -> IaImportService:
    return IaImportService(db)


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
