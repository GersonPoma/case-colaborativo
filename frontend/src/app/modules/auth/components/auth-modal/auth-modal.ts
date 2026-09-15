import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Modal } from '../../../../shared/components/modal/modal';

@Component({
  selector: 'app-auth-modal',
  imports: [Modal, RouterLink],
  templateUrl: './auth-modal.html',
  styleUrl: './auth-modal.scss',
})
export class AuthModal {
  readonly abierto = input(false);
  readonly cerrado = output<void>();

  cerrar(): void {
    this.cerrado.emit();
  }
}
