export const environment = {
  production: true,
  // TODO: reemplazar cuando el backend esté desplegado (ej. EC2) — el backend
  // no tiene prefijo /api, y como el frontend va en un dominio distinto
  // (Cloudflare Pages) necesita la URL completa, no una ruta relativa.
  apiUrl: 'https://api.case-colaborativo.example.com',
  wsUrl: 'wss://api.case-colaborativo.example.com/ws',
};
