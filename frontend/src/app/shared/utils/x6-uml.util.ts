import { Graph } from '@antv/x6';
import type { CellAttrs } from '@antv/x6/lib/registry';
import type { EdgeLabel } from '@antv/x6/lib/model/edge';
import { Clase, Relacion, TipoRelacion } from '../../core/models/lienzo.model';

export const SIMBOLO_VISIBILIDAD: Record<string, string> = {
  PUBLICO: '+',
  PRIVADO: '-',
  PROTEGIDO: '#',
  PAQUETE: '~',
};

interface Marcador {
  name: string;
  width?: number;
  height?: number;
  fill?: string;
  stroke?: string;
}

interface ConfigRelacion {
  origen?: Marcador;
  destino?: Marcador;
  punteada?: boolean;
}

export const CONFIG_RELACION_POR_TIPO: Record<TipoRelacion, ConfigRelacion> = {
  ASOCIACION: {},
  AGREGACION: { destino: { name: 'diamond', width: 14, height: 8, fill: '#fff', stroke: '#555' } },
  COMPOSICION: {
    destino: { name: 'diamond', width: 14, height: 8, fill: '#555', stroke: '#555' },
  },
  HERENCIA: { destino: { name: 'block', width: 14, height: 12, fill: '#fff', stroke: '#555' } },
  REALIZACION: {
    destino: { name: 'block', width: 14, height: 12, fill: '#fff', stroke: '#555' },
    punteada: true,
  },
  TEMPLATE_BINDING: {
    destino: { name: 'classic', width: 10, height: 8, fill: '#fff', stroke: '#555' },
    punteada: true,
  },
};

function conectorAsociadaId(relacionId: string): string {
  return `${relacionId}::asociada`;
}

interface ClaseDibujable {
  ancho: number;
  alto: number;
  altoTitulo: number;
  yMetodos: number;
  attrs: Record<string, object>;
}

/** Mismo ancho por defecto que usa Enterprise Architect para una clase nueva vacía. */
const ANCHO_MINIMO_CLASE = 90;
const PADDING_HORIZONTAL_CLASE = 20;

let ctxMedidaTexto: CanvasRenderingContext2D | null | undefined;

function medirAnchoTexto(texto: string, fontWeight: number, fontSize: number): number {
  if (ctxMedidaTexto === undefined) {
    ctxMedidaTexto = document.createElement('canvas').getContext('2d');
  }
  if (!ctxMedidaTexto) {
    return texto.length * fontSize * 0.6; // estimación de reserva si el canvas 2D no está disponible
  }
  ctxMedidaTexto.font = `${fontWeight} ${fontSize}px sans-serif`;
  return ctxMedidaTexto.measureText(texto).width;
}

function construirClaseDibujable(clase: Clase): ClaseDibujable {
  const altoLinea = 15;
  const padVertical = 8; // 4 arriba + 4 abajo

  const atributos = Object.values(clase.atributos)
    .sort((a, b) => a.orden - b.orden)
    .map((a) => {
      const simbolo = SIMBOLO_VISIBILIDAD[a.visibilidad] ?? '-';
      return `${simbolo} ${a.nombre}${a.tipo ? ': ' + a.tipo : ''}`;
    });

  const metodos = Object.values(clase.metodos)
    .sort((a, b) => a.orden - b.orden)
    .map((m) => {
      const simbolo = SIMBOLO_VISIBILIDAD[m.visibilidad] ?? '+';
      const parametros = m.parametros.map((p) => `${p.nombre}: ${p.tipo}`).join(', ');
      const retorno = m.tipo_retorno || 'void';
      return `${simbolo} ${m.nombre}(${parametros}): ${retorno}`;
    });

  const anchoContenido = Math.max(
    medirAnchoTexto(clase.nombre, 700, 12),
    ...atributos.map((texto) => medirAnchoTexto(texto, 400, 10)),
    ...metodos.map((texto) => medirAnchoTexto(texto, 400, 10)),
    0,
  );
  const ancho = Math.max(ANCHO_MINIMO_CLASE, Math.ceil(anchoContenido) + PADDING_HORIZONTAL_CLASE);

  const hayAtributos = atributos.length > 0;
  const hayMetodos = metodos.length > 0;
  const totalmenteVacia = !hayAtributos && !hayMetodos;
  const altoSeccionVacia = altoLinea + padVertical;

  const altoTitulo = 26;
  const altoAtributos = hayAtributos
    ? atributos.length * altoLinea + padVertical
    : totalmenteVacia
      ? altoSeccionVacia
      : 0;
  const altoMetodos = hayMetodos
    ? metodos.length * altoLinea + padVertical
    : totalmenteVacia
      ? altoSeccionVacia
      : 0;
  const yAtributos = altoTitulo;
  const yMetodos = altoTitulo + altoAtributos;
  const alto = altoTitulo + altoAtributos + altoMetodos;

  return {
    ancho,
    alto,
    altoTitulo,
    yMetodos,
    attrs: {
      body: {
        fill: clase.ui.color || '#e3f2fd',
        stroke: '#555',
        strokeWidth: 1,
        rx: 4,
        ry: 4,
      },
      titulo: {
        text: clase.nombre,
        fontWeight: 700,
        fontSize: 12,
        fill: '#222',
        textAnchor: 'middle',
        textVerticalAnchor: 'middle',
        refX: '50%',
        refY: altoTitulo / 2,
      },
      divisor1: {
        x1: 0,
        y1: altoTitulo,
        x2: ancho,
        y2: altoTitulo,
        stroke: hayAtributos || hayMetodos ? '#555' : 'none',
        strokeWidth: 1,
      },
      atributos: {
        text: atributos.join('\n') || ' ',
        fontSize: 10,
        lineHeight: altoLinea,
        fill: '#444',
        textAnchor: 'start',
        textVerticalAnchor: 'top',
        refX: 8,
        refY: yAtributos + padVertical / 2,
      },
      divisor2: {
        x1: 0,
        y1: yMetodos,
        x2: ancho,
        y2: yMetodos,
        stroke: hayAtributos && hayMetodos ? '#555' : 'none',
        strokeWidth: 1,
      },
      metodos: {
        text: metodos.join('\n') || ' ',
        fontSize: 10,
        lineHeight: altoLinea,
        fill: '#444',
        textAnchor: 'start',
        textVerticalAnchor: 'top',
        refX: 8,
        refY: yMetodos + padVertical / 2,
      },
    },
  };
}

