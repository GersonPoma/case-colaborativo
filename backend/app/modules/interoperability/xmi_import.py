import re
import uuid
from xml.etree.ElementTree import Element, ParseError, fromstring

from app.core.exceptions import AppException
from app.modules.interoperability.xmi_export import NS_XMI

_GEOMETRIA_RE = re.compile(r"Left=(-?\d+);Top=(-?\d+);")

_VISIBILIDAD_DESDE_XMI = {
    "public": "PUBLICO",
    "private": "PRIVADO",
    "protected": "PROTEGIDO",
    "package": "PAQUETE",
}

_AGREGACION_DESDE_XMI = {
    "shared": "AGREGACION",
    "composite": "COMPOSICION",
}

_ANCHO_MINIMO_CLASE = 90


def _q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _tipo_xmi(el: Element) -> str | None:
    return el.get(_q(NS_XMI, "type"))


def _id_xmi(el: Element) -> str | None:
    return el.get(_q(NS_XMI, "id"))


def _idref(el: Element) -> str | None:
    return el.get(_q(NS_XMI, "idref"))


def _leer_cardinalidad(extremo: Element) -> str | None:
    lower = extremo.find("lowerValue")
    upper = extremo.find("upperValue")
    if lower is None or upper is None:
        return None
    inferior = lower.get("value")
    superior = upper.get("value")
    if inferior is None or superior is None:
        return None
    return inferior if inferior == superior else f"{inferior}..{superior}"


def _leer_posiciones_diagrama(raiz: Element) -> dict[str, tuple[int, int]]:
    """Si el archivo trae un bloque xmi:Extension con diagrama (el nuestro, o uno
    nativo de EA), se puede reaprovechar la posicion de cada clase en vez de
    forzar una cuadricula. "subject" en cada <element> del diagrama apunta al
    mismo xmi:id que la clase declara en su packagedElement, en ambos casos."""
    posiciones: dict[str, tuple[int, int]] = {}
    for el in raiz.iter("element"):
        geometria = el.get("geometry")
        referencia = el.get("subject")
        if not geometria or not referencia:
            continue
        coincidencia = _GEOMETRIA_RE.match(geometria)
        if coincidencia:
            posiciones[referencia] = (int(coincidencia.group(1)), int(coincidencia.group(2)))
    return posiciones


