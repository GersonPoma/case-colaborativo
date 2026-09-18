import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.modules.interoperability.model import BaseDatosDestino, ConfiguracionTranspilacion
from app.modules.interoperability.repository import ConfiguracionTranspilacionRepository
from app.modules.interoperability.schema import (
    ConfigurarTranspilacion,
    ConfiguracionTranspilacionRespuesta,
)
from app.modules.interoperability.transpiler import generar_proyecto
from app.modules.interoperability.xmi_export import construir_xmi
from app.modules.interoperability.xmi_import import importar_xmi
from app.modules.workspace.service import ProyectoService

JAVA_VERSION_DEFECTO = "17"
SPRING_BOOT_VERSION_DEFECTO = "3.2.0"
BASE_DATOS_DEFECTO = BaseDatosDestino.POSTGRESQL


def _slug(texto: str) -> str:
    normalizado = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
    return normalizado or "proyecto"


class ConfiguracionTranspilacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ConfiguracionTranspilacionRepository(db)
        self.proyecto_service = ProyectoService(db)

    async def obtener(
        self, proyecto_id: int, id_usuario_solicitante: int
    ) -> ConfiguracionTranspilacionRespuesta:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_miembro(proyecto, id_usuario_solicitante)

        config = await self.repository.get_by_proyecto(proyecto_id)
        if config is not None:
            return self._a_respuesta(config, configurado=True)

        return ConfiguracionTranspilacionRespuesta(
            configurado=False,
            group_id="com.example",
            artifact_id=_slug(proyecto.nombre),
            java_version=JAVA_VERSION_DEFECTO,
            spring_boot_version=SPRING_BOOT_VERSION_DEFECTO,
            base_datos=BASE_DATOS_DEFECTO,
        )

    async def configurar(
        self, proyecto_id: int, id_usuario_solicitante: int, datos: ConfigurarTranspilacion
    ) -> ConfiguracionTranspilacionRespuesta:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_editor(proyecto, id_usuario_solicitante)

        config = await self.repository.get_by_proyecto(proyecto_id)
        if config is None:
            config = ConfiguracionTranspilacion(id_proyecto=proyecto_id)
            self.db.add(config)

        config.group_id = datos.group_id
        config.artifact_id = datos.artifact_id
        config.java_version = datos.java_version
        config.spring_boot_version = datos.spring_boot_version
        config.base_datos = datos.base_datos

        await self.db.commit()
        await self.db.refresh(config)

        return self._a_respuesta(config, configurado=True)

    def _a_respuesta(
        self, config: ConfiguracionTranspilacion, configurado: bool
    ) -> ConfiguracionTranspilacionRespuesta:
        return ConfiguracionTranspilacionRespuesta(
            configurado=configurado,
            group_id=config.group_id,
            artifact_id=config.artifact_id,
            java_version=config.java_version,
            spring_boot_version=config.spring_boot_version,
            base_datos=config.base_datos,
        )


class XmiExportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.proyecto_service = ProyectoService(db)

    async def exportar(self, proyecto_id: int, id_usuario_solicitante: int) -> tuple[bytes, str]:
        return await self._exportar(proyecto_id, id_usuario_solicitante, para_ea=False)

    async def exportar_para_ea(
        self, proyecto_id: int, id_usuario_solicitante: int
    ) -> tuple[bytes, str]:
        return await self._exportar(proyecto_id, id_usuario_solicitante, para_ea=True)

    async def _exportar(
        self, proyecto_id: int, id_usuario_solicitante: int, para_ea: bool
    ) -> tuple[bytes, str]:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_miembro(proyecto, id_usuario_solicitante)

        estado = proyecto.estado_lienzo or {"clases": {}, "relaciones": {}}
        contenido = construir_xmi(
            estado.get("clases", {}),
            estado.get("relaciones", {}),
            proyecto.nombre,
            proyecto_id,
            para_ea=para_ea,
        )
        sufijo = "_ea" if para_ea else ""
        nombre_archivo = f"{_slug(proyecto.nombre)}{sufijo}.xmi"
        return contenido, nombre_archivo


class XmiImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.proyecto_service = ProyectoService(db)

    async def importar(self, proyecto_id: int, id_usuario_solicitante: int, contenido: bytes) -> dict:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_editor(proyecto, id_usuario_solicitante)
        return importar_xmi(contenido)


class TranspilacionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.proyecto_service = ProyectoService(db)
        self.repository = ConfiguracionTranspilacionRepository(db)

    async def generar(self, proyecto_id: int, id_usuario_solicitante: int) -> tuple[bytes, str]:
        proyecto = await self.proyecto_service.obtener(proyecto_id)
        await self.proyecto_service.verificar_miembro(proyecto, id_usuario_solicitante)

        config = await self.repository.get_by_proyecto(proyecto_id)
        if config is None:
            raise ConflictError(
                "El proyecto no tiene una configuracion de transpilacion. Configurala antes de generar el proyecto Spring Boot."
            )

        estado = proyecto.estado_lienzo or {"clases": {}, "relaciones": {}}
        contenido = generar_proyecto(
            estado.get("clases", {}),
            estado.get("relaciones", {}),
            proyecto.nombre,
            {
                "group_id": config.group_id,
                "artifact_id": config.artifact_id,
                "java_version": config.java_version,
                "spring_boot_version": config.spring_boot_version,
                "base_datos": config.base_datos,
            },
        )
        nombre_archivo = f"{_slug(config.artifact_id)}.zip"
        return contenido, nombre_archivo