export function agregarNodoClase(graph: Graph, clase: Clase, interactivo: boolean): void {
  const d = construirClaseDibujable(clase);
  graph.addNode({
    id: clase.id,
    x: clase.ui.x,
    y: clase.ui.y,
    width: d.ancho,
    height: d.alto,
    movable: interactivo,
    markup: [
      { tagName: 'rect', selector: 'body' },
      { tagName: 'text', selector: 'titulo' },
      { tagName: 'line', selector: 'divisor1' },
      { tagName: 'text', selector: 'atributos' },
      { tagName: 'line', selector: 'divisor2' },
      { tagName: 'text', selector: 'metodos' },
    ],
    attrs: {
      ...d.attrs,
      body: { ...(d.attrs['body'] as object), cursor: interactivo ? 'move' : 'default' },
    },
  });
}

function construirLabelsRelacion(relacion: Relacion): EdgeLabel[] {
  const labels: EdgeLabel[] = [];
  if (relacion.cardinalidad_origen) {
    labels.push({
      attrs: { text: { text: relacion.cardinalidad_origen, fontSize: 9, fill: '#555' } },
      position: { distance: 0.12 },
    });
  }
  if (relacion.tipo === 'TEMPLATE_BINDING') {
    const texto = relacion.etiqueta ? `«bind» ${relacion.etiqueta}` : '«bind»';
    labels.push({
      attrs: { text: { text: texto, fontSize: 9, fill: '#333' } },
      position: { distance: 0.5 },
    });
  } else if (relacion.etiqueta) {
    labels.push({
      attrs: { text: { text: relacion.etiqueta, fontSize: 10, fill: '#333', fontStyle: 'italic' } },
      position: { distance: 0.5 },
    });
  }
  if (relacion.cardinalidad_destino) {
    labels.push({
      attrs: { text: { text: relacion.cardinalidad_destino, fontSize: 9, fill: '#555' } },
      position: { distance: 0.88 },
    });
  }
  return labels;
}

function construirAttrsLineaRelacion(relacion: Relacion): CellAttrs {
  const config = CONFIG_RELACION_POR_TIPO[relacion.tipo] ?? {};
  return {
    line: {
      stroke: '#555',
      strokeWidth: 1.5,
      strokeDasharray: config.punteada ? '5 3' : undefined,
      sourceMarker: config.origen ?? null,
      targetMarker: config.destino ?? null,
    },
  } as CellAttrs;
}

function agregarEdgeRelacion(graph: Graph, relacion: Relacion, interactivo: boolean): void {
  graph.addEdge({
    id: relacion.id,
    source: relacion.origen_id,
    target: relacion.destino_id,
    attrs: construirAttrsLineaRelacion(relacion),
    labels: construirLabelsRelacion(relacion),
    interacting: interactivo ? undefined : false,
  });

  if (relacion.clase_asociada_id) {
    graph.addEdge({
      id: conectorAsociadaId(relacion.id),
      source: { cell: relacion.id, anchor: { name: 'ratio', args: { ratio: 0.5 } } },
      target: relacion.clase_asociada_id,
      attrs: {
        line: {
          stroke: '#888',
          strokeWidth: 1,
          strokeDasharray: '3 3',
          targetMarker: null,
          sourceMarker: null,
        },
      },
      zIndex: -1,
      interacting: false,
    });
  }
}

