from fastapi import APIRouter, Depends

from app.core.dependencies import get_configuracion_transpilacion_service, get_current_user
from app.modules.auth.model import Usuario
from app.modules.interoperability.schema import (
    ConfigurarTranspilacion,
    ConfiguracionTranspilacionRespuesta,
)
from app.modules.interoperability.service import ConfiguracionTranspilacionService

router = APIRouter(prefix="/proyectos", tags=["interoperabilidad"])


@router.get("/{proyecto_id}/transpilacion", response_model=ConfiguracionTranspilacionRespuesta)
async def obtener_configuracion_transpilacion(
    proyecto_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: ConfiguracionTranspilacionService = Depends(get_configuracion_transpilacion_service),
):
    return await service.obtener(proyecto_id, usuario.id)


@router.put("/{proyecto_id}/transpilacion", response_model=ConfiguracionTranspilacionRespuesta)
async def configurar_transpilacion(
    proyecto_id: int,
    datos: ConfigurarTranspilacion,
    usuario: Usuario = Depends(get_current_user),
    service: ConfiguracionTranspilacionService = Depends(get_configuracion_transpilacion_service),
):
    return await service.configurar(proyecto_id, usuario.id, datos)
