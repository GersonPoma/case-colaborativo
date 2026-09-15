from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.email import send_email
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
    verify_password_reset_fingerprint,
)
from app.modules.auth.model import Perfil, Usuario
from app.modules.auth.repository import PerfilRepository, UsuarioRepository
from app.modules.auth.schema import IniciarSesion, RegistrarUsuario, TokenRespuesta


class PerfilService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perfil_repository = PerfilRepository(db)

    async def obtener_por_email(self, email: str) -> Perfil | None:
        return await self.perfil_repository.get_by_email(email)

    async def crear(self, id_usuario: int, nombre: str, apellido: str, email: str) -> Perfil:
        perfil = Perfil(id_usuario=id_usuario, nombre=nombre, apellido=apellido, email=email)
        return await self.perfil_repository.create(perfil)


class UsuarioService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.usuario_repository = UsuarioRepository(db)
        self.perfil_service = PerfilService(db)

    async def registrar(self, datos: RegistrarUsuario) -> Usuario:
        if await self.usuario_repository.get_by_username(datos.username):
            raise ConflictError("El nombre de usuario ya existe")

        if await self.perfil_service.obtener_por_email(datos.email):
            raise ConflictError("El email ya está registrado")

        usuario = Usuario(
            username=datos.username,
            password=hash_password(datos.password),
            activo=True,
        )
        await self.usuario_repository.create(usuario)
        await self.db.flush()

        perfil = await self.perfil_service.crear(
            id_usuario=usuario.id,
            nombre=datos.nombre,
            apellido=datos.apellido,
            email=datos.email,
        )

        await self.db.commit()
        await self.db.refresh(usuario)
        usuario.perfil = perfil
        return usuario

    async def iniciar_sesion(self, datos: IniciarSesion) -> TokenRespuesta:
        usuario = await self.usuario_repository.get_by_username(datos.username)
        if not usuario or not verify_password(datos.password, usuario.password):
            raise UnauthorizedError("Credenciales inválidas")
        if not usuario.activo:
            raise ForbiddenError("Usuario inactivo")

        token = create_access_token(subject=str(usuario.id))
        return TokenRespuesta(access_token=token)

    async def recuperar_contrasena(self, email: str) -> None:
        perfil = await self.perfil_service.obtener_por_email(email)
        if perfil is None:
            # No se revela si el email existe o no, para evitar enumeración de usuarios
            return

        usuario = await self.usuario_repository.get_by_id(perfil.id_usuario)
        token = create_password_reset_token(
            subject=str(perfil.id_usuario), password_hash=usuario.password
        )
        enlace = f"{settings.FRONTEND_URL}/recuperar-contrasena?token={token}"

        await send_email(
            to=email,
            subject="Recupera tu contraseña",
            html_body=(
                f"<p>Hola {perfil.nombre},</p>"
                f"<p>Haz clic en el siguiente enlace para restablecer tu contraseña "
                f"(válido por 30 minutos):</p>"
                f'<p><a href="{enlace}">{enlace}</a></p>'
            ),
        )

    async def restablecer_contrasena(self, token: str, nueva_password: str) -> None:
        payload = decode_password_reset_token(token)
        if payload is None:
            raise UnauthorizedError("El enlace de recuperación es inválido o expiró")

        usuario = await self.usuario_repository.get_by_id(int(payload["sub"]))
        if usuario is None or not verify_password_reset_fingerprint(
            payload["pwf"], usuario.password
        ):
            raise UnauthorizedError("El enlace de recuperación es inválido o expiró")

        usuario.password = hash_password(nueva_password)
        await self.db.commit()
