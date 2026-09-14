import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { AuthApiService } from '../../services/auth-api.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly fb = inject(FormBuilder);
  private readonly authApi = inject(AuthApiService);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);

  readonly formulario = this.fb.nonNullable.group({
    username: ['', [Validators.required, Validators.minLength(3)]],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  enviar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    this.cargando.set(true);
    this.error.set(null);

    this.authApi.iniciarSesion(this.formulario.getRawValue()).subscribe({
      next: (respuesta) => {
        this.authService.setToken(respuesta.access_token);
        this.authApi.obtenerUsuarioActual().subscribe({
          next: (usuario) => this.authService.setUsuario(usuario),
          complete: () => {
            this.cargando.set(false);
            this.router.navigateByUrl('/proyectos');
          },
        });
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(this.obtenerMensajeError(err));
      },
    });
  }

  private obtenerMensajeError(err: unknown): string {
    const detalle = (err as { error?: { detail?: unknown } })?.error?.detail;
    return typeof detalle === 'string' ? detalle : 'Ocurrió un error. Intenta de nuevo.';
  }
}
