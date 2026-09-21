from fastapi import APIRouter, Depends, Response, UploadFile

from app.core.dependencies import (
    get_configuracion_transpilacion_service,
    get_current_user,
    get_ia_import_service,
    get_transpilacion_service,
    get_xmi_export_service,
    get_xmi_import_service,
)
from app.core.exceptions import AppException
from app.modules.auth.model import Usuario
from app.modules.canvas.schema import GuardarLienzo
from app.modules.interoperability.schema import (
    ConfigurarTranspilacion,
    ConfiguracionTranspilacionRespuesta,
)
from app.modules.interoperability.service import (
    ConfiguracionTranspilacionService,
    IaImportService,
    TranspilacionService,
    XmiExportService,
    XmiImportService,
)

_MIME_TYPES_IMAGEN_VALIDOS = {"image/png", "image/jpeg", "image/webp"}

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


@router.post("/{proyecto_id}/importar/xmi", response_model=GuardarLienzo)
async def importar_xmi(
    proyecto_id: int,
    archivo: UploadFile,
    usuario: Usuario = Depends(get_current_user),
    service: XmiImportService = Depends(get_xmi_import_service),
):
    contenido = await archivo.read()
    return await service.importar(proyecto_id, usuario.id, contenido)


@router.post("/{proyecto_id}/importar/ia", response_model=GuardarLienzo)
async def importar_desde_imagen(
    proyecto_id: int,
    archivo: UploadFile,
    usuario: Usuario = Depends(get_current_user),
    service: IaImportService = Depends(get_ia_import_service),
):
    if archivo.content_type not in _MIME_TYPES_IMAGEN_VALIDOS:
        raise AppException("El archivo debe ser una imagen (PNG, JPEG o WEBP).")
    contenido = await archivo.read()
    return await service.importar(proyecto_id, usuario.id, contenido, archivo.content_type)


@router.get("/{proyecto_id}/transpilar")
async def transpilar_spring_boot(
    proyecto_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: TranspilacionService = Depends(get_transpilacion_service),
):
    contenido, nombre_archivo = await service.generar(proyecto_id, usuario.id)
    return Response(
        content=contenido,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
