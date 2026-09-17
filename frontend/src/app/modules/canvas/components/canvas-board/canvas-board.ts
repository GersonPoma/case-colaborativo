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
  signal,
  viewChild,
} from '@angular/core';
import { Graph } from '@antv/x6';
import { EstadoLienzo, TipoRelacion } from '../../../../core/models/lienzo.model';
import { sincronizarClases, sincronizarRelaciones } from '../../../../shared/utils/x6-uml.util';
import { CursorRemoto } from '../../services/canvas.service';

export type ModoCanvas = 'seleccionar' | 'crear-clase' | TipoRelacion | 'clase-asociada';

const COLOR_SELECCION = '#1976d2';
const COLORES_CURSOR = ['#e53935', '#8e24aa', '#3949ab', '#00897b', '#f4511e', '#6d4c41'];

interface CursorPosicionado {
  usuarioId: number;
  username: string;
  left: number;
  top: number;
  color: string;
}

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
  readonly cursores = input<Map<number, CursorRemoto>>(new Map());

  readonly claseSeleccionada = output<string | null>();
  readonly relacionSeleccionada = output<string | null>();
  readonly claseMovida = output<{ claseId: string; x: number; y: number }>();
  readonly relacionPropuesta = output<{ origenId: string; destinoId: string }>();
  readonly crearClaseSolicitada = output<{ x: number; y: number }>();
  readonly cursorMovido = output<{ x: number; y: number }>();

  readonly posicionesCursores = signal<CursorPosicionado[]>([]);

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

    effect(() => {
      this.cursores();
      this.recalcularPosicionesCursores();
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
    this.graph.on('translate', () => this.recalcularPosicionesCursores());
    this.graph.on('scale', () => this.recalcularPosicionesCursores());

    elemento.addEventListener('mousemove', (e: MouseEvent) => {
      if (!this.graph) {
        return;
      }
      const punto = this.graph.clientToLocal(e.clientX, e.clientY);
      this.cursorMovido.emit({ x: Math.round(punto.x), y: Math.round(punto.y) });
    });

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
        this.recalcularPosicionesCursores();
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

  /** Exporta el contenido del lienzo (clases + relaciones) como PNG, recortado a su
   * contenido real (sin el fondo punteado ni el area en blanco alrededor). */
  exportarPNG(): Promise<Blob | null> {
    if (!this.graph) {
      return Promise.resolve(null);
    }
    const bbox = this.graph.getContentBBox();
    if (bbox.width === 0 || bbox.height === 0) {
      return Promise.resolve(null);
    }

    const padding = 20;
    const escala = 2; // exporta a 2x para que se vea nitido en pantallas de alta densidad
    const ancho = Math.ceil(bbox.width + padding * 2);
    const alto = Math.ceil(bbox.height + padding * 2);

    const svgOriginal = this.contenedor().nativeElement.querySelector('svg.x6-graph-svg');
    if (!svgOriginal) {
      return Promise.resolve(null);
    }

    const svgClon = svgOriginal.cloneNode(true) as SVGSVGElement;
    svgClon.setAttribute('width', String(ancho));
    svgClon.setAttribute('height', String(alto));
    svgClon.setAttribute('viewBox', `${bbox.x - padding} ${bbox.y - padding} ${ancho} ${alto}`);
    // el grupo raiz trae el pan/zoom actual del lienzo interactivo: se quita porque
    // el viewBox de arriba ya encuadra el contenido en sus propias coordenadas
    svgClon.querySelector('.x6-graph-svg-viewport')?.removeAttribute('transform');

    const svgTexto = new XMLSerializer().serializeToString(svgClon);
    const svgUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgTexto)}`;

    return new Promise((resolve) => {
      const imagen = new Image();
      imagen.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = ancho * escala;
        canvas.height = alto * escala;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          resolve(null);
          return;
        }
        ctx.scale(escala, escala);
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, ancho, alto);
        ctx.drawImage(imagen, 0, 0, ancho, alto);
        canvas.toBlob((blob) => resolve(blob), 'image/png');
      };
      imagen.onerror = () => resolve(null);
      imagen.src = svgUrl;
    });
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

  private recalcularPosicionesCursores(): void {
    if (!this.graph) {
      return;
    }
    const contRect = this.hostRef.nativeElement.getBoundingClientRect();
    const posiciones = Array.from(this.cursores().values()).map((cursor) => {
      const punto = this.graph!.localToClient(cursor.x, cursor.y);
      return {
        usuarioId: cursor.usuarioId,
        username: cursor.username,
        left: punto.x - contRect.left,
        top: punto.y - contRect.top,
        color: COLORES_CURSOR[cursor.usuarioId % COLORES_CURSOR.length],
      };
    });
    this.posicionesCursores.set(posiciones);
  }
}
