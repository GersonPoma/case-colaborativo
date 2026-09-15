import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { Colaborador, Proyecto, RolColaborador } from '../../models/proyecto.model';
import { WorkspaceApiService } from '../../services/workspace-api.service';

@Component({
  selector: 'app-collaborators',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './collaborators.html',
  styleUrl: './collaborators.scss',
})
export class Collaborators {
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);
  private readonly workspaceApi = inject(WorkspaceApiService);
  private readonly authService = inject(AuthService);

  readonly proyectoId = Number(this.route.snapshot.paramMap.get('id'));

  readonly proyecto = signal<Proyecto | null>(null);
  readonly colaboradores = signal<Colaborador[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly invitando = signal(false);
  readonly procesandoUsuarioId = signal<number | null>(null);

  readonly esDueno = computed(() => {
    const usuario = this.authService.usuario();
    const proyecto = this.proyecto();
    return !!usuario && !!proyecto && usuario.id === proyecto.id_dueno;
  });

  readonly formulario = this.fb.nonNullable.group({
    username: ['', [Validators.required]],
    rol: this.fb.nonNullable.control<RolColaborador>('LECTOR', [Validators.required]),
  });

  constructor() {
    this.cargar();
  }

  private cargar(): void {
    this.cargando.set(true);
    this.error.set(null);

    forkJoin({
      proyecto: this.workspaceApi.obtener(this.proyectoId),
      colaboradores: this.workspaceApi.listarColaboradores(this.proyectoId),
    }).subscribe({
      next: ({ proyecto, colaboradores }) => {
        this.proyecto.set(proyecto);
        this.colaboradores.set(colaboradores.items);
        this.cargando.set(false);
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  invitar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.invitando.set(true);
    this.error.set(null);

    this.workspaceApi.invitarColaborador(this.proyectoId, this.formulario.getRawValue()).subscribe({
      next: (colaborador) => {
        this.colaboradores.update((lista) => [...lista, colaborador]);
        this.invitando.set(false);
        this.formulario.reset({ username: '', rol: 'LECTOR' });
      },
      error: (err: unknown) => {
        this.invitando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  cambiarRol(colaborador: Colaborador, rol: RolColaborador): void {
    if (colaborador.rol === rol) {
      return;
    }

    this.procesandoUsuarioId.set(colaborador.usuario.id);
    this.error.set(null);

    this.workspaceApi
      .cambiarRolColaborador(this.proyectoId, colaborador.usuario.id, { rol })
      .subscribe({
        next: (actualizado) => {
          this.colaboradores.update((lista) =>
            lista.map((c) => (c.usuario.id === actualizado.usuario.id ? actualizado : c)),
          );
          this.procesandoUsuarioId.set(null);
        },
        error: (err: unknown) => {
          this.procesandoUsuarioId.set(null);
          this.error.set(obtenerMensajeError(err));
        },
      });
  }

  quitar(colaborador: Colaborador): void {
    if (!confirm(`¿Quitar a ${colaborador.usuario.username} del proyecto?`)) {
      return;
    }

    this.procesandoUsuarioId.set(colaborador.usuario.id);
    this.error.set(null);

    this.workspaceApi.quitarColaborador(this.proyectoId, colaborador.usuario.id).subscribe({
      next: () => {
        this.colaboradores.update((lista) =>
          lista.filter((c) => c.usuario.id !== colaborador.usuario.id),
        );
        this.procesandoUsuarioId.set(null);
      },
      error: (err: unknown) => {
        this.procesandoUsuarioId.set(null);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }
}
