**English** | [Español](README.es.md)

# Fornaviva — Frontend

React and Vite frontend for Fornaviva, a fictional Italian pizzeria. The Spanish-language interface provides a responsive menu with category filters, immediate access to a local menu copy, silent API synchronization and a conversational assistant connected to the FastAPI backend. During a prolonged backend connection, an animated oven and culinary facts are displayed.

- [Live demo](https://fornaviva.vercel.app)
- [Main documentation](../README.md)

## Local development

Use compatible Node.js and npm versions as documented in the main README. From this directory:

```bash
npm ci
npm run dev -- --port 5173
```

Open http://localhost:5173. Start the backend separately following the main README. The default API URL is `http://localhost:8000`; `VITE_API_URL` can override it. Never place provider keys in React code or `VITE_*` variables.

## Build and checks

```bash
npm run build
npm run preview
npm test
npm run lint
```

The frontend is deployed on Vercel. See the [license](../LICENSE) for copyright and usage terms.
