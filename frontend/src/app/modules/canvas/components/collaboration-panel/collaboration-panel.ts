import { Component, effect, inject, input, signal, untracked } from '@angular/core';
import { ChatPanel } from '../chat-panel/chat-panel';
import { CanvasService } from '../../services/canvas.service';

type PestanaColaboracion = 'chat' | 'ia';

@Component({
  selector: 'app-collaboration-panel',
  imports: [ChatPanel],
  templateUrl: './collaboration-panel.html',
  styleUrl: './collaboration-panel.scss',
  host: {
    '[class.minimizado]': 'minimizado()',
  },
})
export class CollaborationPanel {
  private readonly canvasService = inject(CanvasService);

  readonly proyectoId = input.required<number>();

  readonly minimizado = signal(false);
  readonly pestanaActiva = signal<PestanaColaboracion>('chat');
  readonly noLeidosChat = signal(0);

  constructor() {
    // solo debe reaccionar a que llegue un mensaje NUEVO, no a que cambien
    // "minimizado"/"pestanaActiva" — por eso esos dos se leen con untracked,
    // así no quedan como dependencias que reejecuten esto con el mismo mensaje.
    effect(() => {
      const mensaje = this.canvasService.ultimoMensajeChat();
      if (!mensaje) {
        return;
      }
      untracked(() => {
        if (this.minimizado() || this.pestanaActiva() !== 'chat') {
          this.noLeidosChat.update((n) => n + 1);
        }
      });
    });
  }

  alternarMinimizado(): void {
    this.minimizado.update((valor) => !valor);
    if (!this.minimizado() && this.pestanaActiva() === 'chat') {
      this.noLeidosChat.set(0);
    }
  }

  seleccionarPestana(pestana: PestanaColaboracion): void {
    this.pestanaActiva.set(pestana);
    if (pestana === 'chat') {
      this.noLeidosChat.set(0);
    }
  }
}
