import { isPlatformBrowser } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  PLATFORM_ID,
  effect,
  inject,
  input,
  viewChild,
} from '@angular/core';
import { Graph } from '@antv/x6';
import { Clase, EstadoLienzo, Relacion, TipoRelacion } from '../../../core/models/lienzo.model';

const SIMBOLO_VISIBILIDAD: Record<string, string> = {
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

const CONFIG_POR_TIPO: Record<TipoRelacion, ConfigRelacion> = {
  ASOCIACION: {},
  AGREGACION: { origen: { name: 'diamond', width: 14, height: 8, fill: '#fff', stroke: '#555' } },
  COMPOSICION: {
    origen: { name: 'diamond', width: 14, height: 8, fill: '#555', stroke: '#555' },
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

@Component({
  selector: 'app-diagram-preview',
  imports: [],
  templateUrl: './diagram-preview.html',
  styleUrl: './diagram-preview.scss',
})
export class DiagramPreview implements AfterViewInit, OnDestroy {
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly contenedor = viewChild.required<ElementRef<HTMLDivElement>>('contenedor');

  readonly lienzo = input<EstadoLienzo | null>(null);

  private graph: Graph | null = null;

  constructor() {
    effect(() => {
      const lienzo = this.lienzo();
      if (this.graph && lienzo) {
        this.dibujar(lienzo);
      }
    });
  }

  ngAfterViewInit(): void {
    if (!this.isBrowser) {
      return;
    }

    const elemento = this.contenedor().nativeElement;

    this.graph = new Graph({
      container: elemento,
      width: elemento.clientWidth || 600,
      height: 400,
      interacting: false,
      panning: true,
      mousewheel: true,
    });

    const lienzo = this.lienzo();
    if (lienzo) {
      this.dibujar(lienzo);
    }
  }

  ngOnDestroy(): void {
    this.graph?.dispose();
  }

  private dibujar(lienzo: EstadoLienzo): void {
    if (!this.graph) {
      return;
    }

    this.graph.clearCells();

    for (const clase of Object.values(lienzo.clases)) {
      this.dibujarClase(clase);
    }

    for (const relacion of Object.values(lienzo.relaciones)) {
      this.dibujarRelacion(relacion);
    }

    if (Object.keys(lienzo.clases).length > 0) {
      this.graph.zoomToFit({ padding: 24, maxScale: 1 });
    }
  }

  private dibujarClase(clase: Clase): void {
    if (!this.graph) {
      return;
    }

    const ancho = clase.ui.ancho || 200;
    const altoLinea = 15;

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

    const altoTitulo = 26;
    const altoAtributos = Math.max(altoLinea, atributos.length * altoLinea + 8);
    const altoMetodos = Math.max(altoLinea, metodos.length * altoLinea + 8);
    const yAtributos = altoTitulo;
    const yMetodos = altoTitulo + altoAtributos;
    const alto = altoTitulo + altoAtributos + altoMetodos;

    this.graph.addNode({
      id: clase.id,
      x: clase.ui.x,
      y: clase.ui.y,
      width: ancho,
      height: alto,
      markup: [
        { tagName: 'rect', selector: 'body' },
        { tagName: 'text', selector: 'titulo' },
        { tagName: 'line', selector: 'divisor1' },
        { tagName: 'text', selector: 'atributos' },
        { tagName: 'line', selector: 'divisor2' },
        { tagName: 'text', selector: 'metodos' },
      ],
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
          refX: '50%',
          refY: altoTitulo / 2,
        },
        divisor1: { x1: 0, y1: altoTitulo, x2: ancho, y2: altoTitulo, stroke: '#555', strokeWidth: 1 },
        atributos: {
          text: atributos.join('\n') || ' ',
          fontSize: 10,
          fill: '#444',
          textAnchor: 'start',
          refX: 8,
          refY: yAtributos + 10,
        },
        divisor2: { x1: 0, y1: yMetodos, x2: ancho, y2: yMetodos, stroke: '#555', strokeWidth: 1 },
        metodos: {
          text: metodos.join('\n') || ' ',
          fontSize: 10,
          fill: '#444',
          textAnchor: 'start',
          refX: 8,
          refY: yMetodos + 10,
        },
      },
    });
  }

  private dibujarRelacion(relacion: Relacion): void {
    if (!this.graph) {
      return;
    }

    const config = CONFIG_POR_TIPO[relacion.tipo] ?? {};

    const labels: object[] = [];
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

    this.graph.addEdge({
      id: relacion.id,
      source: relacion.origen_id,
      target: relacion.destino_id,
      attrs: {
        line: {
          stroke: '#555',
          strokeWidth: 1.5,
          strokeDasharray: config.punteada ? '5 3' : undefined,
          sourceMarker: config.origen ?? null,
          targetMarker: config.destino ?? null,
        },
      },
      labels,
    });

    if (relacion.clase_asociada_id) {
      this.graph.addEdge({
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
      });
    }
  }
}
