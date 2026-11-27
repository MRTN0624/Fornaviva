[English](README.md) | **Español**

# Fornaviva — Frontend

Frontend de React y Vite para Fornaviva, una pizzería italiana ficticia. La interfaz en español ofrece una carta adaptable con filtros por categoría, acceso inmediato a una copia local de la carta, sincronización silenciosa con la API y un asistente conversacional conectado al backend FastAPI. Durante una conexión prolongada al backend se muestran un horno animado y curiosidades gastronómicas.

- [Demostración en línea](https://fornaviva.vercel.app)
- [Documentación principal](../README.es.md)

## Desarrollo local

Utilizar versiones compatibles de Node.js y npm según el README principal. Desde este directorio:

```bash
npm ci
npm run dev -- --port 5173
```

Abrir http://localhost:5173. Iniciar el backend por separado siguiendo el README principal. La URL predeterminada de la API es `http://localhost:8000`; puede modificarse mediante `VITE_API_URL`. Nunca introducir claves del proveedor en el código React ni en variables `VITE_*`.

## Compilación y comprobaciones

```bash
npm run build
npm run preview
npm test
npm run lint
```

El frontend está desplegado en Vercel. Consultar la [licencia](../LICENSE) para conocer los derechos de autor y las condiciones de uso.
