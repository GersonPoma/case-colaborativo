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
import { EstadoLienzo } from '../../../core/models/lienzo.model';

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
      const atributos = Object.values(clase.atributos)
        .sort((a, b) => a.orden - b.orden)
        .map((a) => `${a.visibilidad === 'PUBLICO' ? '+' : '-'} ${a.nombre}: ${a.tipo}`);

      const alto = Math.max(44, 26 + atributos.length * 15);

      this.graph.addNode({
        id: clase.id,
        x: clase.ui.x,
        y: clase.ui.y,
        width: clase.ui.ancho || 180,
        height: alto,
        markup: [
          { tagName: 'rect', selector: 'body' },
          { tagName: 'text', selector: 'titulo' },
          { tagName: 'text', selector: 'atributos' },
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
            refY: 14,
          },
          atributos: {
            text: atributos.join('\n'),
            fontSize: 10,
            fill: '#444',
            textAnchor: 'start',
            refX: 8,
            refY: 28,
          },
        },
      });
    }

    for (const relacion of Object.values(lienzo.relaciones)) {
      this.graph.addEdge({
        id: relacion.id,
        source: relacion.origen_id,
        target: relacion.destino_id,
        attrs: {
          line: {
            stroke: '#666',
            strokeWidth: 1.5,
            targetMarker: { name: 'classic', size: 6 },
          },
        },
        labels: relacion.tipo
          ? [{ attrs: { text: { text: relacion.tipo, fontSize: 9, fill: '#666' } } }]
          : [],
      });
    }

    if (Object.keys(lienzo.clases).length > 0) {
      this.graph.zoomToFit({ padding: 24, maxScale: 1 });
    }
  }
}
