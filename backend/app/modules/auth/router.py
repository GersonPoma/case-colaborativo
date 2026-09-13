from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_user, get_usuario_service
from app.modules.auth.model import Usuario
from app.modules.auth.schema import (
    IniciarSesion,
    RecuperarContrasena,
    RegistrarUsuario,
    RestablecerContrasena,
    TokenRespuesta,
    UsuarioRespuesta,
)
from app.modules.auth.service import UsuarioService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
async def registrar(
    datos: RegistrarUsuario, service: UsuarioService = Depends(get_usuario_service)
):
    return await service.registrar(datos)


@router.post("/login", response_model=TokenRespuesta)
async def iniciar_sesion(
    datos: IniciarSesion, service: UsuarioService = Depends(get_usuario_service)
):
    return await service.iniciar_sesion(datos)


@router.get("/me", response_model=UsuarioRespuesta)
async def obtener_usuario_actual(usuario: Usuario = Depends(get_current_user)):
    return usuario


@router.post("/recover-password", status_code=status.HTTP_204_NO_CONTENT)
async def recuperar_contrasena(
    datos: RecuperarContrasena, service: UsuarioService = Depends(get_usuario_service)
):
    await service.recuperar_contrasena(datos.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def restablecer_contrasena(
    datos: RestablecerContrasena, service: UsuarioService = Depends(get_usuario_service)
):
    await service.restablecer_contrasena(datos.token, datos.password)
