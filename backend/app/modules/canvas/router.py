from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel

from app.core.dependencies import (
    get_canvas_ia_service,
    get_canvas_service,
    get_current_user,
    get_proyecto_service,
)
from app.modules.auth.model import Usuario
from app.modules.canvas.schema import EstadoLienzo, GuardarLienzo
from app.modules.canvas.service import CanvasIaService, CanvasService
from app.modules.workspace.service import ProyectoService

router = APIRouter(prefix="/proyectos", tags=["canvas"])


class RefactorizarPorTexto(BaseModel):
    texto: str


@router.get("/{proyecto_id}/lienzo", response_model=EstadoLienzo)
async def obtener_lienzo(
    proyecto_id: int,
    usuario: Usuario = Depends(get_current_user),
    proyecto_service: ProyectoService = Depends(get_proyecto_service),
    canvas_service: CanvasService = Depends(get_canvas_service),
):
    proyecto = await proyecto_service.obtener(proyecto_id)
    await proyecto_service.verificar_miembro(proyecto, usuario.id)
    return await canvas_service.obtener_lienzo(proyecto_id)


@router.put("/{proyecto_id}/lienzo", response_model=EstadoLienzo)
async def guardar_lienzo(
    proyecto_id: int,
    datos: GuardarLienzo,
    usuario: Usuario = Depends(get_current_user),
    proyecto_service: ProyectoService = Depends(get_proyecto_service),
    canvas_service: CanvasService = Depends(get_canvas_service),
):
    proyecto = await proyecto_service.obtener(proyecto_id)
    await proyecto_service.verificar_editor(proyecto, usuario.id)
    return await canvas_service.guardar_lienzo(proyecto_id, datos)


@router.post("/{proyecto_id}/ia/texto")
async def refactorizar_por_texto(
    proyecto_id: int,
    datos: RefactorizarPorTexto,
    usuario: Usuario = Depends(get_current_user),
    canvas_ia_service: CanvasIaService = Depends(get_canvas_ia_service),
):
    return await canvas_ia_service.refactorizar_por_texto(proyecto_id, usuario.id, datos.texto)


@router.post("/{proyecto_id}/ia/voz")
async def refactorizar_por_voz(
    proyecto_id: int,
    archivo: UploadFile,
    usuario: Usuario = Depends(get_current_user),
    canvas_ia_service: CanvasIaService = Depends(get_canvas_ia_service),
):
    contenido = await archivo.read()
    return await canvas_ia_service.refactorizar_por_voz(
        proyecto_id, usuario.id, contenido, archivo.filename or "audio.wav"
    )
