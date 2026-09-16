import { NgTemplateOutlet } from '@angular/common';
import { Component, computed, inject, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Atributo, Clase, Metodo, ParametroMetodo, Visibilidad } from '../../../../core/models/lienzo.model';
import { Modal } from '../../../../shared/components/modal/modal';
import { CanvasService } from '../../services/canvas.service';

@Component({
  selector: 'app-class-panel',
  imports: [ReactiveFormsModule, Modal, NgTemplateOutlet],
  templateUrl: './class-panel.html',
  styleUrl: './class-panel.scss',
})
export class ClassPanel {
  private readonly fb = inject(FormBuilder);
  private readonly canvasService = inject(CanvasService);

  readonly clase = input.required<Clase>();
  readonly soloLectura = input(false);

  readonly cerrar = output<void>();

  readonly editandoNombre = signal(false);
  readonly editandoAtributoId = signal<string | null>(null);
  readonly editandoMetodoId = signal<string | null>(null);
  readonly mostrarConfirmarEliminar = signal(false);
  readonly pestanaActiva = signal<'atributos' | 'metodos'>('atributos');

  readonly atributosOrdenados = computed(() =>
    Object.values(this.clase().atributos).sort((a, b) => a.orden - b.orden),
  );
  readonly metodosOrdenados = computed(() =>
    Object.values(this.clase().metodos).sort((a, b) => a.orden - b.orden),
  );

  readonly formNombre = this.fb.nonNullable.group({
    nombre: ['', [Validators.required]],
  });

  readonly formAtributo = this.fb.nonNullable.group({
    nombre: ['', [Validators.required]],
    tipo: [''],
    es_pk: [false],
    visibilidad: this.fb.nonNullable.control<Visibilidad>('PRIVADO'),
  });

  readonly formMetodo = this.fb.nonNullable.group({
    nombre: ['', [Validators.required]],
    tipo_retorno: [''],
    visibilidad: this.fb.nonNullable.control<Visibilidad>('PUBLICO'),
  });

  readonly parametrosMetodo = signal<ParametroMetodo[]>([]);

  iniciarEdicionNombre(): void {
    this.formNombre.setValue({ nombre: this.clase().nombre });
    this.editandoNombre.set(true);
  }

  guardarNombre(): void {
    if (this.formNombre.invalid) {
      this.formNombre.markAllAsTouched();
      return;
    }
    this.canvasService.editarClase(this.clase().id, this.formNombre.getRawValue().nombre);
    this.editandoNombre.set(false);
  }

  eliminarClase(): void {
    this.mostrarConfirmarEliminar.set(true);
  }

  confirmarEliminarClase(): void {
    this.canvasService.eliminarClase(this.clase().id);
    this.mostrarConfirmarEliminar.set(false);
    this.cerrar.emit();
  }

  cancelarEliminarClase(): void {
    this.mostrarConfirmarEliminar.set(false);
  }

  iniciarNuevoAtributo(): void {
    this.formAtributo.reset({ nombre: '', tipo: '', es_pk: false, visibilidad: 'PRIVADO' });
    this.editandoAtributoId.set('nuevo');
  }

  iniciarEdicionAtributo(atributo: Atributo): void {
    this.formAtributo.setValue({
      nombre: atributo.nombre,
      tipo: atributo.tipo ?? '',
      es_pk: atributo.es_pk,
      visibilidad: atributo.visibilidad,
    });
    this.editandoAtributoId.set(atributo.id);
  }

  guardarAtributo(): void {
    if (this.formAtributo.invalid) {
      this.formAtributo.markAllAsTouched();
      return;
    }
    const valor = this.formAtributo.getRawValue();
    const datos = {
      nombre: valor.nombre,
      tipo: valor.tipo.trim() || null,
      es_pk: valor.es_pk,
      visibilidad: valor.visibilidad,
    };
    const id = this.editandoAtributoId();
    if (id === 'nuevo') {
      this.canvasService.agregarAtributo(this.clase().id, datos);
    } else if (id) {
      this.canvasService.editarAtributo(this.clase().id, id, datos);
    }
    this.editandoAtributoId.set(null);
  }

  eliminarAtributo(atributo: Atributo): void {
    this.canvasService.eliminarAtributo(this.clase().id, atributo.id);
  }

  cancelarAtributo(): void {
    this.editandoAtributoId.set(null);
  }

  iniciarNuevoMetodo(): void {
    this.formMetodo.reset({ nombre: '', tipo_retorno: '', visibilidad: 'PUBLICO' });
    this.parametrosMetodo.set([]);
    this.editandoMetodoId.set('nuevo');
  }

  iniciarEdicionMetodo(metodo: Metodo): void {
    this.formMetodo.setValue({
      nombre: metodo.nombre,
      tipo_retorno: metodo.tipo_retorno ?? '',
      visibilidad: metodo.visibilidad,
    });
    this.parametrosMetodo.set([...metodo.parametros]);
    this.editandoMetodoId.set(metodo.id);
  }

  agregarParametro(): void {
    this.parametrosMetodo.update((lista) => [...lista, { nombre: '', tipo: '' }]);
  }

  quitarParametro(indice: number): void {
    this.parametrosMetodo.update((lista) => lista.filter((_, i) => i !== indice));
  }

  actualizarParametro(indice: number, campo: 'nombre' | 'tipo', valor: string): void {
    this.parametrosMetodo.update((lista) =>
      lista.map((p, i) => (i === indice ? { ...p, [campo]: valor } : p)),
    );
  }

  guardarMetodo(): void {
    if (this.formMetodo.invalid) {
      this.formMetodo.markAllAsTouched();
      return;
    }
    const valor = this.formMetodo.getRawValue();
    const parametros = this.parametrosMetodo().filter((p) => p.nombre.trim() && p.tipo.trim());
    const datos = {
      nombre: valor.nombre,
      tipo_retorno: valor.tipo_retorno.trim() || null,
      visibilidad: valor.visibilidad,
      parametros,
    };
    const id = this.editandoMetodoId();
    if (id === 'nuevo') {
      this.canvasService.agregarMetodo(this.clase().id, datos);
    } else if (id) {
      this.canvasService.editarMetodo(this.clase().id, id, datos);
    }
    this.editandoMetodoId.set(null);
  }

  eliminarMetodo(metodo: Metodo): void {
    this.canvasService.eliminarMetodo(this.clase().id, metodo.id);
  }

  cancelarMetodo(): void {
    this.editandoMetodoId.set(null);
  }

  simboloVisibilidad(visibilidad: Visibilidad): string {
    return { PUBLICO: '+', PRIVADO: '-', PROTEGIDO: '#', PAQUETE: '~' }[visibilidad];
  }

  parametrosTexto(metodo: Metodo): string {
    return metodo.parametros.map((p) => `${p.nombre}: ${p.tipo}`).join(', ');
  }
}
