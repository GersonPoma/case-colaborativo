import { DatePipe } from '@angular/common';
import {
  Component,
  ElementRef,
  OnInit,
  effect,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../../../core/services/auth.service';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { MensajeChat } from '../../../workspace/models/proyecto.model';
import { WorkspaceApiService } from '../../../workspace/services/workspace-api.service';
import { CanvasService } from '../../services/canvas.service';

const TAMANO_PAGINA = 30;
const UMBRAL_SCROLL_ARRIBA = 40;

@Component({
  selector: 'app-chat-panel',
  imports: [ReactiveFormsModule, DatePipe],
  templateUrl: './chat-panel.html',
  styleUrl: './chat-panel.scss',
})
export class ChatPanel implements OnInit {
  private readonly workspaceApi = inject(WorkspaceApiService);
  private readonly canvasService = inject(CanvasService);
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);

  private readonly lista = viewChild<ElementRef<HTMLDivElement>>('lista');

  readonly proyectoId = input.required<number>();

  readonly mensajes = signal<MensajeChat[]>([]);
  readonly cargando = signal(true);
  readonly cargandoMas = signal(false);
  readonly hayMas = signal(false);
  readonly error = signal<string | null>(null);
  readonly enviando = signal(false);

  private pagina = 1;

  readonly formulario = this.fb.nonNullable.group({
    contenido: ['', [Validators.required]],
  });

  constructor() {
    effect(() => {
      const mensaje = this.canvasService.ultimoMensajeChat();
      if (mensaje) {
        this.mensajes.update((actuales) => [...actuales, mensaje]);
        this.desplazarAlFondo();
      }
    });
  }

  ngOnInit(): void {
    this.cargarInicial();
  }

  miUsuarioId(): number | undefined {
    return this.authService.usuario()?.id;
  }

  private cargarInicial(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.workspaceApi.listarMensajes(this.proyectoId(), 1, TAMANO_PAGINA).subscribe({
      next: (respuesta) => {
        this.mensajes.set([...respuesta.items].reverse());
        this.pagina = 1;
        this.hayMas.set(respuesta.total_paginas > 1);
        this.cargando.set(false);
        this.desplazarAlFondo();
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  alScrollear(): void {
    const elemento = this.lista()?.nativeElement;
    if (!elemento || elemento.scrollTop > UMBRAL_SCROLL_ARRIBA) {
      return;
    }
    this.cargarMas();
  }

  private cargarMas(): void {
    if (this.cargandoMas() || !this.hayMas()) {
      return;
    }
    this.cargandoMas.set(true);
    const siguientePagina = this.pagina + 1;
    const elemento = this.lista()?.nativeElement;
    const alturaAnterior = elemento?.scrollHeight ?? 0;

    this.workspaceApi.listarMensajes(this.proyectoId(), siguientePagina, TAMANO_PAGINA).subscribe({
      next: (respuesta) => {
        const anteriores = [...respuesta.items].reverse();
        this.mensajes.update((actuales) => [...anteriores, ...actuales]);
        this.pagina = siguientePagina;
        this.hayMas.set(siguientePagina < respuesta.total_paginas);
        this.cargandoMas.set(false);

        setTimeout(() => {
          if (elemento) {
            elemento.scrollTop = elemento.scrollHeight - alturaAnterior;
          }
        });
      },
      error: (err: unknown) => {
        this.cargandoMas.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.enviando.set(true);
    this.error.set(null);
    const contenido = this.formulario.getRawValue().contenido;

    this.workspaceApi.enviarMensaje(this.proyectoId(), { contenido }).subscribe({
      next: () => {
        this.enviando.set(false);
        this.formulario.reset({ contenido: '' });
      },
      error: (err: unknown) => {
        this.enviando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  private desplazarAlFondo(): void {
    // setTimeout (no queueMicrotask): hace falta esperar a que Angular
    // termine de pintar los mensajes nuevos en el DOM antes de leer
    // scrollHeight, si no el valor queda desactualizado y no baja del todo.
    setTimeout(() => {
      const elemento = this.lista()?.nativeElement;
      if (elemento) {
        elemento.scrollTop = elemento.scrollHeight;
      }
    });
  }
}
