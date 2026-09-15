export function obtenerMensajeError(err: unknown): string {
  const detalle = (err as { error?: { detail?: unknown } })?.error?.detail;
  return typeof detalle === 'string' ? detalle : 'Ocurrió un error. Intenta de nuevo.';
}
