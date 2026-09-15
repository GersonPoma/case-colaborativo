import { Component, computed, effect, inject, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Clase, Relacion, TipoRelacion } from '../../../../core/models/lienzo.model';
import { Modal } from '../../../../shared/components/modal/modal';
import { CanvasService } from '../../services/canvas.service';

@Component({
  selector: 'app-relation-form',
  imports: [ReactiveFormsModule, Modal],
  templateUrl: './relation-form.html',
  styleUrl: './relation-form.scss',
})
export class RelationForm {
  private readonly fb = inject(FormBuilder);
  private readonly canvasService = inject(CanvasService);

  readonly abierto = input(false);
  readonly origenId = input<string | null>(null);
  readonly destinoId = input<string | null>(null);
  readonly relacion = input<Relacion | null>(null);
  readonly clases = input<Record<string, Clase>>({});
  readonly tipoInicial = input<TipoRelacion>('ASOCIACION');

  readonly cerrado = output<void>();

  readonly confirmandoEliminar = signal(false);
  readonly claseAsociadaIdActual = signal<string | null>(null);

  readonly editando = computed(() => this.relacion() !== null);

  readonly nombreOrigen = computed(() => {
    const id = this.relacion()?.origen_id ?? this.origenId();
    return id ? (this.clases()[id]?.nombre ?? id) : '';
  });
  readonly nombreDestino = computed(() => {
    const id = this.relacion()?.destino_id ?? this.destinoId();
    return id ? (this.clases()[id]?.nombre ?? id) : '';
  });

  readonly nombreClaseAsociadaActual = computed(() => {
    const id = this.claseAsociadaIdActual();
    return id ? (this.clases()[id]?.nombre ?? id) : '';
  });

  readonly formulario = this.fb.nonNullable.group({
    tipo: this.fb.nonNullable.control<TipoRelacion>('ASOCIACION', [Validators.required]),
    cardinalidad_origen: [''],
    cardinalidad_destino: [''],
    etiqueta: [''],
  });

  constructor() {
    effect(() => {
      if (!this.abierto()) {
        return;
      }
      this.confirmandoEliminar.set(false);
      const relacion = this.relacion();
      this.claseAsociadaIdActual.set(relacion?.clase_asociada_id ?? null);
      if (relacion) {
        this.formulario.setValue({
          tipo: relacion.tipo,
          cardinalidad_origen: relacion.cardinalidad_origen ?? '',
          cardinalidad_destino: relacion.cardinalidad_destino ?? '',
          etiqueta: relacion.etiqueta ?? '',
        });
      } else {
        this.formulario.reset({
          tipo: this.tipoInicial(),
          cardinalidad_origen: '',
          cardinalidad_destino: '',
          etiqueta: '',
        });
      }
    });
  }

  guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    const valor = this.formulario.getRawValue();
    const datos = {
      tipo: valor.tipo,
      cardinalidad_origen: valor.cardinalidad_origen.trim() || null,
      cardinalidad_destino: valor.cardinalidad_destino.trim() || null,
      etiqueta: valor.etiqueta.trim() || null,
      clase_asociada_id: this.claseAsociadaIdActual(),
    };

    const relacion = this.relacion();
    if (relacion) {
      this.canvasService.editarRelacion(relacion.id, datos);
    } else if (this.origenId() && this.destinoId()) {
      this.canvasService.trazarRelacion(this.origenId()!, this.destinoId()!, datos);
    }
    this.cerrado.emit();
  }

  eliminar(): void {
    this.confirmandoEliminar.set(true);
  }

  confirmarEliminar(): void {
    const relacion = this.relacion();
    if (!relacion) {
      return;
    }
    this.canvasService.eliminarRelacion(relacion.id);
    this.confirmandoEliminar.set(false);
    this.cerrado.emit();
  }

  cancelarEliminar(): void {
    this.confirmandoEliminar.set(false);
  }

  cancelar(): void {
    this.cerrado.emit();
  }
}
