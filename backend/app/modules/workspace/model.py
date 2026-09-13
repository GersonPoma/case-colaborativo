import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Identity, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.config.database import Base
from app.core.base_model import BaseAuditable

JSONB_VARIANT = JSON().with_variant(JSONB(), "postgresql")


class RolColaborador(str, enum.Enum):
    LECTOR = "LECTOR"
    EDITOR = "EDITOR"


class Proyecto(BaseAuditable, Base):
    __tablename__ = "proyectos"

    id = Column(Integer, Identity(), primary_key=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    estado_lienzo = Column(JSONB_VARIANT, nullable=True)
    id_dueno = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    dueno = relationship("Usuario")
    colaboradores = relationship("Colaborador", back_populates="proyecto")
    historial_versiones = relationship("HistorialVersiones", back_populates="proyecto")
    mensajes_chat = relationship("MensajeChat", back_populates="proyecto")


class Colaborador(Base):
    __tablename__ = "colaboradores"

    id_proyecto = Column(Integer, ForeignKey("proyectos.id"), primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    rol = Column(Enum(RolColaborador, name="rol_colaborador"), nullable=False)
    unido_en = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    proyecto = relationship("Proyecto", back_populates="colaboradores")
    usuario = relationship("Usuario")


class HistorialVersiones(Base):
    __tablename__ = "historial_versiones"

    id = Column(Integer, Identity(), primary_key=True)
    id_proyecto = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    snapshot_lienzo = Column(JSONB_VARIANT, nullable=False)
    creado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    proyecto = relationship("Proyecto", back_populates="historial_versiones")
    usuario_creador = relationship("Usuario")


class MensajeChat(Base):
    __tablename__ = "mensajes_chat"

    id = Column(Integer, Identity(), primary_key=True)
    id_proyecto = Column(Integer, ForeignKey("proyectos.id"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    contenido = Column(Text, nullable=False)
    fecha_envio = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    proyecto = relationship("Proyecto", back_populates="mensajes_chat")
    usuario = relationship("Usuario")
