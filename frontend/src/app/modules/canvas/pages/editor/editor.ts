import { HttpResponse } from '@angular/common/http';
import {
  Component,
  HostListener,
  WritableSignal,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Observable, forkJoin } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';
import { Clase, TipoRelacion } from '../../../../core/models/lienzo.model';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { Modal } from '../../../../shared/components/modal/modal';
import { ConfiguracionTranspilacion } from '../../../interoperability/models/interoperability.model';
import { InteroperabilidadApiService } from '../../../interoperability/services/interoperability-api.service';
import { Colaborador, Proyecto, RolColaborador } from '../../../workspace/models/proyecto.model';
import { WorkspaceApiService } from '../../../workspace/services/workspace-api.service';
import { CanvasBoard, ModoCanvas } from '../../components/canvas-board/canvas-board';
import { ClassPanel } from '../../components/class-panel/class-panel';
import { CollaborationPanel } from '../../components/collaboration-panel/collaboration-panel';
import { RelationForm } from '../../components/relation-form/relation-form';
import { Toolbar } from '../../components/toolbar/toolbar';
import { Toolbox } from '../../components/toolbox/toolbox';
import { CanvasApiService } from '../../services/canvas-api.service';
import { CanvasService } from '../../services/canvas.service';

const TIPOS_RELACION = new Set<string>([
  'ASOCIACION',
  'AGREGACION',
  'COMPOSICION',
  'HERENCIA',
  'REALIZACION',
  'TEMPLATE_BINDING',
]);

function esTipoRelacion(modo: ModoCanvas): modo is TipoRelacion {
  return TIPOS_RELACION.has(modo);
}

@Component({
  selector: 'app-editor',
  imports: [Toolbar, Toolbox, CanvasBoard, ClassPanel, RelationForm, CollaborationPanel, Modal],
  templateUrl: './editor.html',
  styleUrl: './editor.scss',
  providers: [CanvasService],
})
export class Editor {
  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly workspaceApi = inject(WorkspaceApiService);
  private readonly canvasApi = inject(CanvasApiService);
  private readonly interoperabilidadApi = inject(InteroperabilidadApiService);
  protected readonly canvasService = inject(CanvasService);

  private readonly board = viewChild<CanvasBoard>(CanvasBoard);

  readonly proyectoId = Number(this.route.snapshot.paramMap.get('id'));

  readonly proyecto = signal<Proyecto | null>(null);
  readonly miRol = signal<RolColaborador | null>(null);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly guardandoVersion = signal(false);
  readonly exportandoXmi = signal(false);
  readonly exportandoXmiEa = signal(false);
  readonly exportandoImagen = signal(false);
  readonly importandoXmi = signal(false);
  readonly archivoXmiPendiente = signal<File | null>(null);
  readonly generandoBackend = signal(false);
  readonly mostrarModalBackend = signal(false);
  readonly cargandoConfigTranspilacion = signal(false);
  readonly configTranspilacion = signal<ConfiguracionTranspilacion | null>(null);

  readonly modo = signal<ModoCanvas>('seleccionar');
  readonly claseSeleccionadaId = signal<string | null>(null);
  readonly mostrarRelationForm = signal(false);
  readonly relacionEditandoId = signal<string | null>(null);
  readonly origenPendiente = signal<string | null>(null);
  readonly destinoPendiente = signal<string | null>(null);
  readonly tipoRelacionPropuesta = signal<TipoRelacion>('ASOCIACION');
  readonly portapapeles = signal<Clase | null>(null);
  private vecesPegado = 0;

  readonly esDueno = computed(() => {
    const usuario = this.authService.usuario();
    const proyecto = this.proyecto();
    return !!usuario && !!proyecto && usuario.id === proyecto.id_dueno;
  });
  readonly puedeEditar = computed(() => this.esDueno() || this.miRol() === 'EDITOR');

  readonly claseSeleccionada = computed(() => {
    const id = this.claseSeleccionadaId();
    const lienzo = this.canvasService.lienzo();
    return id && lienzo ? (lienzo.clases[id] ?? null) : null;
  });

  readonly relacionEditando = computed(() => {
    const id = this.relacionEditandoId();
    const lienzo = this.canvasService.lienzo();
    return id && lienzo ? (lienzo.relaciones[id] ?? null) : null;
  });

  constructor() {
    this.cargar();
  }