def importar_xmi(contenido: bytes) -> dict:
    """Reconstruye clases/relaciones a partir de un XMI 2.1/UML2 estandar (el mismo
    formato que produce construir_xmi con para_ea=False). Genera ids internos nuevos
    para cada elemento; los xmi:id del archivo solo se usan para resolver referencias
    (type/@idref, general, boundElement, client/supplier, memberEnd) durante el parseo."""
    try:
        raiz = fromstring(contenido)
    except ParseError as e:
        raise AppException(f"El archivo no es un XML válido: {e}") from e

    nombres_tipo: dict[str, str] = {}
    for el in raiz.iter("packagedElement"):
        if _tipo_xmi(el) == "uml:PrimitiveType":
            id_el = _id_xmi(el)
            nombre = el.get("name")
            if id_el and nombre:
                nombres_tipo[id_el] = nombre

    def _tipo_de(propiedad: Element) -> str | None:
        tipo_el = propiedad.find("type")
        if tipo_el is None:
            return None
        ref = _idref(tipo_el)
        return nombres_tipo.get(ref) if ref else None

    clases: dict[str, dict] = {}
    relaciones: dict[str, dict] = {}
    id_por_xmi: dict[str, str] = {}
    generalizaciones_pendientes: list[tuple[str, str]] = []
    bindings_pendientes: list[tuple[str, str]] = []

    def _nuevo_id() -> str:
        return str(uuid.uuid4())

    def _parsear_atributos_y_metodos(elemento_clase: Element) -> tuple[dict, dict]:
        atributos: dict[str, dict] = {}
        for orden, attr_el in enumerate(elemento_clase.findall("ownedAttribute")):
            # las que son extremos de asociacion (aggregation=...) no son atributos de negocio
            if attr_el.get("association"):
                continue
            aid = _nuevo_id()
            atributos[aid] = {
                "id": aid,
                "nombre": attr_el.get("name") or "",
                "tipo": _tipo_de(attr_el),
                "es_pk": attr_el.get("isID") == "true",
                "visibilidad": _VISIBILIDAD_DESDE_XMI.get(attr_el.get("visibility") or "", "PRIVADO"),
                "orden": orden,
            }

        metodos: dict[str, dict] = {}
        for orden, op_el in enumerate(elemento_clase.findall("ownedOperation")):
            parametros = []
            tipo_retorno = None
            for param_el in op_el.findall("ownedParameter"):
                if param_el.get("direction") == "return":
                    tipo_retorno = _tipo_de(param_el)
                else:
                    parametros.append({"nombre": param_el.get("name") or "", "tipo": _tipo_de(param_el) or ""})
            mid = _nuevo_id()
            metodos[mid] = {
                "id": mid,
                "nombre": op_el.get("name") or "",
                "tipo_retorno": tipo_retorno,
                "parametros": parametros,
                "visibilidad": _VISIBILIDAD_DESDE_XMI.get(op_el.get("visibility") or "", "PUBLICO"),
                "orden": orden,
            }

        return atributos, metodos

    def _registrar_clase(elemento: Element) -> None:
        xmi_id = _id_xmi(elemento)
        interno_id = _nuevo_id()
        if xmi_id:
            id_por_xmi[xmi_id] = interno_id

        atributos, metodos = _parsear_atributos_y_metodos(elemento)
        clases[interno_id] = {
            "id": interno_id,
            "nombre": elemento.get("name") or "Clase",
            "atributos": atributos,
            "metodos": metodos,
            "ui": {"x": 0, "y": 0, "ancho": _ANCHO_MINIMO_CLASE, "color": "#e3f2fd"},
        }

        for gen_el in elemento.findall("generalization"):
            general_ref = gen_el.get("general")
            if general_ref and xmi_id:
                generalizaciones_pendientes.append((xmi_id, general_ref))
        for bind_el in elemento.findall("templateBinding"):
            bound_ref = bind_el.get("boundElement")
            if bound_ref and xmi_id:
                bindings_pendientes.append((xmi_id, bound_ref))

    # 1a pasada: registrar todas las clases (para que las referencias hacia
    # adelante o hacia atras entre ellas se puedan resolver despues). Solo se
    # considera "packagedElement": el bloque xmi:Extension de EA repite un
    # <element xmi:type="uml:Class" xmi:idref="..."> por cada clase como resumen
    # (no es una declaracion), y con el mismo xmi:type se duplicaria todo.
    for el in raiz.iter("packagedElement"):
        if _tipo_xmi(el) in ("uml:Class", "uml:AssociationClass"):
            _registrar_clase(el)

    def _procesar_extremos(el: Element) -> tuple[str, dict] | None:
        extremos = el.findall("ownedEnd")
        if len(extremos) < 2:
            return None
        e1, e2 = extremos[0], extremos[1]
        tipo1, tipo2 = e1.find("type"), e2.find("type")
        origen_xmi = _idref(tipo1) if tipo1 is not None else None
        destino_xmi = _idref(tipo2) if tipo2 is not None else None
        origen_id = id_por_xmi.get(origen_xmi or "")
        destino_id = id_por_xmi.get(destino_xmi or "")
        if not origen_id or not destino_id:
            return None

        agregacion = e1.get("aggregation", "none")
        if agregacion == "none":
            agregacion = e2.get("aggregation", "none")

        rid = _nuevo_id()
        return rid, {
            "id": rid,
            "origen_id": origen_id,
            "destino_id": destino_id,
            "tipo": _AGREGACION_DESDE_XMI.get(agregacion, "ASOCIACION"),
            "cardinalidad_origen": _leer_cardinalidad(e1),
            "cardinalidad_destino": _leer_cardinalidad(e2),
            "etiqueta": el.get("name"),
            "clase_asociada_id": None,
            "ui": {"vertices": []},
        }

    # 2a pasada: asociaciones, clases de asociacion y realizaciones (top-level)
    for el in raiz.iter("packagedElement"):
        tipo = _tipo_xmi(el)
        if tipo == "uml:Association":
            resultado = _procesar_extremos(el)
            if resultado:
                rid, datos = resultado
                relaciones[rid] = datos
        elif tipo == "uml:AssociationClass":
            resultado = _procesar_extremos(el)
            if resultado:
                rid, datos = resultado
                xmi_id = _id_xmi(el)
                datos["clase_asociada_id"] = id_por_xmi.get(xmi_id or "")
                relaciones[rid] = datos
        elif tipo == "uml:Realization":
            client_ref, supplier_ref = el.get("client"), el.get("supplier")
            origen_id = id_por_xmi.get(client_ref or "")
            destino_id = id_por_xmi.get(supplier_ref or "")
            if origen_id and destino_id:
                rid = _nuevo_id()
                relaciones[rid] = {
                    "id": rid,
                    "origen_id": origen_id,
                    "destino_id": destino_id,
                    "tipo": "REALIZACION",
                    "cardinalidad_origen": None,
                    "cardinalidad_destino": None,
                    "etiqueta": None,
                    "clase_asociada_id": None,
                    "ui": {"vertices": []},
                }

    # generalizaciones (herencia) y template bindings, anidados dentro de cada clase
    for origen_xmi, general_xmi in generalizaciones_pendientes:
        origen_id = id_por_xmi.get(origen_xmi)
        destino_id = id_por_xmi.get(general_xmi)
        if origen_id and destino_id:
            rid = _nuevo_id()
            relaciones[rid] = {
                "id": rid,
                "origen_id": origen_id,
                "destino_id": destino_id,
                "tipo": "HERENCIA",
                "cardinalidad_origen": None,
                "cardinalidad_destino": None,
                "etiqueta": None,
                "clase_asociada_id": None,
                "ui": {"vertices": []},
            }
    for origen_xmi, bound_xmi in bindings_pendientes:
        origen_id = id_por_xmi.get(origen_xmi)
        destino_id = id_por_xmi.get(bound_xmi)
        if origen_id and destino_id:
            rid = _nuevo_id()
            relaciones[rid] = {
                "id": rid,
                "origen_id": origen_id,
                "destino_id": destino_id,
                "tipo": "TEMPLATE_BINDING",
                "cardinalidad_origen": None,
                "cardinalidad_destino": None,
                "etiqueta": None,
                "clase_asociada_id": None,
                "ui": {"vertices": []},
            }

    if not clases:
        raise AppException("El archivo no tiene ninguna clase UML reconocible")

    # el XMI puro (OMG) no trae posiciones - esas son del bloque propietario
    # xmi:Extension - pero si el archivo lo trae (nuestra exportacion para EA, o un
    # archivo nativo de EA), se reaprovechan; el resto cae a una cuadricula simple,
    # igual que "alinear" en el lienzo
    posiciones = _leer_posiciones_diagrama(raiz)
    sin_posicion: list[dict] = []
    for xmi_id, interno_id in id_por_xmi.items():
        clase = clases[interno_id]
        pos = posiciones.get(xmi_id)
        if pos:
            clase["ui"]["x"], clase["ui"]["y"] = pos
        else:
            sin_posicion.append(clase)

    for indice, clase in enumerate(sin_posicion):
        clase["ui"]["x"] = 80 + (indice % 4) * 260
        clase["ui"]["y"] = 80 + (indice // 4) * 220

    return {"clases": clases, "relaciones": relaciones}
