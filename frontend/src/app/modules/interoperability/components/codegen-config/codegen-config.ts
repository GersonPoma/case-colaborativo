import { Component, effect, inject, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { Modal } from '../../../../shared/components/modal/modal';
import { BaseDatosDestino } from '../../models/interoperability.model';
import { InteroperabilidadApiService } from '../../services/interoperability-api.service';

@Component({
  selector: 'app-codegen-config',
  imports: [ReactiveFormsModule, Modal],
  templateUrl: './codegen-config.html',
  styleUrl: './codegen-config.scss',
})
export class CodegenConfig {
  private readonly fb = inject(FormBuilder);
  private readonly interoperabilidadApi = inject(InteroperabilidadApiService);

  readonly abierto = input(false);
  readonly proyectoId = input.required<number>();

  readonly cerrado = output<void>();

  readonly cargando = signal(false);
  readonly guardando = signal(false);
  readonly error = signal<string | null>(null);

  readonly formulario = this.fb.nonNullable.group({
    group_id: ['', [Validators.required]],
    artifact_id: ['', [Validators.required]],
    java_version: this.fb.nonNullable.control('17', [Validators.required]),
    spring_boot_version: ['', [Validators.required]],
    base_datos: this.fb.nonNullable.control<BaseDatosDestino>('POSTGRESQL', [Validators.required]),
  });

  constructor() {
    effect(() => {
      if (!this.abierto()) {
        return;
      }
      this.cargar();
    });
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.interoperabilidadApi.obtenerConfiguracionTranspilacion(this.proyectoId()).subscribe({
      next: (config) => {
        this.formulario.setValue({
          group_id: config.group_id,
          artifact_id: config.artifact_id,
          java_version: config.java_version,
          spring_boot_version: config.spring_boot_version,
          base_datos: config.base_datos,
        });
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.guardando.set(true);
    this.error.set(null);

    this.interoperabilidadApi
      .configurarTranspilacion(this.proyectoId(), this.formulario.getRawValue())
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.cerrar();
        },
        error: (err: unknown) => {
          this.guardando.set(false);
          this.error.set(obtenerMensajeError(err));
        },
      });
  }

  cerrar(): void {
    this.cerrado.emit();
  }
}
