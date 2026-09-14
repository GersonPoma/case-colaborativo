export interface Pagina<T> {
  items: T[];
  total: number;
  pagina: number;
  tamano: number;
  total_paginas: number;
}
