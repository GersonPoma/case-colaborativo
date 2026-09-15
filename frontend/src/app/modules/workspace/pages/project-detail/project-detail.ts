import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { EstadoLienzo } from '../../../../core/models/lienzo.model';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { DiagramPreview } from '../../../../shared/components/diagram-preview/diagram-preview';
import { Modal } from '../../../../shared/components/modal/modal';
import { Paginador } from '../../../../shared/components/paginador/paginador';
import { Colaborador, HistorialVersionResumen, Proyecto } from '../../models/proyecto.model';
import { WorkspaceApiService } from '../../services/workspace-api.service';

@Component({
  selector: 'app-project-detail',
  imports: [RouterLink, DatePipe, Modal, DiagramPreview, Paginador],
  templateUrl: './project-detail.html',
  styleUrl: './project-detail.scss',
})
export class ProjectDetail {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly workspaceApi = inject(WorkspaceApiService);
  private readonly authService = inject(AuthService);

  private readonly proyectoId = Number(this.route.snapshot.paramMap.get('id'));

  readonly proyecto = signal<Proyecto | null>(null);
  readonly colaboradores = signal<Colaborador[]>([]);
  readonly historial = signal<HistorialVersionResumen[]>([]);
  readonly paginaHistorial = signal(1);
  readonly totalPaginasHistorial = signal(1);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly eliminando = signal(false);
  readonly restaurandoId = signal<number | null>(null);
  readonly mostrarPreview = signal(false);
  readonly cargandoPreview = signal(false);
  readonly lienzoPreview = signal<EstadoLienzo | null>(null);

  readonly esDueno = computed(() => {
    const usuario = this.authService.usuario();
    const proyecto = this.proyecto();
    return !!usuario && !!proyecto && usuario.id === proyecto.id_dueno;
  });

  constructor() {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.workspaceApi.obtener(this.proyectoId).subscribe({
      next: (proyecto) => {
        this.proyecto.set(proyecto);
        this.cargarColaboradores();
        if (this.esDueno()) {
          this.cargarHistorial();
        }
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  private cargarColaboradores(): void {
    this.workspaceApi.listarColaboradores(this.proyectoId).subscribe({
      next: (pagina) => {
        this.colaboradores.set(pagina.items);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  private cargarHistorial(): void {
    this.workspaceApi.listarHistorial(this.proyectoId, this.paginaHistorial()).subscribe({
      next: (pagina) => {
        this.historial.set(pagina.items);
        this.totalPaginasHistorial.set(pagina.total_paginas);
      },
      error: (err: unknown) => this.error.set(obtenerMensajeError(err)),
    });
  }

  cambiarPaginaHistorial(pagina: number): void {
    this.paginaHistorial.set(pagina);
    this.workspaceApi.listarHistorial(this.proyectoId, pagina).subscribe({
      next: (respuesta) => {
        this.historial.set(respuesta.items);
        this.totalPaginasHistorial.set(respuesta.total_paginas);
      },
      error: (err: unknown) => this.error.set(obtenerMensajeError(err)),
    });
  }

  verPreview(historialId: number): void {
    this.mostrarPreview.set(true);
    this.cargandoPreview.set(true);
    this.lienzoPreview.set(null);

    this.workspaceApi.obtenerLienzoHistorial(this.proyectoId, historialId).subscribe({
      next: (lienzo) => {
        this.lienzoPreview.set(lienzo);
        this.cargandoPreview.set(false);
      },
      error: (err: unknown) => {
        this.cargandoPreview.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  cerrarPreview(): void {
    this.mostrarPreview.set(false);
    this.lienzoPreview.set(null);
  }

  restaurar(historialId: number): void {
    if (!confirm('¿Restaurar el proyecto a esta versión? Se reemplaza el diagrama actual.')) {
      return;
    }

    this.restaurandoId.set(historialId);
    this.error.set(null);

    this.workspaceApi.restaurarVersion(this.proyectoId, historialId).subscribe({
      next: (proyecto) => {
        this.proyecto.set(proyecto);
        this.restaurandoId.set(null);
      },
      error: (err: unknown) => {
        this.restaurandoId.set(null);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  eliminar(): void {
    if (!confirm('¿Seguro que querés eliminar este proyecto? Esta acción no se puede deshacer.')) {
      return;
    }

    this.eliminando.set(true);
    this.error.set(null);

    this.workspaceApi.eliminar(this.proyectoId).subscribe({
      next: () => this.router.navigateByUrl('/proyectos'),
      error: (err: unknown) => {
        this.eliminando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }
}
