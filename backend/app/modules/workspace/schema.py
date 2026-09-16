from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.workspace.model import EstadoColaborador, RolColaborador


class UsuarioResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class CrearProyecto(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None


class ProyectoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None = None
    id_dueno: int
    created_at: datetime
    updated_at: datetime | None = None


class ProyectoConRol(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    proyecto: ProyectoRespuesta
    rol: RolColaborador


class InvitarColaborador(BaseModel):
    username: str
    rol: RolColaborador


class CambiarRolColaborador(BaseModel):
    rol: RolColaborador


class ResponderInvitacion(BaseModel):
    aceptar: bool


class ColaboradorRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario: UsuarioResumen
    rol: RolColaborador
    estado: EstadoColaborador
    unido_en: datetime


class InvitacionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_proyecto: int
    proyecto: ProyectoRespuesta
    rol: RolColaborador
    unido_en: datetime


class HistorialVersionesResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    creado_por: int
    fecha: datetime


class EnviarMensaje(BaseModel):
    contenido: str = Field(min_length=1)


class MensajeChatRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario: UsuarioResumen
    contenido: str
    fecha_envio: datetime
