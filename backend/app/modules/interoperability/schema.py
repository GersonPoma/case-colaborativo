from pydantic import BaseModel, Field

from app.modules.interoperability.model import BaseDatosDestino


class ConfigurarTranspilacion(BaseModel):
    group_id: str = Field(min_length=1, max_length=150)
    artifact_id: str = Field(min_length=1, max_length=100)
    java_version: str = Field(min_length=1, max_length=10)
    spring_boot_version: str = Field(min_length=1, max_length=20)
    base_datos: BaseDatosDestino


class ConfiguracionTranspilacionRespuesta(BaseModel):
    configurado: bool
    group_id: str
    artifact_id: str
    java_version: str
    spring_boot_version: str
    base_datos: BaseDatosDestino
