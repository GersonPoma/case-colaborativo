import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-paginador',
  imports: [],
  templateUrl: './paginador.html',
  styleUrl: './paginador.scss',
})
export class Paginador {
  readonly pagina = input.required<number>();
  readonly totalPaginas = input.required<number>();
  readonly cambio = output<number>();

  anterior(): void {
    if (this.pagina() > 1) {
      this.cambio.emit(this.pagina() - 1);
    }
  }

  siguiente(): void {
    if (this.pagina() < this.totalPaginas()) {
      this.cambio.emit(this.pagina() + 1);
    }
  }
}
