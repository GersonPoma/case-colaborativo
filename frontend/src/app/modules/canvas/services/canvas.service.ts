import { isPlatformBrowser } from '@angular/common';
import { Injectable, OnDestroy, PLATFORM_ID, inject, signal } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../../core/services/auth.service';
import {
  Atributo,
  Clase,
  EstadoLienzo,
  Metodo,
  ParametroMetodo,
  Relacion,
  TipoRelacion,
  Visibilidad,
} from '../../../core/models/lienzo.model';
import { MensajeChat } from '../../workspace/models/proyecto.model';

export type AccionCanvas =
  | 'CREAR_CLASE'
  | 'EDITAR_CLASE'
  | 'ELIMINAR_CLASE'
  | 'AGREGAR_ATRIBUTO'
  | 'EDITAR_ATRIBUTO'
  | 'ELIMINAR_ATRIBUTO'
  | 'AGREGAR_METODO'
  | 'EDITAR_METODO'
  | 'ELIMINAR_METODO'
  | 'TRAZAR_RELACION'
  | 'EDITAR_RELACION'
  | 'ELIMINAR_RELACION'
  | 'MODIFICAR_UI'
  | 'ALINEAR_NODOS'
  | 'REEMPLAZAR_LIENZO';

interface DatosAtributo {
  nombre: string;
  tipo: string | null;
  es_pk: boolean;
  visibilidad: Visibilidad;
}

interface DatosMetodo {
  nombre: string;
  tipo_retorno: string | null;
  parametros: ParametroMetodo[];
  visibilidad: Visibilidad;
}

interface DatosRelacion {
  tipo: TipoRelacion;
  cardinalidad_origen: string | null;
  cardinalidad_destino: string | null;
  etiqueta: string | null;
  clase_asociada_id: string | null;
}

interface OpcionesEnvio {
  registrarDeshacer?: boolean;
}

interface ConfirmacionPendiente {
  accion: AccionCanvas;
  resolver: (datos: any) => void;
}

export interface CursorRemoto {
  usuarioId: number;
  username: string;
  x: number;
  y: number;
}

