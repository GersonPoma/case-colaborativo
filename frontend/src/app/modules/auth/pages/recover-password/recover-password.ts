import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LucideEye, LucideEyeOff } from '@lucide/angular';
import { obtenerMensajeError } from '../../../../core/utils/http-error.util';
import { AuthApiService } from '../../services/auth-api.service';

@Component({
  selector: 'app-recover-password',
  imports: [ReactiveFormsModule, RouterLink, LucideEye, LucideEyeOff],
  templateUrl: './recover-password.html',
  styleUrl: './recover-password.scss',
})
export class RecoverPassword {
  private readonly fb = inject(FormBuilder);
  private readonly authApi = inject(AuthApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly token = signal(this.route.snapshot.queryParamMap.get('token'));
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly enviado = signal(false);
  readonly mostrarPassword = signal(false);

  readonly formularioSolicitar = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  readonly formularioRestablecer = this.fb.nonNullable.group({
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  alternarMostrarPassword(): void {
    this.mostrarPassword.update((valor) => !valor);
  }

  solicitar(): void {
    if (this.formularioSolicitar.invalid) {
      this.formularioSolicitar.markAllAsTouched();
      return;
    }

    this.cargando.set(true);
    this.error.set(null);

    this.authApi.recuperarContrasena(this.formularioSolicitar.getRawValue().email).subscribe({
      next: () => {
        this.cargando.set(false);
        this.enviado.set(true);
      },
      error: (err: unknown) => {
        this.cargando.set(false);
        this.error.set(obtenerMensajeError(err));
      },
    });
  }

  restablecer(): void {
    if (this.formularioRestablecer.invalid) {
      this.formularioRestablecer.markAllAsTouched();
      return;
    }

    const token = this.token();
    if (!token) {
      return;
    }

    this.cargando.set(true);
    this.error.set(null);

    this.authApi
      .restablecerContrasena(token, this.formularioRestablecer.getRawValue().password)
      .subscribe({
        next: () => {
          this.cargando.set(false);
          this.router.navigateByUrl('/iniciar-sesion');
        },
        error: (err: unknown) => {
          this.cargando.set(false);
          this.error.set(obtenerMensajeError(err));
        },
      });
  }
}
