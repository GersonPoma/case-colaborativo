from fastapi import APIRouter, Depends

from app.core.dependencies import get_canvas_service, get_current_user, get_proyecto_service
from app.modules.auth.model import Usuario
from app.modules.canvas.schema import EstadoLienzo, GuardarLienzo
from app.modules.canvas.service import CanvasService
from app.modules.workspace.service import ProyectoService

router = APIRouter(prefix="/proyectos", tags=["canvas"])


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
