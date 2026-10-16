# AGENTS.md · Melos

## Qué es este proyecto

[Una frase: qué problema resuelve y para quién. Ejemplo: "Asistente que
responde las dudas de los vecinos de la asociación X a partir de sus
estatutos".]

## Cómo está hecho

- Python 3.12, gestionado con [uv](https://docs.astral.sh/uv/).
- Interfaz: Streamlit.
- IA: API de Gemini con el SDK `google-genai`. El modelo está en la
  constante `MODELO` de `src/app.py`.
- La especificación completa está en `docs/prd.md`.

## Estructura del proyecto

```text
.
├── AGENTS.md          # Instrucciones para agentes (este archivo)
├── CLAUDE.md          # Redirige a AGENTS.md
├── GEMINI.md          # Redirige a AGENTS.md
├── README.md          # Guía para personas usuarias
├── pyproject.toml     # Metadatos y dependencias (lo gestiona uv)
├── uv.lock            # Versiones exactas; se sube al repositorio
├── .python-version    # Versión de Python que usa uv (3.12)
├── docs/
│   ├── prd.md         # Especificación del producto
│   └── *.pdf          # Enunciado, rúbrica, pautas y plantillas del curso
└── src/
    ├── app.py         # Toda la app de Streamlit
    └── .env           # GEMINI_API_KEY local; NUNCA se sube a git
```

Si algún archivo aún no existe, créalo siguiendo esta estructura. No añadas
carpetas nuevas sin preguntar.

## Entorno de desarrollo (uv)

Usa SIEMPRE `uv` para Python y dependencias. No uses `pip`, `pip install`,
`python -m venv` ni `requirements.txt` para trabajar en local.

- Preparar el entorno (crea `.venv` e instala lo que dice `uv.lock`):

  ```bash
  uv sync
  ```

- Añadir una librería: `uv add <paquete>` (actualiza `pyproject.toml` y
  `uv.lock`). Para quitarla: `uv remove <paquete>`. Nunca edites `uv.lock` a
  mano.
- Ejecutar cualquier comando de Python dentro del entorno: `uv run <comando>`
  (no actives el `.venv` a mano).
- Arrancar la app en desarrollo, cargando la clave desde `src/.env`:

  ```bash
  uv run --env-file src/.env streamlit run src/app.py
  ```

  La app queda en <http://localhost:8501> y se recarga al guardar cambios.

## Reglas

- La clave de la API va SIEMPRE en secretos: variable de entorno
  `GEMINI_API_KEY` (en local, dentro de `src/.env`; en despliegue, en los
  secretos de la plataforma). Nunca en el código, en el README ni en el chat.
  No leas ni muestres el contenido de `src/.env`.
- `src/.env` y `.venv/` deben estar en `.gitignore`.
- Cada llamada a la API va dentro de `try/except` y muestra un mensaje claro
  para el usuario.
- Textos de la interfaz en español, sencillos, pensados para alguien sin
  conocimientos técnicos.
- Cambios pequeños: uno por petición. Al terminar, explica qué has cambiado
  y por qué.
- Si añades una librería, hazlo con `uv add` y dilo.
- No uses datos personales reales. Para probar, inventa ejemplos.

## Cómo comprobar que funciona

- Arranca la app con el comando de desarrollo de arriba y pruébala en el
  navegador.
- Casos de prueba (entrada → lo que esperamos):
  1. [entrada] → [respuesta esperada]
  2. [entrada] → [respuesta esperada]
  3. [entrada fuera de tema] → [la app dice amablemente que no puede ayudar
     con eso]

## Qué no hacer

- No borres ni reescribas el README sin preguntar.
- No cambies el modelo ni la arquitectura sin preguntar.
- No hagas push ni despliegues sin que yo lo haya revisado.
