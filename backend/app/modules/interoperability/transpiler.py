import re
import unicodedata
import zipfile
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_DIR_PLANTILLAS = Path(__file__).resolve().parent.parent.parent / "templates" / "spring_boot"

_env = Environment(
    loader=FileSystemLoader(str(_DIR_PLANTILLAS)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)

_MODIFICADOR_JAVA = {
    "PUBLICO": "public ",
    "PRIVADO": "private ",
    "PROTEGIDO": "protected ",
    "PAQUETE": "",  # sin modificador = paquete-privado en Java
}

_TIPOS_JAVA = {
    "int": "Integer",
    "integer": "Integer",
    "long": "Long",
    "short": "Short",
    "double": "Double",
    "float": "Float",
    "boolean": "Boolean",
    "bool": "Boolean",
    "string": "String",
    "char": "Character",
    "character": "Character",
    "byte": "Byte",
    "date": "LocalDate",
    "localdate": "LocalDate",
    "datetime": "LocalDateTime",
    "localdatetime": "LocalDateTime",
    "decimal": "BigDecimal",
    "bigdecimal": "BigDecimal",
    "void": "void",
    "text": "String",
    "texto": "String",
}

# tipos que ademas de mapear a String, necesitan @Lob en la entidad (JPA
# los guarda en una columna TEXT/CLOB en vez del VARCHAR(255) por defecto)
_TIPOS_TEXTO_LARGO = {"text", "texto"}


def _es_texto_largo(tipo_uml: str | None) -> bool:
    return bool(tipo_uml) and tipo_uml.strip().lower() in _TIPOS_TEXTO_LARGO

# tipos que necesitan un import extra ademas de jakarta/lombok/java.util.List
_IMPORTS_POR_TIPO_JAVA = {
    "LocalDate": "java.time.LocalDate",
    "LocalDateTime": "java.time.LocalDateTime",
    "BigDecimal": "java.math.BigDecimal",
}

_BD_INFO = {
    "POSTGRESQL": {
        "dependencia": {"group_id": "org.postgresql", "artifact_id": "postgresql", "scope": "runtime"},
        "driver": "org.postgresql.Driver",
        "dialecto": "org.hibernate.dialect.PostgreSQLDialect",
        "url": "jdbc:postgresql://localhost:5432/{db}",
        "usuario": "postgres",
        "clave": "postgres",
    },
}


def _limpiar_identificador(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^0-9a-zA-Z]+", " ", sin_acentos).strip()


def _pascal(texto: str) -> str:
    partes = _limpiar_identificador(texto).split()
    nombre = "".join(p[:1].upper() + p[1:] for p in partes) or "Clase"
    if nombre[0].isdigit():
        nombre = "C" + nombre
    return nombre


def _camel(texto: str) -> str:
    p = _pascal(texto)
    return p[:1].lower() + p[1:]


def _snake(texto: str) -> str:
    p = _pascal(texto)
    return re.sub(r"(?<!^)(?=[A-Z])", "_", p).lower()


def _segmento_paquete(texto: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9]", "", texto).lower()
    if not limpio:
        limpio = "app"
    if limpio[0].isdigit():
        limpio = "p" + limpio
    return limpio


def _tipo_java(tipo_uml: str | None) -> str:
    if not tipo_uml:
        return "String"
    texto = tipo_uml.strip()
    tipo_conocido = _TIPOS_JAVA.get(texto.lower())
    if tipo_conocido:
        return tipo_conocido
    # un tipo no reconocido (no es un primitivo/wrapper que ya mapeamos):
    # si empieza en mayuscula probablemente sea el nombre de una clase (del
    # diagrama o no), asi que se usa Object en vez de inventar un nombre de
    # tipo que no existe y no compila; si no, se asume texto libre
    return "Object" if texto and texto[0].isupper() else "String"


def _es_muchos(cardinalidad: str | None) -> bool:
    if not cardinalidad:
        return False
    valor = cardinalidad.strip()
    superior = valor.split("..", 1)[1].strip() if ".." in valor else valor
    if superior in ("", "*"):
        return True
    try:
        return int(superior) > 1
    except ValueError:
        return False


def _requerido(cardinalidad: str | None) -> bool:
    """True si el minimo de la cardinalidad es >= 1 (no permite 0)."""
    if not cardinalidad:
        return False
    valor = cardinalidad.strip()
    inferior = valor.split("..", 1)[0].strip() if ".." in valor else valor
    if inferior in ("0", "*", ""):
        return False
    try:
        return int(inferior) >= 1
    except ValueError:
        return True


class _ContextoClase:
    """Acumula, para una clase del diagrama, todo lo que hace falta para
    renderizar sus plantillas: atributos propios, campos de relacion (para la
    entidad), campos FK (para los DTOs) y dependencias de repositorios (para
    el service)."""

    def __init__(self, clase_id: str, clase: dict):
        self.clase_id = clase_id
        self.nombre_clase = _pascal(clase["nombre"])
        self.tabla = _snake(clase["nombre"])
        self.extiende: str | None = None
        self.tiene_subclases = False
        self.pk_atributo_id: str | None = None
        self.pk_tipo_java = "Long"
        self.pk_generado = True
        self.pk_modificador = "private "
        self.nombres_usados: set[str] = set()
        self.relaciones_entidad: list[dict] = []
        self.campos_dto: list[dict] = []  # {nombre, tipo_java, validacion, es_pk}
        self.dependencias_servicio: dict[str, dict] = {}  # tipo_repo -> {tipo, nombre}
        self.asignaciones: list[str] = []
        self.argumentos_respuesta: list[str] = []
        self.imports_entity: set[str] = set()
        self.imports_dto: set[str] = set()
        self.imports_validacion: set[str] = set()
        self.imports_service: set[str] = set()
        self.metodos_interfaz: list[dict] = []  # metodos PUBLICO: van en la interfaz + @Override en la impl
        self.metodos_extra: list[dict] = []  # metodos no publicos: solo en la impl, sin interfaz
        self.nombres_metodos_usados: set[str] = {"listar", "obtener", "crear", "actualizar", "eliminar"}
        self.imports_metodos: set[str] = set()  # de metodos PUBLICO: van en la interfaz y en la impl
        self.imports_metodos_impl: set[str] = set()  # de metodos no publicos: solo en la impl
        # clase asociada (AssociationClass) sin id propio: se identifica con
        # la combinacion de las dos clases que relaciona en vez de un id
        # sintetico, usando una clave compuesta @Embeddable
        self.usa_id_compuesto = False
        self.id_compuesto_clase: str | None = None
        self.id_compuesto_campos: list[dict] = []  # [{nombre_id, nombre_relacion, tipo_java}, ...]


def _construir_contextos(clases: dict, relaciones: dict) -> dict[str, _ContextoClase]:
    contextos = {cid: _ContextoClase(cid, clase) for cid, clase in clases.items()}
    nombre_a_clase_id = {ctx.nombre_clase: ctx.clase_id for ctx in contextos.values()}

    for ctx in contextos.values():
        clase = clases[ctx.clase_id]
        atributos = sorted(clase.get("atributos", {}).values(), key=lambda a: a.get("orden", 0))
        # se prioriza el atributo marcado como PK que se llame "id"; si ninguno
        # esta marcado asi, cualquier atributo llamado "id" igual se trata como
        # la llave primaria (nadie llama "id" a algo que no lo sea, y evita
        # duplicar el campo con uno sintetico + renombrar el propio a "id2")
        pk = next((a for a in atributos if a.get("es_pk") and _camel(a["nombre"]) == "id"), None)
        if not pk:
            pk = next((a for a in atributos if _camel(a["nombre"]) == "id"), None)
        # las plantillas (service/controller/repository) asumen que el campo
        # de la llave primaria se llama "id"
        if pk:
            ctx.pk_atributo_id = pk["id"]
            ctx.pk_tipo_java = _tipo_java(pk.get("tipo"))
            ctx.pk_generado = ctx.pk_tipo_java in ("Long", "Integer", "Short")
            ctx.pk_modificador = _MODIFICADOR_JAVA.get(pk.get("visibilidad"), "private ")

    for rel_id, rel in relaciones.items():
        tipo = rel.get("tipo")
        origen_id = rel.get("origen_id")
        destino_id = rel.get("destino_id")
        if origen_id not in contextos or destino_id not in contextos:
            continue

        if tipo == "HERENCIA":
            contextos[origen_id].extiende = contextos[destino_id].nombre_clase
            contextos[destino_id].tiene_subclases = True
            continue
        if tipo in ("REALIZACION", "TEMPLATE_BINDING"):
            continue
        clase_asociada_id = rel.get("clase_asociada_id")
        if clase_asociada_id:
            if clase_asociada_id in contextos:
                _agregar_clase_asociada(
                    contextos[clase_asociada_id], contextos[origen_id], contextos[destino_id]
                )
            continue

        card_origen = rel.get("cardinalidad_origen")
        card_destino = rel.get("cardinalidad_destino")
        origen_muchos = _es_muchos(card_origen)
        destino_muchos = _es_muchos(card_destino)
        es_composicion = tipo == "COMPOSICION"

        if origen_muchos and destino_muchos:
            _agregar_muchos_a_muchos(rel_id, contextos[origen_id], contextos[destino_id])
        elif destino_muchos:
            _agregar_uno_a_muchos(
                contextos[destino_id], contextos[origen_id], es_composicion, card_origen
            )
        elif origen_muchos:
            _agregar_uno_a_muchos(
                contextos[origen_id], contextos[destino_id], es_composicion, card_destino
            )
        else:
            if _requerido(card_destino):
                dueno, inverso = contextos[origen_id], contextos[destino_id]
            elif _requerido(card_origen):
                dueno, inverso = contextos[destino_id], contextos[origen_id]
            else:
                dueno, inverso = contextos[origen_id], contextos[destino_id]
            card_lado_apuntado = card_destino if dueno is contextos[origen_id] else card_origen
            _agregar_uno_a_uno(dueno, inverso, es_composicion, card_lado_apuntado)

    for ctx in contextos.values():
        clase = clases[ctx.clase_id]
        atributos = sorted(clase.get("atributos", {}).values(), key=lambda a: a.get("orden", 0))
        if ctx.usa_id_compuesto:
            for campo_id in ctx.id_compuesto_campos:
                ctx.campos_dto.append(
                    {
                        "nombre": campo_id["nombre_id"],
                        "tipo_java": campo_id["tipo_java"],
                        "validacion": "NotNull",
                        "modificador": None,
                    }
                )
                ctx.imports_validacion.add("jakarta.validation.constraints.NotNull")
                nombre_pascal = _pascal(campo_id["nombre_relacion"])
                ctx.argumentos_respuesta.append(
                    f"entidad.get{nombre_pascal}() != null ? entidad.get{nombre_pascal}().getId() : null"
                )
                ctx.nombres_usados.add(campo_id["nombre_id"])
        else:
            ctx.campos_dto.append(
                {
                    "nombre": "id",
                    "tipo_java": ctx.pk_tipo_java,
                    "validacion": None,
                    "modificador": ctx.pk_modificador,
                }
            )
            ctx.argumentos_respuesta.append("entidad.getId()")
        # "id" ya esta tomado por el campo @Id de arriba: si otro atributo
        # (sin marcar como PK) tambien se llama "id", debe renombrarse en vez
        # de colisionar (sino el record de respuesta queda con dos campos
        # "id" y ni compila)
        ctx.nombres_usados.add("id")
        for attr in atributos:
            if attr["id"] == ctx.pk_atributo_id:
                continue  # ya se represento como el campo "id" de arriba
            nombre_campo = _campo_unico(_camel(attr["nombre"]), ctx.nombres_usados)
            tipo_java = _tipo_java(attr.get("tipo"))
            _registrar_import_tipo(ctx.imports_entity, tipo_java)
            _registrar_import_tipo(ctx.imports_dto, tipo_java)
            validacion = "NotBlank" if tipo_java == "String" else "NotNull"
            ctx.imports_validacion.add(f"jakarta.validation.constraints.{validacion}")
            modificador = _MODIFICADOR_JAVA.get(attr.get("visibilidad"), "private ")
            ctx.campos_dto.append(
                {
                    "nombre": nombre_campo,
                    "tipo_java": tipo_java,
                    "validacion": validacion,
                    "modificador": modificador,
                    "lob": _es_texto_largo(attr.get("tipo")),
                }
            )
            ctx.argumentos_respuesta.append(f"entidad.get{_pascal(nombre_campo)}()")
            ctx.asignaciones.append(
                f"entidad.set{_pascal(nombre_campo)}(datos.{nombre_campo}());"
            )
        _procesar_metodos(ctx, clase, nombre_a_clase_id)

    return contextos


def _procesar_metodos(ctx: "_ContextoClase", clase: dict, nombre_a_clase_id: dict[str, str]) -> None:
    """Los metodos del diagrama no tienen logica de negocio (son solo firma),
    asi que se generan como stub: los PUBLICO van en la interfaz del service
    (con @Override en la implementacion), el resto se agregan directo en la
    implementacion con su propio modificador. El cuerpo de todos queda con un
    TODO y un valor de retorno vacio (null, o nada si es void).

    Si un tipo de parametro/retorno coincide con otra clase del diagrama: en
    metodos PUBLICO (que son parte del contrato del service, hacia afuera) se
    usa el DTO Response de esa clase, igual que el resto del CRUD nunca
    expone la entidad JPA; en metodos no publicos (que nunca salen de la
    implementacion, son detalle interno) se usa la entidad real."""
    metodos = sorted(clase.get("metodos", {}).values(), key=lambda m: m.get("orden", 0))
    for metodo in metodos:
        es_publico = metodo.get("visibilidad") == "PUBLICO"
        nombre_java = _campo_unico(_camel(metodo["nombre"]), ctx.nombres_metodos_usados)
        tipo_retorno = (
            _resolver_tipo_metodo(ctx, metodo.get("tipo_retorno"), es_publico, nombre_a_clase_id) or "void"
        )

        nombres_parametros_usados: set[str] = set()
        parametros_java = []
        for parametro in metodo.get("parametros", []):
            nombre_parametro = _campo_unico(_camel(parametro["nombre"]), nombres_parametros_usados)
            tipo_parametro = (
                _resolver_tipo_metodo(ctx, parametro.get("tipo"), es_publico, nombre_a_clase_id) or "String"
            )
            parametros_java.append(f"{tipo_parametro} {nombre_parametro}")

        info = {
            "tipo_retorno": tipo_retorno,
            "firma": f"{nombre_java}({', '.join(parametros_java)})",
            "cuerpo_return": None if tipo_retorno == "void" else "return null;",
            "modificador": _MODIFICADOR_JAVA.get(metodo.get("visibilidad"), "private "),
        }
        if es_publico:
            ctx.metodos_interfaz.append(info)
        else:
            ctx.metodos_extra.append(info)


def _resolver_tipo_metodo(
    ctx: "_ContextoClase", tipo_uml: str | None, es_publico: bool, nombre_a_clase_id: dict[str, str]
) -> str | None:
    """None si no hay tipo (el llamador aplica su propio default: void para
    retorno, String para parametro)."""
    if not tipo_uml:
        return None
    nombre_clase_ref = _pascal(tipo_uml)
    clase_id_ref = nombre_a_clase_id.get(nombre_clase_ref)
    if clase_id_ref:
        if es_publico:
            ctx.imports_metodos.add(f"__DTO_RESPONSE__{clase_id_ref}")
            return f"{nombre_clase_ref}Response"
        ctx.imports_metodos_impl.add(f"__ENTITY__{clase_id_ref}")
        return nombre_clase_ref
    tipo = _tipo_java(tipo_uml)
    _registrar_import_tipo(ctx.imports_metodos if es_publico else ctx.imports_metodos_impl, tipo)
    return tipo


def _campo_unico(nombre_base: str, usados: set[str]) -> str:
    nombre = nombre_base
    contador = 2
    while nombre in usados:
        nombre = f"{nombre_base}{contador}"
        contador += 1
    usados.add(nombre)
    return nombre


def _registrar_import_tipo(imports: set[str], tipo_java: str) -> None:
    extra = _IMPORTS_POR_TIPO_JAVA.get(tipo_java)
    if extra:
        imports.add(extra)


def _resolver_marcadores_import(
    imports_con_marcadores: set[str], contextos: dict[str, "_ContextoClase"], paquete_base: str
) -> set[str]:
    """Los imports que dependen de otra clase (repositorio, DTO Response,
    entidad) se guardan como marcador con el id de esa clase, porque el
    paquete final no se conoce hasta ahora. Un import que ya viene resuelto
    (ej. "java.time.LocalDate") se deja igual."""
    resueltos: set[str] = set()
    for item in imports_con_marcadores:
        if item.startswith("__REPO__"):
            clase = contextos[item[len("__REPO__") :]]
            resueltos.add(f"{paquete_base}.repository.{clase.nombre_clase}Repository")
        elif item.startswith("__DTO_RESPONSE__"):
            clase = contextos[item[len("__DTO_RESPONSE__") :]]
            resueltos.add(f"{paquete_base}.dto.response.{clase.nombre_clase}Response")
        elif item.startswith("__ENTITY__"):
            clase = contextos[item[len("__ENTITY__") :]]
            resueltos.add(f"{paquete_base}.entity.{clase.nombre_clase}")
        else:
            resueltos.add(item)
    return resueltos


def _agregar_muchos_a_muchos(rel_id: str, origen: _ContextoClase, destino: _ContextoClase) -> None:
    tabla_join = f"{origen.tabla}_{destino.tabla}"
    columna_origen = f"{origen.tabla}_id"
    columna_destino = f"{destino.tabla}_id"

    campo_en_origen = _campo_unico(_camel(destino.nombre_clase) + "List", origen.nombres_usados)
    origen.relaciones_entidad.append(
        {
            "anotacion_completa": "ManyToMany",
            "lineas_extra": [
                "@JoinTable(\n"
                f'            name = "{tabla_join}",\n'
                f'            joinColumns = @JoinColumn(name = "{columna_origen}"),\n'
                f'            inverseJoinColumns = @JoinColumn(name = "{columna_destino}")\n'
                "    )"
            ],
            "tipo_campo": f"List<{destino.nombre_clase}>",
            "nombre_campo": campo_en_origen,
        }
    )
    origen.imports_entity.add("java.util.List")

    campo_en_destino = _campo_unico(_camel(origen.nombre_clase) + "List", destino.nombres_usados)
    destino.relaciones_entidad.append(
        {
            "anotacion_completa": f'ManyToMany(mappedBy = "{campo_en_origen}")',
            "lineas_extra": ["@JsonIgnore"],
            "tipo_campo": f"List<{origen.nombre_clase}>",
            "nombre_campo": campo_en_destino,
        }
    )
    destino.imports_entity.add("java.util.List")
    destino.imports_entity.add("com.fasterxml.jackson.annotation.JsonIgnore")


def _agregar_uno_a_muchos(
    lado_muchos: _ContextoClase, lado_uno: _ContextoClase, es_composicion: bool, card_lado_uno: str | None
) -> None:
    # el lado "muchos" lleva la FK (@ManyToOne); el lado "uno" queda con la
    # coleccion inversa (@OneToMany mappedBy). La nulabilidad de la FK la da
    # la cardinalidad del lado al que apunta (lado_uno).
    campo_fk = _campo_unico(_camel(lado_uno.nombre_clase), lado_muchos.nombres_usados)
    columna_fk = f"{_snake(lado_uno.nombre_clase)}_id"
    nullable = "false" if _requerido(card_lado_uno) else "true"
    lado_muchos.relaciones_entidad.append(
        {
            "anotacion_completa": "ManyToOne(fetch = FetchType.LAZY)",
            "lineas_extra": [f'@JoinColumn(name = "{columna_fk}", nullable = {nullable})'],
            "tipo_campo": lado_uno.nombre_clase,
            "nombre_campo": campo_fk,
        }
    )
    lado_muchos.campos_dto.append({"nombre": f"{campo_fk}Id", "tipo_java": "Long", "validacion": None if nullable == "true" else "NotNull"})
    if nullable == "false":
        lado_muchos.imports_validacion.add("jakarta.validation.constraints.NotNull")
    lado_muchos.argumentos_respuesta.append(
        f"entidad.get{_pascal(campo_fk)}() != null ? entidad.get{_pascal(campo_fk)}().getId() : null"
    )
    nombre_repo = f"{lado_uno.nombre_clase}Repository"
    lado_muchos.dependencias_servicio[nombre_repo] = {"tipo": nombre_repo, "nombre": _camel(nombre_repo)}
    lado_muchos.imports_service.add(f"__REPO__{lado_uno.clase_id}")
    lado_muchos.asignaciones.append(
        f"entidad.set{_pascal(campo_fk)}(datos.{campo_fk}Id() != null ? "
        f"{_camel(nombre_repo)}.findById(datos.{campo_fk}Id()).orElse(null) : null);"
    )

    campo_coleccion = _campo_unico(_camel(lado_muchos.nombre_clase) + "List", lado_uno.nombres_usados)
    lineas_extra = ["@JsonIgnore"]
    if es_composicion:
        anotacion = f'OneToMany(mappedBy = "{campo_fk}", cascade = CascadeType.ALL, orphanRemoval = true)'
    else:
        anotacion = f'OneToMany(mappedBy = "{campo_fk}")'
    lado_uno.relaciones_entidad.append(
        {
            "anotacion_completa": anotacion,
            "lineas_extra": lineas_extra,
            "tipo_campo": f"List<{lado_muchos.nombre_clase}>",
            "nombre_campo": campo_coleccion,
        }
    )
    lado_uno.imports_entity.add("java.util.List")
    lado_uno.imports_entity.add("com.fasterxml.jackson.annotation.JsonIgnore")


def _agregar_uno_a_uno(
    dueno: _ContextoClase, inverso: _ContextoClase, es_composicion: bool, card_lado_apuntado: str | None
) -> None:
    campo_fk = _campo_unico(_camel(inverso.nombre_clase), dueno.nombres_usados)
    columna_fk = f"{_snake(inverso.nombre_clase)}_id"
    nullable = "false" if _requerido(card_lado_apuntado) else "true"
    dueno.relaciones_entidad.append(
        {
            "anotacion_completa": "OneToOne(fetch = FetchType.LAZY)",
            "lineas_extra": [f'@JoinColumn(name = "{columna_fk}", nullable = {nullable}, unique = true)'],
            "tipo_campo": inverso.nombre_clase,
            "nombre_campo": campo_fk,
        }
    )
    dueno.campos_dto.append({"nombre": f"{campo_fk}Id", "tipo_java": "Long", "validacion": None if nullable == "true" else "NotNull"})
    if nullable == "false":
        dueno.imports_validacion.add("jakarta.validation.constraints.NotNull")
    dueno.argumentos_respuesta.append(
        f"entidad.get{_pascal(campo_fk)}() != null ? entidad.get{_pascal(campo_fk)}().getId() : null"
    )
    nombre_repo = f"{inverso.nombre_clase}Repository"
    dueno.dependencias_servicio[nombre_repo] = {"tipo": nombre_repo, "nombre": _camel(nombre_repo)}
    dueno.imports_service.add(f"__REPO__{inverso.clase_id}")
    dueno.asignaciones.append(
        f"entidad.set{_pascal(campo_fk)}(datos.{campo_fk}Id() != null ? "
        f"{_camel(nombre_repo)}.findById(datos.{campo_fk}Id()).orElse(null) : null);"
    )

    campo_inverso = _campo_unico(_camel(dueno.nombre_clase), inverso.nombres_usados)
    lineas_extra = ["@JsonIgnore"]
    anotacion = f'OneToOne(mappedBy = "{campo_fk}"'
    if es_composicion:
        anotacion += ", cascade = CascadeType.ALL, orphanRemoval = true"
    anotacion += ")"
    inverso.relaciones_entidad.append(
        {
            "anotacion_completa": anotacion,
            "lineas_extra": lineas_extra,
            "tipo_campo": dueno.nombre_clase,
            "nombre_campo": campo_inverso,
        }
    )
    inverso.imports_entity.add("com.fasterxml.jackson.annotation.JsonIgnore")


def _agregar_clase_asociada(
    asociada: _ContextoClase, origen: _ContextoClase, destino: _ContextoClase
) -> None:
    """Una relacion con clase asociada (AssociationClass) equivale a
    descomponer un muchos-a-muchos en dos relaciones uno-a-muchos hacia una
    clase intermedia: la asociada siempre necesita las dos puntas (no puede
    existir sin origen ni sin destino), asi que ambas FK son obligatorias
    sin importar la cardinalidad que traiga la relacion."""
    if asociada.pk_atributo_id is not None:
        # tiene su propio id: entidad normal con dos FK obligatorias
        _agregar_uno_a_muchos(asociada, origen, False, "1")
        _agregar_uno_a_muchos(asociada, destino, False, "1")
        return

    # sin id propio: la identidad es la combinacion de las dos relaciones,
    # con una clave compuesta @Embeddable (ver embeddable_id.java.jinja2)
    campo_origen = _campo_unico(_camel(origen.nombre_clase), asociada.nombres_usados)
    campo_destino = _campo_unico(_camel(destino.nombre_clase), asociada.nombres_usados)
    asociada.usa_id_compuesto = True
    asociada.id_compuesto_clase = f"{origen.nombre_clase}{destino.nombre_clase}Id"
    asociada.id_compuesto_campos = [
        {"nombre_id": f"{campo_origen}Id", "nombre_relacion": campo_origen, "tipo_java": origen.pk_tipo_java},
        {"nombre_id": f"{campo_destino}Id", "nombre_relacion": campo_destino, "tipo_java": destino.pk_tipo_java},
    ]

    for campo, clase_relacionada in ((campo_origen, origen), (campo_destino, destino)):
        columna_fk = f"{_snake(clase_relacionada.nombre_clase)}_id"
        asociada.relaciones_entidad.append(
            {
                "anotacion_completa": "ManyToOne(fetch = FetchType.LAZY)",
                "lineas_extra": [
                    f'@MapsId("{campo}Id")',
                    f'@JoinColumn(name = "{columna_fk}", nullable = false)',
                ],
                "tipo_campo": clase_relacionada.nombre_clase,
                "nombre_campo": campo,
            }
        )
        nombre_repo = f"{clase_relacionada.nombre_clase}Repository"
        asociada.dependencias_servicio[nombre_repo] = {"tipo": nombre_repo, "nombre": _camel(nombre_repo)}
        asociada.imports_service.add(f"__REPO__{clase_relacionada.clase_id}")
        asociada.asignaciones.append(
            f"entidad.set{_pascal(campo)}(datos.{campo}Id() != null ? "
            f"{_camel(nombre_repo)}.findById(datos.{campo}Id()).orElse(null) : null);"
        )

        campo_coleccion = _campo_unico(_camel(asociada.nombre_clase) + "List", clase_relacionada.nombres_usados)
        clase_relacionada.relaciones_entidad.append(
            {
                "anotacion_completa": f'OneToMany(mappedBy = "{campo}")',
                "lineas_extra": ["@JsonIgnore"],
                "tipo_campo": f"List<{asociada.nombre_clase}>",
                "nombre_campo": campo_coleccion,
            }
        )
        clase_relacionada.imports_entity.add("java.util.List")
        clase_relacionada.imports_entity.add("com.fasterxml.jackson.annotation.JsonIgnore")


def generar_proyecto(
    clases: dict,
    relaciones: dict,
    nombre_proyecto: str,
    config: dict,
) -> bytes:
    """Genera el .zip de un proyecto Spring Boot a partir del lienzo y la
    configuracion de transpilacion (group_id, artifact_id, java_version,
    spring_boot_version, base_datos)."""
    group_id = config["group_id"]
    artifact_id = config["artifact_id"]
    paquete_base = ".".join(_segmento_paquete(p) for p in group_id.split(".")) + "." + _segmento_paquete(
        artifact_id
    )
    ruta_paquete = paquete_base.replace(".", "/")
    nombre_clase_principal = _pascal(artifact_id) + "Application"

    bd = config["base_datos"]
    bd_info = _BD_INFO[bd if isinstance(bd, str) else bd.value]

    contextos = _construir_contextos(clases, relaciones)
    # resuelve los imports que quedaron como marcador (repositorio, DTO
    # Response o entidad de otra clase) ahora que ya se conoce el paquete
    for ctx in contextos.values():
        ctx.imports_service = _resolver_marcadores_import(ctx.imports_service, contextos, paquete_base)
        ctx.imports_metodos = _resolver_marcadores_import(ctx.imports_metodos, contextos, paquete_base)
        ctx.imports_metodos_impl = _resolver_marcadores_import(
            ctx.imports_metodos_impl, contextos, paquete_base
        )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        raiz = f"{artifact_id}/"

        zf.writestr(
            raiz + "pom.xml",
            _env.get_template("pom.xml.jinja2").render(
                group_id=group_id,
                artifact_id=artifact_id,
                java_version=config["java_version"],
                spring_boot_version=config["spring_boot_version"],
                bd_dependencia=bd_info["dependencia"],
            ),
        )
        zf.writestr(
            raiz + "README.md",
            _env.get_template("README.md.jinja2").render(
                artifact_id=artifact_id,
                nombre_proyecto=nombre_proyecto,
                group_id=group_id,
                java_version=config["java_version"],
                spring_boot_version=config["spring_boot_version"],
                base_datos=bd if isinstance(bd, str) else bd.value,
                paquete_base=paquete_base,
            ),
        )
        zf.writestr(
            raiz + "src/main/resources/application.properties",
            _env.get_template("application.properties.jinja2").render(
                artifact_id=artifact_id,
                datasource_url=bd_info["url"].format(db=_segmento_paquete(artifact_id)),
                datasource_username=bd_info["usuario"],
                datasource_password=bd_info["clave"],
                datasource_driver=bd_info["driver"],
                hibernate_dialect=bd_info["dialecto"],
            ),
        )
        zf.writestr(
            raiz + "Dockerfile",
            _env.get_template("Dockerfile.jinja2").render(java_version=config["java_version"]),
        )
        zf.writestr(
            raiz + "docker-compose.yml",
            _env.get_template("docker-compose.yml.jinja2").render(
                nombre_bd=_segmento_paquete(artifact_id),
            ),
        )
        zf.writestr(
            f"{raiz}src/main/java/{ruta_paquete}/{nombre_clase_principal}.java",
            _env.get_template("application.java.jinja2").render(
                paquete_base=paquete_base, nombre_clase_principal=nombre_clase_principal
            ),
        )

        for ctx in contextos.values():
            id_vars = _variables_id(ctx)
            if ctx.usa_id_compuesto:
                zf.writestr(
                    f"{raiz}src/main/java/{ruta_paquete}/entity/{ctx.id_compuesto_clase}.java",
                    _env.get_template("embeddable_id.java.jinja2").render(
                        paquete_base=paquete_base,
                        nombre_clase=ctx.id_compuesto_clase,
                        campos=ctx.id_compuesto_campos,
                    ),
                )
            zf.writestr(
                f"{raiz}src/main/java/{ruta_paquete}/entity/{ctx.nombre_clase}.java",
                _env.get_template("entity.java.jinja2").render(
                    paquete_base=paquete_base,
                    imports=sorted(ctx.imports_entity),
                    tabla=ctx.tabla,
                    tiene_subclases=ctx.tiene_subclases,
                    nombre_clase=ctx.nombre_clase,
                    extiende=ctx.extiende,
                    pk_tipo_java=ctx.pk_tipo_java,
                    pk_generado=ctx.pk_generado,
                    pk_modificador=ctx.pk_modificador,
                    usa_id_compuesto=ctx.usa_id_compuesto,
                    id_compuesto_clase=ctx.id_compuesto_clase,
                    atributos=_atributos_entidad(ctx),
                    relaciones=ctx.relaciones_entidad,
                ),
            )
            zf.writestr(
                f"{raiz}src/main/java/{ruta_paquete}/dto/request/{ctx.nombre_clase}Request.java",
                _env.get_template("request_dto.java.jinja2").render(
                    paquete_base=paquete_base,
                    imports=sorted(ctx.imports_dto | ctx.imports_validacion),
                    nombre_clase=ctx.nombre_clase,
                    campos=_campos_dto_texto(ctx, incluir_id=False, con_validacion=True),
                ),
            )
            zf.writestr(
                f"{raiz}src/main/java/{ruta_paquete}/dto/response/{ctx.nombre_clase}Response.java",
                _env.get_template("response_dto.java.jinja2").render(
                    paquete_base=paquete_base,
                    imports=sorted(ctx.imports_dto),
                    nombre_clase=ctx.nombre_clase,
                    campos=_campos_dto_texto(ctx, incluir_id=True, con_validacion=False),
                ),
            )
            zf.writestr(
                f"{raiz}src/main/java/{ruta_paquete}/repository/{ctx.nombre_clase}Repository.java",
                _env.get_template("repository.java.jinja2").render(
                    paquete_base=paquete_base,
                    nombre_clase=ctx.nombre_clase,
                    pk_tipo_java=ctx.id_compuesto_clase if ctx.usa_id_compuesto else ctx.pk_tipo_java,
                    id_compuesto_clase=ctx.id_compuesto_clase,
                ),
            )
            zf.writestr(
                f"{raiz}src/main/java/{ruta_paquete}/service/{ctx.nombre_clase}Service.java",
                _env.get_template("service_interface.java.jinja2").render(
                    paquete_base=paquete_base,
                    imports=sorted(ctx.imports_metodos),
                    nombre_clase=ctx.nombre_clase,
                    parametros_id=id_vars["parametros_id"],
                    metodos=ctx.metodos_interfaz,
                ),
            )
            zf.writestr(
                f"{raiz}src/main/java/{ruta_paquete}/service/impl/{ctx.nombre_clase}ServiceImpl.java",
                _env.get_template("service.java.jinja2").render(
                    paquete_base=paquete_base,
                    imports=sorted(ctx.imports_service | ctx.imports_metodos | ctx.imports_metodos_impl),
                    nombre_clase=ctx.nombre_clase,
                    id_compuesto_clase=ctx.id_compuesto_clase,
                    parametros_id=id_vars["parametros_id"],
                    argumentos_id=id_vars["argumentos_id"],
                    argumento_find_by_id=id_vars["argumento_find_by_id"],
                    expresion_error_id=id_vars["expresion_error_id"],
                    dependencias=list(ctx.dependencias_servicio.values()),
                    asignaciones=ctx.asignaciones,
                    argumentos_respuesta=ctx.argumentos_respuesta,
                    metodos_interfaz=ctx.metodos_interfaz,
                    metodos_extra=ctx.metodos_extra,
                ),
            )
            zf.writestr(
                f"{raiz}src/main/java/{ruta_paquete}/controller/{ctx.nombre_clase}Controller.java",
                _env.get_template("controller.java.jinja2").render(
                    paquete_base=paquete_base,
                    nombre_clase=ctx.nombre_clase,
                    parametros_id_controller=id_vars["parametros_id_controller"],
                    argumentos_id=id_vars["argumentos_id"],
                    anotacion_obtener=id_vars["anotacion_obtener"],
                    anotacion_actualizar=id_vars["anotacion_actualizar"],
                    anotacion_eliminar=id_vars["anotacion_eliminar"],
                    nombre_recurso=_recurso_url(ctx.nombre_clase),
                ),
            )

    return buffer.getvalue()


def _variables_id(ctx: _ContextoClase) -> dict[str, str]:
    """Arma, en un solo lugar, todos los fragmentos de codigo que dependen de
    si la clase usa un id simple o una clave compuesta (@EmbeddedId): asi las
    plantillas de service/controller no necesitan ramas condicionales, solo
    insertan el string ya resuelto."""
    if not ctx.usa_id_compuesto:
        return {
            "parametros_id": f"{ctx.pk_tipo_java} id",
            "argumentos_id": "id",
            "argumento_find_by_id": "id",
            "expresion_error_id": "id",
            "parametros_id_controller": f"@PathVariable {ctx.pk_tipo_java} id",
            "anotacion_obtener": '@GetMapping("/{id}")',
            "anotacion_actualizar": '@PutMapping("/{id}")',
            "anotacion_eliminar": '@DeleteMapping("/{id}")',
        }
    nombres = [c["nombre_id"] for c in ctx.id_compuesto_campos]
    argumentos_id = ", ".join(nombres)
    campos_query = ", ".join(f'"{n}"' for n in nombres)
    return {
        "parametros_id": ", ".join(f"{c['tipo_java']} {c['nombre_id']}" for c in ctx.id_compuesto_campos),
        "argumentos_id": argumentos_id,
        "argumento_find_by_id": f"new {ctx.id_compuesto_clase}({argumentos_id})",
        "expresion_error_id": ' + ", " + '.join(nombres),
        "parametros_id_controller": ", ".join(
            f"@RequestParam {c['tipo_java']} {c['nombre_id']}" for c in ctx.id_compuesto_campos
        ),
        "anotacion_obtener": f"@GetMapping(params = {{{campos_query}}})",
        "anotacion_actualizar": "@PutMapping",
        "anotacion_eliminar": "@DeleteMapping",
    }


def _atributos_entidad(ctx: _ContextoClase) -> list[dict]:
    # los campos_dto ya excluyen el id (se maneja aparte con @Id) pero
    # incluyen los *Id de relacion (que en la entidad NO son atributos, son
    # los campos de relaciones_entidad) asi que se filtran aqui
    ids_relacion = {r["nombre_campo"] + "Id" for r in ctx.relaciones_entidad}
    return [c for c in ctx.campos_dto if c["nombre"] != "id" and c["nombre"] not in ids_relacion]


def _campos_dto_texto(ctx: _ContextoClase, incluir_id: bool, con_validacion: bool) -> list[str]:
    textos = []
    for campo in ctx.campos_dto:
        if campo["nombre"] == "id" and not incluir_id:
            continue
        prefijo = f"@{campo['validacion']} " if con_validacion and campo["validacion"] else ""
        textos.append(f"{prefijo}{campo['tipo_java']} {campo['nombre']}")
    return textos


def _recurso_url(nombre_clase: str) -> str:
    return _snake(nombre_clase).replace("_", "-") + "s"
