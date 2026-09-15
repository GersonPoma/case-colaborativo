import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { Colaborador, Proyecto } from '../../models/proyecto.model';
import { WorkspaceApiService } from '../../services/workspace-api.service';

@Component({
  selector: 'app-project-detail',
  imports: [RouterLink, DatePipe],
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
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly eliminando = signal(false);

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
