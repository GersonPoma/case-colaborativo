from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PerfilBase(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr


class PerfilRespuesta(PerfilBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_usuario: int
    created_at: datetime
    updated_at: datetime | None = None


class RegistrarUsuario(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    nombre: str
    apellido: str
    email: EmailStr


class IniciarSesion(BaseModel):
    username: str
    password: str


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    activo: bool
    created_at: datetime
    perfil: PerfilRespuesta | None = None


class TokenRespuesta(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RecuperarContrasena(BaseModel):
    email: EmailStr


class RestablecerContrasena(BaseModel):
    token: str
    password: str = Field(min_length=8)
