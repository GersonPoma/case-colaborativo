from fastapi import APIRouter, Depends, Response

from app.core.dependencies import (
    get_configuracion_transpilacion_service,
    get_current_user,
    get_xmi_export_service,
)
from app.modules.auth.model import Usuario
from app.modules.interoperability.schema import (
    ConfigurarTranspilacion,
    ConfiguracionTranspilacionRespuesta,
)
from app.modules.interoperability.service import ConfiguracionTranspilacionService, XmiExportService

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


@router.get("/{proyecto_id}/exportar/xmi")
async def exportar_xmi(
    proyecto_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: XmiExportService = Depends(get_xmi_export_service),
):
    contenido, nombre_archivo = await service.exportar(proyecto_id, usuario.id)
    return Response(
        content=contenido,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/{proyecto_id}/exportar/xmi-ea")
async def exportar_xmi_para_ea(
    proyecto_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: XmiExportService = Depends(get_xmi_export_service),
):
    contenido, nombre_archivo = await service.exportar_para_ea(proyecto_id, usuario.id)
    return Response(
        content=contenido,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
