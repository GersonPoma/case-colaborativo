import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { Modal } from '../../../../shared/components/modal/modal';
import { Paginador } from '../../../../shared/components/paginador/paginador';
import { Proyecto, ProyectoConRol } from '../../models/proyecto.model';
import { WorkspaceApiService } from '../../services/workspace-api.service';

@Component({
  selector: 'app-project-list',
  imports: [ReactiveFormsModule, RouterLink, Modal, Paginador, DatePipe],
  templateUrl: './project-list.html',
  styleUrl: './project-list.scss',
})
export class ProjectList {
  private readonly fb = inject(FormBuilder);
  private readonly workspaceApi = inject(WorkspaceApiService);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly propios = signal<Proyecto[]>([]);
  readonly paginaPropios = signal(1);
  readonly totalPaginasPropios = signal(1);

  readonly colaboraciones = signal<ProyectoConRol[]>([]);
  readonly paginaColaboraciones = signal(1);
  readonly totalPaginasColaboraciones = signal(1);

  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  readonly mostrarFormulario = signal(false);
  readonly creando = signal(false);

  readonly formulario = this.fb.nonNullable.group({
    nombre: ['', [Validators.required]],
    descripcion: [''],
  });

  constructor() {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);

    forkJoin({
      propios: this.workspaceApi.listarPropios(this.paginaPropios()),
      colaboraciones: this.workspaceApi.listarColaboraciones(this.paginaColaboraciones()),
    }).subscribe({
      next: ({ propios, colaboraciones }) => {
        this.propios.set(propios.items);
        this.totalPaginasPropios.set(propios.total_paginas);
        this.colaboraciones.set(colaboraciones.items);
        this.totalPaginasColaboraciones.set(colaboraciones.total_paginas);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.error.set(obtenerMensajeError(err));
        this.cargando.set(false);
      },
    });
  }

  cambiarPaginaPropios(pagina: number): void {
    this.paginaPropios.set(pagina);
    this.workspaceApi.listarPropios(pagina).subscribe({
      next: (respuesta) => {
        this.propios.set(respuesta.items);
        this.totalPaginasPropios.set(respuesta.total_paginas);
      },
      error: (err: unknown) => this.error.set(obtenerMensajeError(err)),
    });
  }

  cambiarPaginaColaboraciones(pagina: number): void {
    this.paginaColaboraciones.set(pagina);
    this.workspaceApi.listarColaboraciones(pagina).subscribe({
      next: (respuesta) => {
        this.colaboraciones.set(respuesta.items);
        this.totalPaginasColaboraciones.set(respuesta.total_paginas);
      },
      error: (err: unknown) => this.error.set(obtenerMensajeError(err)),
    });
  }

  abrirFormulario(): void {
    this.mostrarFormulario.set(true);
  }

  cancelarFormulario(): void {
    this.mostrarFormulario.set(false);
    this.formulario.reset();
  }

  crear(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.creando.set(true);
    this.error.set(null);

    const datos = this.formulario.getRawValue();

    this.workspaceApi
      .crear({ nombre: datos.nombre, descripcion: datos.descripcion || null })
      .subscribe({
        next: (proyecto) => {
          this.creando.set(false);
          this.router.navigate(['/editor', proyecto.id]);
        },
        error: (err: unknown) => {
          this.creando.set(false);
          this.error.set(obtenerMensajeError(err));
        },
      });
  }

  cerrarSesion(): void {
    this.authService.logout();
    this.router.navigateByUrl('/');
  }
}
