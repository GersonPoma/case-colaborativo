from sqlalchemy import Boolean, Column, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship

from app.config.database import Base
from app.core.base_model import BaseAuditable


class Usuario(BaseAuditable, Base):
    __tablename__ = "usuarios"

    id = Column(Integer, Identity(), primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    perfil = relationship("Perfil", back_populates="usuario", uselist=False)


class Perfil(BaseAuditable, Base):
    __tablename__ = "perfiles"

    id = Column(Integer, Identity(), primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)

    usuario = relationship("Usuario", back_populates="perfil")
