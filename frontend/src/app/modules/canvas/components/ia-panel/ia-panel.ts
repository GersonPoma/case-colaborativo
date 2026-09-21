import { Component, ElementRef, inject, input, signal, viewChild } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { LucideMic, LucideX } from '@lucide/angular';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { IaService } from '../../services/ia.service';

interface MensajeIa {
  autor: 'yo' | 'ia';
  texto: string;
}

@Component({
  selector: 'app-ia-panel',
  imports: [ReactiveFormsModule, LucideMic, LucideX],
  templateUrl: './ia-panel.html',
  styleUrl: './ia-panel.scss',
})
export class IaPanel {
  private readonly iaService = inject(IaService);
  private readonly fb = inject(FormBuilder);

  private readonly lista = viewChild<ElementRef<HTMLDivElement>>('lista');

  readonly proyectoId = input.required<number>();

  readonly mensajes = signal<MensajeIa[]>([]);
  readonly procesando = signal(false);
  readonly grabando = signal(false);
  readonly error = signal<string | null>(null);

  private mediaRecorder: MediaRecorder | null = null;
  private fragmentos: Blob[] = [];
  private grabacionCancelada = false;

  readonly formulario = this.fb.nonNullable.group({
    texto: ['', [Validators.required]],
  });

  enviarTexto(): void {
    if (this.formulario.invalid || this.procesando() || this.grabando()) {
      this.formulario.markAllAsTouched();
      return;
    }
    const texto = this.formulario.getRawValue().texto;
    this.agregarMensaje('yo', texto);
    this.formulario.reset({ texto: '' });
    this.procesando.set(true);
    this.error.set(null);

    this.iaService.refactorizarPorTexto(this.proyectoId(), texto).subscribe({
      next: (respuesta) => {
        this.procesando.set(false);
        this.agregarMensaje('ia', respuesta.respuesta);
      },
      error: (err: unknown) => {
        this.procesando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  async alternarGrabacion(): Promise<void> {
    if (this.grabando()) {
      this.mediaRecorder?.stop();
      return;
    }
    if (this.procesando()) {
      return;
    }
    this.error.set(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.fragmentos = [];
      this.grabacionCancelada = false;
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (evento) => {
        if (evento.data.size > 0) {
          this.fragmentos.push(evento.data);
        }
      };
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        this.grabando.set(false);
        if (!this.grabacionCancelada) {
          this.enviarAudio(new Blob(this.fragmentos, { type: 'audio/webm' }));
        }
      };
      this.mediaRecorder = mediaRecorder;
      mediaRecorder.start();
      this.grabando.set(true);
    } catch {
      this.error.set('No se pudo acceder al micrófono. Revisá los permisos del navegador.');
    }
  }

  cancelarGrabacion(): void {
    if (!this.grabando()) {
      return;
    }
    this.grabacionCancelada = true;
    this.mediaRecorder?.stop();
  }

  private enviarAudio(audio: Blob): void {
    this.procesando.set(true);
    this.error.set(null);

    this.iaService.refactorizarPorVoz(this.proyectoId(), audio).subscribe({
      next: (respuesta) => {
        this.procesando.set(false);
        this.agregarMensaje('yo', respuesta.texto);
        this.agregarMensaje('ia', respuesta.respuesta);
      },
      error: (err: unknown) => {
        this.procesando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  private agregarMensaje(autor: 'yo' | 'ia', texto: string): void {
    this.mensajes.update((actuales) => [...actuales, { autor, texto }]);
    this.desplazarAlFondo();
  }

  private desplazarAlFondo(): void {
    // setTimeout (no queueMicrotask): hace falta esperar a que Angular
    // termine de pintar el mensaje nuevo en el DOM antes de leer
    // scrollHeight, si no el valor queda desactualizado y no baja del todo.
    setTimeout(() => {
      const elemento = this.lista()?.nativeElement;
      if (elemento) {
        elemento.scrollTop = elemento.scrollHeight;
      }
    });
  }
}
