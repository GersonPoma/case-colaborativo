from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    get_colaborador_service,
    get_current_user,
    get_historial_versiones_service,
    get_mensaje_chat_service,
    get_proyecto_service,
)
from app.core.pagination import Pagina, ParametrosPaginacion, construir_pagina
from app.modules.auth.model import Usuario
from app.modules.workspace.schema import (
    CambiarRolColaborador,
    ColaboradorRespuesta,
    CrearProyecto,
    EnviarMensaje,
    HistorialVersionesResumen,
    InvitacionRespuesta,
    InvitarColaborador,
    MensajeChatRespuesta,
    ProyectoConRol,
    ProyectoRespuesta,
    ResponderInvitacion,
)
from app.modules.workspace.service import (
    ColaboradorService,
    HistorialVersionesService,
    MensajeChatService,
    ProyectoService,
)

router = APIRouter(prefix="/proyectos", tags=["workspace"])


# ===== PROYECTOS =====


@router.post("", response_model=ProyectoRespuesta, status_code=status.HTTP_201_CREATED)
async def crear_proyecto(
    datos: CrearProyecto,
    usuario: Usuario = Depends(get_current_user),
    service: ProyectoService = Depends(get_proyecto_service),
):
    return await service.crear(datos, usuario.id)


@router.get("/propios", response_model=Pagina[ProyectoRespuesta])
async def listar_proyectos_propios(
    params: ParametrosPaginacion = Depends(),
    usuario: Usuario = Depends(get_current_user),
    service: ProyectoService = Depends(get_proyecto_service),
):
    items, total = await service.listar_propios(usuario.id, params)
    return construir_pagina(items, total, params)


@router.get("/colaboraciones", response_model=Pagina[ProyectoConRol])
async def listar_proyectos_colaboraciones(
    params: ParametrosPaginacion = Depends(),
    usuario: Usuario = Depends(get_current_user),
    service: ColaboradorService = Depends(get_colaborador_service),
):
    items, total = await service.listar_colaboraciones(usuario.id, params)
    return construir_pagina(items, total, params)


@router.get("/invitaciones", response_model=Pagina[InvitacionRespuesta])
async def listar_invitaciones_pendientes(
    params: ParametrosPaginacion = Depends(),
    usuario: Usuario = Depends(get_current_user),
    service: ColaboradorService = Depends(get_colaborador_service),
):
    items, total = await service.listar_invitaciones_pendientes(usuario.id, params)
    return construir_pagina(items, total, params)


@router.get("/{proyecto_id}", response_model=ProyectoRespuesta)
async def obtener_proyecto(
    proyecto_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: ProyectoService = Depends(get_proyecto_service),
):
    proyecto = await service.obtener(proyecto_id)
    await service.verificar_miembro(proyecto, usuario.id)
    return proyecto


@router.delete("/{proyecto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_proyecto(
    proyecto_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: ProyectoService = Depends(get_proyecto_service),
):
    await service.eliminar(proyecto_id, usuario.id)


# ===== COLABORADORES =====


@router.get("/{proyecto_id}/colaboradores", response_model=Pagina[ColaboradorRespuesta])
async def listar_colaboradores(
    proyecto_id: int,
    params: ParametrosPaginacion = Depends(),
    usuario: Usuario = Depends(get_current_user),
    service: ColaboradorService = Depends(get_colaborador_service),
):
    items, total = await service.listar_colaboradores(proyecto_id, usuario.id, params)
    return construir_pagina(items, total, params)


@router.post(
    "/{proyecto_id}/colaboradores",
    response_model=ColaboradorRespuesta,
    status_code=status.HTTP_201_CREATED,
)
async def invitar_colaborador(
    proyecto_id: int,
    datos: InvitarColaborador,
    usuario: Usuario = Depends(get_current_user),
    service: ColaboradorService = Depends(get_colaborador_service),
):
    return await service.invitar(proyecto_id, usuario.id, datos)


@router.post("/{proyecto_id}/invitacion/responder", response_model=ColaboradorRespuesta)
async def responder_invitacion(
    proyecto_id: int,
    datos: ResponderInvitacion,
    usuario: Usuario = Depends(get_current_user),
    service: ColaboradorService = Depends(get_colaborador_service),
):
    return await service.responder_invitacion(proyecto_id, usuario.id, datos)


@router.patch("/{proyecto_id}/colaboradores/{id_usuario}", response_model=ColaboradorRespuesta)
async def cambiar_rol_colaborador(
    proyecto_id: int,
    id_usuario: int,
    datos: CambiarRolColaborador,
    usuario: Usuario = Depends(get_current_user),
    service: ColaboradorService = Depends(get_colaborador_service),
):
    return await service.cambiar_rol(proyecto_id, usuario.id, id_usuario, datos)


@router.delete("/{proyecto_id}/colaboradores/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
async def quitar_colaborador(
    proyecto_id: int,
    id_usuario: int,
    usuario: Usuario = Depends(get_current_user),
    service: ColaboradorService = Depends(get_colaborador_service),
):
    await service.quitar(proyecto_id, usuario.id, id_usuario)


# ===== HISTORIAL DE VERSIONES (solo dueño) =====


@router.get("/{proyecto_id}/historial", response_model=Pagina[HistorialVersionesResumen])
async def listar_historial_versiones(
    proyecto_id: int,
    params: ParametrosPaginacion = Depends(),
    usuario: Usuario = Depends(get_current_user),
    service: HistorialVersionesService = Depends(get_historial_versiones_service),
):
    items, total = await service.listar(proyecto_id, usuario.id, params)
    return construir_pagina(items, total, params)


@router.post(
    "/{proyecto_id}/historial",
    response_model=HistorialVersionesResumen,
    status_code=201,
)
async def crear_version_historial(
    proyecto_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: HistorialVersionesService = Depends(get_historial_versiones_service),
):
    return await service.crear_version(proyecto_id, usuario.id)


@router.get("/{proyecto_id}/historial/{historial_id}/lienzo")
async def obtener_lienzo_historial(
    proyecto_id: int,
    historial_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: HistorialVersionesService = Depends(get_historial_versiones_service),
):
    return await service.obtener_lienzo(proyecto_id, usuario.id, historial_id)


@router.post("/{proyecto_id}/historial/{historial_id}/restaurar", response_model=ProyectoRespuesta)
async def restaurar_version(
    proyecto_id: int,
    historial_id: int,
    usuario: Usuario = Depends(get_current_user),
    service: HistorialVersionesService = Depends(get_historial_versiones_service),
):
    return await service.restaurar(proyecto_id, usuario.id, historial_id)


# ===== CHAT DEL PROYECTO (CU-23) =====


@router.get("/{proyecto_id}/mensajes", response_model=Pagina[MensajeChatRespuesta])
async def listar_mensajes(
    proyecto_id: int,
    params: ParametrosPaginacion = Depends(),
    usuario: Usuario = Depends(get_current_user),
    service: MensajeChatService = Depends(get_mensaje_chat_service),
):
    items, total = await service.listar(proyecto_id, usuario.id, params)
    return construir_pagina(items, total, params)


@router.post(
    "/{proyecto_id}/mensajes",
    response_model=MensajeChatRespuesta,
    status_code=status.HTTP_201_CREATED,
)
async def enviar_mensaje(
    proyecto_id: int,
    datos: EnviarMensaje,
    usuario: Usuario = Depends(get_current_user),
    service: MensajeChatService = Depends(get_mensaje_chat_service),
):
    return await service.enviar(proyecto_id, usuario.id, datos)