@Injectable()
export class CanvasService implements OnDestroy {
  private readonly authService = inject(AuthService);
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));

  private socket: WebSocket | null = null;
  // pila de deshacer local a esta pestaña/usuario: nunca contiene acciones de otros colaboradores
  private readonly pilaDeshacer: Array<() => void> = [];
  private readonly colaConfirmacion: ConfirmacionPendiente[] = [];

  readonly lienzo = signal<EstadoLienzo | null>(null);
  readonly conectado = signal(false);
  readonly error = signal<string | null>(null);
  readonly puedeDeshacer = signal(false);
  readonly ultimoMensajeChat = signal<MensajeChat | null>(null);
  readonly cursores = signal<Map<number, CursorRemoto>>(new Map());

  private ultimoEnvioCursor = 0;

  inicializar(estado: EstadoLienzo): void {
    this.lienzo.set(estado);
  }

  moverCursor(x: number, y: number): void {
    const ahora = Date.now();
    if (ahora - this.ultimoEnvioCursor < 60) {
      return;
    }
    this.ultimoEnvioCursor = ahora;
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ tipo: 'CURSOR', x, y }));
    }
  }

  deshacer(): void {
    const inversa = this.pilaDeshacer.pop();
    this.puedeDeshacer.set(this.pilaDeshacer.length > 0);
    inversa?.();
  }

  conectar(proyectoId: number): void {
    if (!this.isBrowser || this.socket) {
      return;
    }

    const token = this.authService.token();
    const url = `${environment.wsUrl}/proyectos/${proyectoId}?token=${token ?? ''}`;
    const socket = new WebSocket(url);

    socket.onopen = () => this.conectado.set(true);
    socket.onclose = () => this.conectado.set(false);
    socket.onerror = () => this.error.set('Se perdió la conexión en tiempo real');
    socket.onmessage = (evento) => this.procesarMensaje(JSON.parse(evento.data));

    this.socket = socket;
  }

  ngOnDestroy(): void {
    this.socket?.close();
    this.socket = null;
  }

  limpiarError(): void {
    this.error.set(null);
  }

  crearClase(nombre: string, x: number, y: number, alConfirmar?: (clase: Clase) => void): void {
    this.enviar('CREAR_CLASE', { nombre, x, y });
    this.esperarConfirmacion('CREAR_CLASE', (clase: Clase) => {
      this.apilarDeshacer(() => this.eliminarClase(clase.id));
      alConfirmar?.(clase);
    });
  }

  editarClase(claseId: string, nombre: string, opciones: OpcionesEnvio = {}): void {
    if (opciones.registrarDeshacer ?? true) {
      const anterior = this.lienzo()?.clases[claseId]?.nombre;
      if (anterior !== undefined) {
        this.apilarDeshacer(() => this.editarClase(claseId, anterior, { registrarDeshacer: false }));
      }
    }
    this.enviar('EDITAR_CLASE', { clase_id: claseId, nombre });
  }

  eliminarClase(claseId: string): void {
    this.enviar('ELIMINAR_CLASE', { clase_id: claseId });
  }

  agregarAtributo(claseId: string, datos: DatosAtributo): void {
    this.enviar('AGREGAR_ATRIBUTO', { clase_id: claseId, ...datos });
    this.esperarConfirmacion('AGREGAR_ATRIBUTO', (resultado: { clase_id: string; atributo: Atributo }) => {
      this.apilarDeshacer(() => this.eliminarAtributo(resultado.clase_id, resultado.atributo.id));
    });
  }

  editarAtributo(
    claseId: string,
    atributoId: string,
    datos: DatosAtributo,
    opciones: OpcionesEnvio = {},
  ): void {
    if (opciones.registrarDeshacer ?? true) {
      const anterior = this.lienzo()?.clases[claseId]?.atributos[atributoId];
      if (anterior) {
        this.apilarDeshacer(() =>
          this.editarAtributo(
            claseId,
            atributoId,
            {
              nombre: anterior.nombre,
              tipo: anterior.tipo,
              es_pk: anterior.es_pk,
              visibilidad: anterior.visibilidad,
            },
            { registrarDeshacer: false },
          ),
        );
      }
    }
    this.enviar('EDITAR_ATRIBUTO', { clase_id: claseId, atributo_id: atributoId, ...datos });
  }

  eliminarAtributo(claseId: string, atributoId: string): void {
    this.enviar('ELIMINAR_ATRIBUTO', { clase_id: claseId, atributo_id: atributoId });
  }

  agregarMetodo(claseId: string, datos: DatosMetodo): void {
    this.enviar('AGREGAR_METODO', { clase_id: claseId, ...datos });
    this.esperarConfirmacion('AGREGAR_METODO', (resultado: { clase_id: string; metodo: Metodo }) => {
      this.apilarDeshacer(() => this.eliminarMetodo(resultado.clase_id, resultado.metodo.id));
    });
  }

  editarMetodo(
    claseId: string,
    metodoId: string,
    datos: DatosMetodo,
    opciones: OpcionesEnvio = {},
  ): void {
    if (opciones.registrarDeshacer ?? true) {
      const anterior = this.lienzo()?.clases[claseId]?.metodos[metodoId];
      if (anterior) {
        this.apilarDeshacer(() =>
          this.editarMetodo(
            claseId,
            metodoId,
            {
              nombre: anterior.nombre,
              tipo_retorno: anterior.tipo_retorno,
              parametros: anterior.parametros,
              visibilidad: anterior.visibilidad,
            },
            { registrarDeshacer: false },
          ),
        );
      }
    }
    this.enviar('EDITAR_METODO', { clase_id: claseId, metodo_id: metodoId, ...datos });
  }

  eliminarMetodo(claseId: string, metodoId: string): void {
    this.enviar('ELIMINAR_METODO', { clase_id: claseId, metodo_id: metodoId });
  }

  trazarRelacion(origenId: string, destinoId: string, datos: DatosRelacion): void {
    this.enviar('TRAZAR_RELACION', { origen_id: origenId, destino_id: destinoId, ...datos });
    this.esperarConfirmacion('TRAZAR_RELACION', (relacion: Relacion) => {
      this.apilarDeshacer(() => this.eliminarRelacion(relacion.id));
    });
  }

  editarRelacion(relacionId: string, datos: DatosRelacion, opciones: OpcionesEnvio = {}): void {
    if (opciones.registrarDeshacer ?? true) {
      const anterior = this.lienzo()?.relaciones[relacionId];
      if (anterior) {
        this.apilarDeshacer(() =>
          this.editarRelacion(
            relacionId,
            {
              tipo: anterior.tipo,
              cardinalidad_origen: anterior.cardinalidad_origen,
              cardinalidad_destino: anterior.cardinalidad_destino,
              etiqueta: anterior.etiqueta,
              clase_asociada_id: anterior.clase_asociada_id,
            },
            { registrarDeshacer: false },
          ),
        );
      }
    }
    this.enviar('EDITAR_RELACION', { relacion_id: relacionId, ...datos });
  }

  eliminarRelacion(relacionId: string): void {
    this.enviar('ELIMINAR_RELACION', { relacion_id: relacionId });
  }

  modificarUi(
    claseId: string,
    datos: { x?: number; y?: number; ancho?: number; color?: string },
    opciones: OpcionesEnvio = {},
  ): void {
    if (opciones.registrarDeshacer ?? true) {
      const anterior = this.lienzo()?.clases[claseId]?.ui;
      if (anterior) {
        const inversos: typeof datos = {};
        if (datos.x !== undefined) inversos.x = anterior.x;
        if (datos.y !== undefined) inversos.y = anterior.y;
        if (datos.ancho !== undefined) inversos.ancho = anterior.ancho;
        if (datos.color !== undefined) inversos.color = anterior.color;
        this.apilarDeshacer(() => this.modificarUi(claseId, inversos, { registrarDeshacer: false }));
      }
    }
    this.enviar('MODIFICAR_UI', { clase_id: claseId, ...datos });
  }

  alinearNodos(
    posiciones: { clase_id: string; x: number; y: number }[],
    opciones: OpcionesEnvio = {},
  ): void {
    if (opciones.registrarDeshacer ?? true) {
      const estado = this.lienzo();
      const anteriores = estado
        ? posiciones
            .map((p) => {
              const clase = estado.clases[p.clase_id];
              return clase ? { clase_id: p.clase_id, x: clase.ui.x, y: clase.ui.y } : null;
            })
            .filter((p): p is { clase_id: string; x: number; y: number } => p !== null)
        : [];
      if (anteriores.length > 0) {
        this.apilarDeshacer(() => this.alinearNodos(anteriores, { registrarDeshacer: false }));
      }
    }
    this.enviar('ALINEAR_NODOS', { posiciones });
  }

  /** Reemplaza por completo clases y relaciones (usado al importar un XMI). */
  reemplazarLienzo(
    clases: Record<string, Clase>,
    relaciones: Record<string, Relacion>,
    opciones: OpcionesEnvio = {},
  ): void {
    if (opciones.registrarDeshacer ?? true) {
      const anterior = this.lienzo();
      if (anterior) {
        this.apilarDeshacer(() =>
          this.reemplazarLienzo(anterior.clases, anterior.relaciones, { registrarDeshacer: false }),
        );
      }
    }
    this.enviar('REEMPLAZAR_LIENZO', { clases, relaciones });
  }

  private enviar(accion: AccionCanvas, datos: object): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      this.error.set('Todavía no hay conexión en tiempo real con el proyecto');
      return;
    }
    this.socket.send(JSON.stringify({ accion, datos }));
  }

  private apilarDeshacer(inversa: () => void): void {
    this.pilaDeshacer.push(inversa);
    this.puedeDeshacer.set(true);
  }

  /** Registra qué hacer cuando llegue la confirmación (con el id generado por el servidor) de esta acción propia. */
  private esperarConfirmacion(accion: AccionCanvas, resolver: (datos: any) => void): void {
    this.colaConfirmacion.push({ accion, resolver });
  }

  private resolverConfirmacionPropia(accion: AccionCanvas, usuarioId: number | undefined, datos: any): void {
    if (usuarioId === undefined || usuarioId !== this.authService.usuario()?.id) {
      return;
    }
    const indice = this.colaConfirmacion.findIndex((p) => p.accion === accion);
    if (indice === -1) {
      return;
    }
    const [pendiente] = this.colaConfirmacion.splice(indice, 1);
    pendiente.resolver(datos);
  }

  private procesarMensaje(mensaje: {
    tipo?: string;
    mensaje?: MensajeChat;
    accion?: AccionCanvas;
    datos?: any;
    usuario_id?: number;
    username?: string;
    x?: number;
    y?: number;
    error?: string;
  }): void {
    if (mensaje.error) {
      this.error.set(mensaje.error);
      return;
    }
    if (mensaje.tipo === 'MENSAJE_CHAT' && mensaje.mensaje) {
      this.ultimoMensajeChat.set(mensaje.mensaje);
      return;
    }
    if (
      mensaje.tipo === 'CURSOR' &&
      mensaje.usuario_id !== undefined &&
      mensaje.username &&
      mensaje.x !== undefined &&
      mensaje.y !== undefined
    ) {
      const mapa = new Map(this.cursores());
      mapa.set(mensaje.usuario_id, {
        usuarioId: mensaje.usuario_id,
        username: mensaje.username,
        x: mensaje.x,
        y: mensaje.y,
      });
      this.cursores.set(mapa);
      return;
    }
    if (mensaje.tipo === 'CURSOR_SALIO' && mensaje.usuario_id !== undefined) {
      const mapa = new Map(this.cursores());
      mapa.delete(mensaje.usuario_id);
      this.cursores.set(mapa);
      return;
    }
    if (mensaje.accion) {
      this.aplicar(mensaje.accion, mensaje.datos);
      this.resolverConfirmacionPropia(mensaje.accion, mensaje.usuario_id, mensaje.datos);
    }
  }

  private aplicar(accion: AccionCanvas, datos: any): void {
    const estado = this.lienzo();
    if (!estado) {
      return;
    }

    switch (accion) {
      case 'CREAR_CLASE':
      case 'EDITAR_CLASE': {
        const clase: Clase = datos;
        this.lienzo.set({ ...estado, clases: { ...estado.clases, [clase.id]: clase } });
        break;
      }
      case 'ELIMINAR_CLASE': {
        const clases = { ...estado.clases };
        delete clases[datos.clase_id];
        const relaciones = Object.fromEntries(
          Object.entries(estado.relaciones).filter(
            ([, r]) =>
              r.origen_id !== datos.clase_id &&
              r.destino_id !== datos.clase_id &&
              r.clase_asociada_id !== datos.clase_id,
          ),
        );
        this.lienzo.set({ ...estado, clases, relaciones });
        break;
      }
      case 'AGREGAR_ATRIBUTO':
      case 'EDITAR_ATRIBUTO': {
        const clase = estado.clases[datos.clase_id];
        if (!clase) break;
        const atributo: Atributo = datos.atributo;
        const claseActualizada: Clase = {
          ...clase,
          atributos: { ...clase.atributos, [atributo.id]: atributo },
        };
        this.lienzo.set({ ...estado, clases: { ...estado.clases, [clase.id]: claseActualizada } });
        break;
      }
      case 'ELIMINAR_ATRIBUTO': {
        const clase = estado.clases[datos.clase_id];
        if (!clase) break;
        const atributos = { ...clase.atributos };
        delete atributos[datos.atributo_id];
        const claseActualizada: Clase = { ...clase, atributos };
        this.lienzo.set({ ...estado, clases: { ...estado.clases, [clase.id]: claseActualizada } });
        break;
      }
      case 'AGREGAR_METODO':
      case 'EDITAR_METODO': {
        const clase = estado.clases[datos.clase_id];
        if (!clase) break;
        const metodo: Metodo = datos.metodo;
        const claseActualizada: Clase = {
          ...clase,
          metodos: { ...clase.metodos, [metodo.id]: metodo },
        };
        this.lienzo.set({ ...estado, clases: { ...estado.clases, [clase.id]: claseActualizada } });
        break;
      }
      case 'ELIMINAR_METODO': {
        const clase = estado.clases[datos.clase_id];
        if (!clase) break;
        const metodos = { ...clase.metodos };
        delete metodos[datos.metodo_id];
        const claseActualizada: Clase = { ...clase, metodos };
        this.lienzo.set({ ...estado, clases: { ...estado.clases, [clase.id]: claseActualizada } });
        break;
      }
      case 'TRAZAR_RELACION':
      case 'EDITAR_RELACION': {
        const relacion: Relacion = datos;
        this.lienzo.set({ ...estado, relaciones: { ...estado.relaciones, [relacion.id]: relacion } });
        break;
      }
      case 'ELIMINAR_RELACION': {
        const relaciones = { ...estado.relaciones };
        delete relaciones[datos.relacion_id];

        let clases = estado.clases;
        const claseAsociadaId: string | undefined = datos.clase_asociada_id;
        if (claseAsociadaId) {
          clases = { ...clases };
          delete clases[claseAsociadaId];
          for (const [rid, r] of Object.entries(relaciones)) {
            if (
              r.origen_id === claseAsociadaId ||
              r.destino_id === claseAsociadaId ||
              r.clase_asociada_id === claseAsociadaId
            ) {
              delete relaciones[rid];
            }
          }
        }

        this.lienzo.set({ ...estado, clases, relaciones });
        break;
      }
      case 'MODIFICAR_UI': {
        const clase = estado.clases[datos.clase_id];
        if (!clase) break;
        const claseActualizada: Clase = { ...clase, ui: datos.ui };
        this.lienzo.set({ ...estado, clases: { ...estado.clases, [clase.id]: claseActualizada } });
        break;
      }
      case 'ALINEAR_NODOS': {
        const clases = { ...estado.clases };
        for (const pos of datos.posiciones) {
          const clase = clases[pos.clase_id];
          if (clase) {
            clases[pos.clase_id] = { ...clase, ui: { ...clase.ui, x: pos.x, y: pos.y } };
          }
        }
        this.lienzo.set({ ...estado, clases });
        break;
      }
      case 'REEMPLAZAR_LIENZO': {
        const nuevoEstado: EstadoLienzo = datos;
        this.lienzo.set(nuevoEstado);
        break;
      }
    }
  }
}