  @HostListener('document:keydown', ['$event'])
  alTeclado(evento: KeyboardEvent): void {
    const objetivo = evento.target as HTMLElement | null;
    const esCampoTexto = ['INPUT', 'TEXTAREA', 'SELECT'].includes(objetivo?.tagName ?? '');
    const esCtrlZ = (evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 'z' && !evento.shiftKey;
    const esCtrlC = (evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 'c';
    const esCtrlV = (evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 'v';

    if (esCtrlZ && !esCampoTexto && this.puedeEditar()) {
      evento.preventDefault();
      this.canvasService.deshacer();
      return;
    }

    if (esCtrlC && !esCampoTexto && this.claseSeleccionada()) {
      evento.preventDefault();
      this.copiarClaseSeleccionada();
      return;
    }

    if (esCtrlV && !esCampoTexto && this.puedeEditar() && this.portapapeles()) {
      evento.preventDefault();
      this.pegarClaseCopiada();
    }
  }

  private copiarClaseSeleccionada(): void {
    const clase = this.claseSeleccionada();
    if (!clase) {
      return;
    }
    this.portapapeles.set(clase);
    this.vecesPegado = 0;
  }

  private pegarClaseCopiada(): void {
    const copia = this.portapapeles();
    if (!copia) {
      return;
    }
    this.vecesPegado += 1;
    const x = copia.ui.x + 40 * this.vecesPegado;
    const y = copia.ui.y + 40 * this.vecesPegado;

    this.canvasService.crearClase(`${copia.nombre} (copia)`, x, y, (nuevaClase) => {
      const atributos = Object.values(copia.atributos).sort((a, b) => a.orden - b.orden);
      for (const atributo of atributos) {
        this.canvasService.agregarAtributo(nuevaClase.id, {
          nombre: atributo.nombre,
          tipo: atributo.tipo,
          es_pk: atributo.es_pk,
          visibilidad: atributo.visibilidad,
        });
      }

      const metodos = Object.values(copia.metodos).sort((a, b) => a.orden - b.orden);
      for (const metodo of metodos) {
        this.canvasService.agregarMetodo(nuevaClase.id, {
          nombre: metodo.nombre,
          tipo_retorno: metodo.tipo_retorno,
          parametros: metodo.parametros,
          visibilidad: metodo.visibilidad,
        });
      }

      this.claseSeleccionadaId.set(nuevaClase.id);
    });
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);

    forkJoin({
      proyecto: this.workspaceApi.obtener(this.proyectoId),
      colaboradores: this.workspaceApi.listarColaboradores(this.proyectoId, 1, 100),
      lienzo: this.canvasApi.obtenerLienzo(this.proyectoId),
    }).subscribe({
      next: ({ proyecto, colaboradores, lienzo }) => {
        this.proyecto.set(proyecto);
        const propio: Colaborador | undefined = colaboradores.items.find(
          (c) => c.usuario.id === this.authService.usuario()?.id,
        );
        this.miRol.set(propio?.rol ?? null);
        this.canvasService.inicializar(lienzo);
        this.canvasService.conectar(this.proyectoId);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  cambiarModo(modo: ModoCanvas): void {
    this.modo.set(modo);
    if (esTipoRelacion(modo)) {
      this.tipoRelacionPropuesta.set(modo);
    }
  }

  alCrearClaseEnPosicion(evento: { x: number; y: number }): void {
    this.canvasService.crearClase('NuevaClase', evento.x, evento.y, (clase) => {
      this.claseSeleccionadaId.set(clase.id);
    });
    this.modo.set('seleccionar');
  }

  alClaseSeleccionada(id: string | null): void {
    this.claseSeleccionadaId.set(id);
  }

  alRelacionSeleccionada(id: string | null): void {
    if (!id || !this.puedeEditar()) {
      return;
    }
    this.relacionEditandoId.set(id);
    this.origenPendiente.set(null);
    this.destinoPendiente.set(null);
    this.mostrarRelationForm.set(true);
  }

  alClaseMovida(evento: { claseId: string; x: number; y: number }): void {
    this.canvasService.modificarUi(evento.claseId, { x: evento.x, y: evento.y });
  }

  alRelacionPropuesta(evento: { origenId: string; destinoId: string }): void {
    if (this.modo() === 'clase-asociada') {
      this.crearRelacionConClaseAsociada(evento.origenId, evento.destinoId);
      this.modo.set('seleccionar');
      return;
    }

    this.relacionEditandoId.set(null);
    this.origenPendiente.set(evento.origenId);
    this.destinoPendiente.set(evento.destinoId);
    this.mostrarRelationForm.set(true);
    this.modo.set('seleccionar');
  }

  private crearRelacionConClaseAsociada(origenId: string, destinoId: string): void {
    const lienzo = this.canvasService.lienzo();
    const origen = lienzo?.clases[origenId];
    const destino = lienzo?.clases[destinoId];
    const x = origen && destino ? Math.round((origen.ui.x + destino.ui.x) / 2) : 200;
    const y = origen && destino ? Math.round((origen.ui.y + destino.ui.y) / 2) + 140 : 400;

    this.canvasService.crearClase('NuevaClase', x, y, (clase) => {
      this.canvasService.trazarRelacion(origenId, destinoId, {
        tipo: 'ASOCIACION',
        cardinalidad_origen: null,
        cardinalidad_destino: null,
        etiqueta: null,
        clase_asociada_id: clase.id,
      });
      this.claseSeleccionadaId.set(clase.id);
    });
  }

  cerrarRelationForm(): void {
    this.mostrarRelationForm.set(false);
    this.relacionEditandoId.set(null);
    this.origenPendiente.set(null);
    this.destinoPendiente.set(null);
  }

  alinear(): void {
    const clases = Object.values(this.canvasService.lienzo()?.clases ?? {});
    const posiciones = clases.map((clase, i) => ({
      clase_id: clase.id,
      x: 80 + (i % 4) * 260,
      y: 80 + Math.floor(i / 4) * 220,
    }));
    this.canvasService.alinearNodos(posiciones);
  }

  centrar(): void {
    this.board()?.centrar();
  }

  guardarVersion(): void {
    this.guardandoVersion.set(true);
    this.error.set(null);
    this.workspaceApi.crearVersionHistorial(this.proyectoId).subscribe({
      next: () => this.guardandoVersion.set(false),
      error: (err: unknown) => {
        this.guardandoVersion.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  exportarXmi(): void {
    this.descargarExportacion(
      this.interoperabilidadApi.exportarXmi(this.proyectoId),
      this.exportandoXmi,
      'diagrama.xmi',
    );
  }

  exportarXmiEa(): void {
    this.descargarExportacion(
      this.interoperabilidadApi.exportarXmiParaEa(this.proyectoId),
      this.exportandoXmiEa,
      'diagrama_ea.xmi',
    );
  }

  async exportarImagen(): Promise<void> {
    this.exportandoImagen.set(true);
    this.error.set(null);
    try {
      const blob = await this.board()?.exportarPNG();
      if (!blob) {
        this.error.set('No se pudo generar la imagen: el lienzo está vacío.');
        return;
      }
      const nombreArchivo = `${this.slug(this.proyecto()?.nombre ?? 'diagrama')}.png`;
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = nombreArchivo;
      enlace.click();
      URL.revokeObjectURL(url);
    } finally {
      this.exportandoImagen.set(false);
    }
  }

  alArchivoXmiSeleccionado(archivo: File): void {
    this.archivoXmiPendiente.set(archivo);
  }

  cancelarImportarXmi(): void {
    this.archivoXmiPendiente.set(null);
  }

  confirmarImportarXmi(): void {
    const archivo = this.archivoXmiPendiente();
    if (!archivo) {
      return;
    }
    this.importandoXmi.set(true);
    this.error.set(null);
    this.interoperabilidadApi.importarXmi(this.proyectoId, archivo).subscribe({
      next: (resultado) => {
        this.importandoXmi.set(false);
        this.archivoXmiPendiente.set(null);
        this.canvasService.reemplazarLienzo(resultado.clases, resultado.relaciones);
      },
      error: (err: unknown) => {
        this.importandoXmi.set(false);
        this.archivoXmiPendiente.set(null);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  abrirModalBackend(): void {
    this.mostrarModalBackend.set(true);
    this.cargandoConfigTranspilacion.set(true);
    this.error.set(null);
    this.interoperabilidadApi.obtenerConfiguracionTranspilacion(this.proyectoId).subscribe({
      next: (config) => {
        this.cargandoConfigTranspilacion.set(false);
        this.configTranspilacion.set(config);
      },
      error: (err: unknown) => {
        this.cargandoConfigTranspilacion.set(false);
        this.mostrarModalBackend.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  cerrarModalBackend(): void {
    this.mostrarModalBackend.set(false);
  }

  confirmarGenerarBackend(): void {
    this.mostrarModalBackend.set(false);
    this.descargarExportacion(
      this.interoperabilidadApi.generarBackend(this.proyectoId),
      this.generandoBackend,
      'backend.zip',
    );
  }

  private slug(texto: string): string {
    const normalizado = texto
      .toLowerCase()
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
    return normalizado || 'diagrama';
  }

  private descargarExportacion(
    peticion: Observable<HttpResponse<Blob>>,
    cargando: WritableSignal<boolean>,
    nombrePorDefecto: string,
  ): void {
    cargando.set(true);
    this.error.set(null);

    peticion.subscribe({
      next: (respuesta) => {
        cargando.set(false);
        const contenido = respuesta.body;
        if (!contenido) {
          return;
        }
        const nombreArchivo =
          this.extraerNombreArchivo(respuesta.headers.get('content-disposition')) ??
          nombrePorDefecto;
        const url = URL.createObjectURL(contenido);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = nombreArchivo;
        enlace.click();
        URL.revokeObjectURL(url);
      },
      error: (err: unknown) => {
        cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  private extraerNombreArchivo(encabezado: string | null): string | null {
    if (!encabezado) {
      return null;
    }
    const coincidencia = /filename="([^"]+)"/.exec(encabezado);
    return coincidencia ? coincidencia[1] : null;
  }
}
