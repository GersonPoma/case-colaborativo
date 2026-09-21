import enum

from sqlalchemy import Column, Enum, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship

from app.config.database import Base
from app.core.base_model import BaseAuditable


class BaseDatosDestino(str, enum.Enum):
    POSTGRESQL = "POSTGRESQL"


class ConfiguracionTranspilacion(BaseAuditable, Base):
    __tablename__ = "configuraciones_transpilacion"

    id = Column(Integer, Identity(), primary_key=True)
    id_proyecto = Column(Integer, ForeignKey("proyectos.id"), nullable=False, unique=True)
    group_id = Column(String(150), nullable=False)
    artifact_id = Column(String(100), nullable=False)
    java_version = Column(String(10), nullable=False)
    spring_boot_version = Column(String(20), nullable=False)
    base_datos = Column(Enum(BaseDatosDestino, name="base_datos_destino"), nullable=False)

    proyecto = relationship("Proyecto", back_populates="configuracion_transpilacion")
