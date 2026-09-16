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
import { dibujarLienzoCompleto } from '../../utils/x6-uml.util';

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
      width: elemento.clientWidth || 800,
      height: elemento.clientHeight || 560,
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

    dibujarLienzoCompleto(this.graph, lienzo.clases, lienzo.relaciones, false);

    if (Object.keys(lienzo.clases).length > 0) {
      this.graph.zoomToFit({ padding: 24, maxScale: 1 });
    }
  }
}
