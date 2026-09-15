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
  output,
  viewChild,
} from '@angular/core';
import { Graph } from '@antv/x6';
import { EstadoLienzo, TipoRelacion } from '../../../../core/models/lienzo.model';
import { sincronizarClases, sincronizarRelaciones } from '../../../../shared/utils/x6-uml.util';

export type ModoCanvas = 'seleccionar' | 'crear-clase' | TipoRelacion | 'clase-asociada';

const COLOR_SELECCION = '#1976d2';

@Component({
  selector: 'app-canvas-board',
  imports: [],
  templateUrl: './canvas-board.html',
  styleUrl: './canvas-board.scss',
})
export class CanvasBoard implements AfterViewInit, OnDestroy {
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));
  private readonly hostRef = inject(ElementRef<HTMLElement>);
  private readonly contenedor = viewChild.required<ElementRef<HTMLDivElement>>('contenedor');

  readonly lienzo = input<EstadoLienzo | null>(null);
  readonly soloLectura = input(false);
  readonly modo = input<ModoCanvas>('seleccionar');

  readonly claseSeleccionada = output<string | null>();
  readonly relacionSeleccionada = output<string | null>();
  readonly claseMovida = output<{ claseId: string; x: number; y: number }>();
  readonly relacionPropuesta = output<{ origenId: string; destinoId: string }>();
  readonly crearClaseSolicitada = output<{ x: number; y: number }>();

  private graph: Graph | null = null;
  private claseSeleccionadaId: string | null = null;
  private relacionSeleccionadaId: string | null = null;
  private origenRelacion: string | null = null;
  private readonly huellasRelaciones = new Map<string, string>();
  private observadorTamano: ResizeObserver | null = null;

  constructor() {
    effect(() => {
      const lienzo = this.lienzo();
      if (this.graph && lienzo) {
        this.dibujar(lienzo);
      }
    });

    effect(() => {
      this.modo();
      this.cancelarSeleccionRelacion();
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
      height: elemento.clientHeight || 600,
      panning: true,
      mousewheel: true,
      interacting: () => !this.soloLectura(),
    });

    this.graph.on('node:click', ({ node }) => this.alClickNodo(node.id));
    this.graph.on('node:moved', ({ node }) => {
      const { x, y } = node.position();
      this.claseMovida.emit({ claseId: node.id, x: Math.round(x), y: Math.round(y) });
    });
    this.graph.on('edge:click', ({ edge }) => this.alClickEdge(edge.id));
    this.graph.on('blank:click', ({ x, y }) => this.alClickVacio(x, y));

    // el layout flex del editor cambia el ancho disponible cuando se abre o
    // cierra el panel lateral. OJO: hay que observar el HOST del componente
    // (el que participa del flex), no "elemento" (#contenedor) — a ese X6 le
    // escribe un width/height fijos por style inline al crear el Graph, así
    // que nunca "cambia de tamaño" por sí solo y el ResizeObserver nunca
    // dispararía si lo observáramos a él.
    this.observadorTamano = new ResizeObserver((entradas) => {
      const entrada = entradas[0];
      if (entrada && this.graph) {
        const { width, height } = entrada.contentRect;
        this.graph.resize(width, height);
      }
    });
    this.observadorTamano.observe(this.hostRef.nativeElement);

    const lienzo = this.lienzo();
    if (lienzo) {
      this.dibujar(lienzo);
    }
  }

  ngOnDestroy(): void {
    this.observadorTamano?.disconnect();
    this.graph?.dispose();
  }

  centrar(): void {
    if (this.graph && Object.keys(this.lienzo()?.clases ?? {}).length > 0) {
      this.graph.zoomToFit({ padding: 24, maxScale: 1 });
    }
  }

  private dibujar(lienzo: EstadoLienzo): void {
    if (!this.graph) {
      return;
    }

    const interactivo = !this.soloLectura();
    sincronizarClases(this.graph, lienzo.clases, interactivo);
    sincronizarRelaciones(this.graph, lienzo.relaciones, interactivo, this.huellasRelaciones);

    this.reaplicarSeleccion();
  }

  private alClickNodo(claseId: string): void {
    if (this.esModoRelacion() && !this.soloLectura()) {
      if (!this.origenRelacion) {
        this.origenRelacion = claseId;
        this.resaltarNodo(claseId, true);
      } else if (this.origenRelacion !== claseId) {
        const origenId = this.origenRelacion;
        this.resaltarNodo(origenId, false);
        this.origenRelacion = null;
        this.relacionPropuesta.emit({ origenId, destinoId: claseId });
      }
      return;
    }

    this.deseleccionarRelacion();
    if (this.claseSeleccionadaId === claseId) {
      return;
    }
    this.resaltarNodo(this.claseSeleccionadaId, false);
    this.claseSeleccionadaId = claseId;
    this.resaltarNodo(claseId, true);
    this.claseSeleccionada.emit(claseId);
  }

  private alClickEdge(edgeId: string): void {
    const estado = this.lienzo();
    if (!estado || !estado.relaciones[edgeId]) {
      return;
    }
    this.deseleccionarClase();
    this.relacionSeleccionadaId = edgeId;
    this.relacionSeleccionada.emit(edgeId);
  }

  private alClickVacio(x: number, y: number): void {
    if (this.modo() === 'crear-clase' && !this.soloLectura()) {
      this.crearClaseSolicitada.emit({ x: Math.round(x), y: Math.round(y) });
      return;
    }
    if (this.origenRelacion) {
      this.cancelarSeleccionRelacion();
      return;
    }
    this.deseleccionarClase();
    this.deseleccionarRelacion();
  }

  private esModoRelacion(): boolean {
    return this.modo() !== 'seleccionar' && this.modo() !== 'crear-clase';
  }

  private deseleccionarClase(): void {
    if (this.claseSeleccionadaId) {
      this.resaltarNodo(this.claseSeleccionadaId, false);
      this.claseSeleccionadaId = null;
      this.claseSeleccionada.emit(null);
    }
  }

  private deseleccionarRelacion(): void {
    if (this.relacionSeleccionadaId) {
      this.relacionSeleccionadaId = null;
      this.relacionSeleccionada.emit(null);
    }
  }

  private cancelarSeleccionRelacion(): void {
    if (this.origenRelacion) {
      this.resaltarNodo(this.origenRelacion, false);
      this.origenRelacion = null;
    }
  }

  private resaltarNodo(claseId: string | null, activo: boolean): void {
    if (!claseId || !this.graph) {
      return;
    }
    const nodo = this.graph.getCellById(claseId);
    nodo?.attr('body/stroke', activo ? COLOR_SELECCION : '#555');
    nodo?.attr('body/strokeWidth', activo ? 2 : 1);
  }

  private reaplicarSeleccion(): void {
    if (this.claseSeleccionadaId) {
      this.resaltarNodo(this.claseSeleccionadaId, true);
    }
    if (this.origenRelacion) {
      this.resaltarNodo(this.origenRelacion, true);
    }
  }
}