/** Dibuja todo el lienzo desde cero (usado por vistas de solo lectura, no interactivas). */
export function dibujarLienzoCompleto(
  graph: Graph,
  clases: Record<string, Clase>,
  relaciones: Record<string, Relacion>,
  interactivo: boolean,
): void {
  graph.clearCells();
  for (const clase of Object.values(clases)) {
    agregarNodoClase(graph, clase, interactivo);
  }
  for (const relacion of Object.values(relaciones)) {
    agregarEdgeRelacion(graph, relacion, interactivo);
  }
}

/**
 * Sincroniza el grafo con el estado actual sin recrear los nodos existentes:
 * los nodos que ya están en el grafo se reposicionan/actualizan en el lugar
 * (necesario para que arrastrar una clase no se vea como si se "duplicara"
 * mientras se espera la confirmación del servidor).
 */
export function sincronizarClases(graph: Graph, clases: Record<string, Clase>, interactivo: boolean): void {
  const idsDeseados = new Set(Object.keys(clases));

  for (const nodo of graph.getNodes()) {
    if (!idsDeseados.has(String(nodo.id))) {
      graph.removeCell(nodo);
    }
  }

  for (const clase of Object.values(clases)) {
    const existente = graph.getCellById(clase.id);
    if (existente && existente.isNode()) {
      const d = construirClaseDibujable(clase);
      existente.resize(d.ancho, d.alto);
      existente.position(clase.ui.x, clase.ui.y);
      existente.setAttrs({
        ...d.attrs,
        body: { ...(d.attrs['body'] as object), cursor: interactivo ? 'move' : 'default' },
      });
      existente.prop('movable', interactivo, { silent: true });
    } else {
      agregarNodoClase(graph, clase, interactivo);
    }
  }
}

function huellaRelacion(relacion: Relacion): string {
  return [
    relacion.origen_id,
    relacion.destino_id,
    relacion.tipo,
    relacion.cardinalidad_origen,
    relacion.cardinalidad_destino,
    relacion.etiqueta,
    relacion.clase_asociada_id,
  ].join('|');
}

/**
 * `huellas` es un Map que debe vivir en el componente que llama (una instancia
 * por CanvasBoard) para recordar, entre llamadas, qué relación ya está dibujada
 * y con qué datos. Sin esto, cada redibujado (p. ej. al mover OTRA clase sin
 * relación) volvía a borrar y recrear TODAS las relaciones, lo que en X6 podía
 * dejar bordes fantasma acumulándose visualmente.
 */
export function sincronizarRelaciones(
  graph: Graph,
  relaciones: Record<string, Relacion>,
  interactivo: boolean,
  huellas: Map<string, string>,
): void {
  for (const id of [...huellas.keys()]) {
    if (!relaciones[id]) {
      const borde = graph.getCellById(id);
      if (borde) {
        graph.removeCell(borde);
      }
      const conector = graph.getCellById(conectorAsociadaId(id));
      if (conector) {
        graph.removeCell(conector);
      }
      huellas.delete(id);
    }
  }

  for (const relacion of Object.values(relaciones)) {
    if (!graph.getCellById(relacion.origen_id) || !graph.getCellById(relacion.destino_id)) {
      continue;
    }

    const huella = huellaRelacion(relacion);
    if (huellas.get(relacion.id) === huella && graph.getCellById(relacion.id)) {
      continue; // nada relevante cambió: no la tocamos, evita duplicados fantasma
    }

    const bordeExistente = graph.getCellById(relacion.id);
    const esEdgeExistente = bordeExistente !== null && bordeExistente.isEdge();
    const mismaTopologia =
      esEdgeExistente &&
      String(bordeExistente.getSourceCellId()) === relacion.origen_id &&
      String(bordeExistente.getTargetCellId()) === relacion.destino_id;

    if (esEdgeExistente && mismaTopologia) {
      // Actualiza en el lugar en vez de borrar y recrear: recrear la arista con el
      // mismo id podía dejar el <text> de los labels (cardinalidades) con contenido
      // mezclado entre el valor anterior y el nuevo (p. ej. "1..1" -> "0" quedaba
      // como "010"), porque X6 reutiliza la vista de la celda al reinsertarla.
      bordeExistente.setLabels(construirLabelsRelacion(relacion));
      bordeExistente.setAttrs(construirAttrsLineaRelacion(relacion));
    } else {
      if (bordeExistente) {
        graph.removeCell(bordeExistente);
      }
      const conectorExistente = graph.getCellById(conectorAsociadaId(relacion.id));
      if (conectorExistente) {
        graph.removeCell(conectorExistente);
      }
      agregarEdgeRelacion(graph, relacion, interactivo);
    }
    huellas.set(relacion.id, huella);
  }
}
