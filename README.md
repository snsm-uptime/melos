# [Nombre de la app]

**Enlace a la app:** [https://...streamlit.app o https://...hf.space]
**Autor/a:** [vuestro nombre]

## Pitch

[Cinco frases: el problema y quién lo tiene, qué hace la app, qué aporta la
IA, qué aprendisteis de la prueba y qué haríais después, con un dato o un
ejemplo.]

## El problema

10/16/26, 12:33 AMDocumento
Page 5 of 13<https://learn.obsbusiness.school/ultra/courses/_248910_1/document/_11288207_1?view=content&state=view>
[Quién tiene el problema, cómo lo resuelve hoy y por qué merece la pena
resolverlo. 3 o 4 frases.]

## Qué hace la app

[Qué puede hacer el usuario, paso a paso.]

## La pieza de IA

- **Qué usa:** [API de Gemini con el modelo ..., un modelo de Hugging Face ...,
un RAG sobre ...]
- **Por qué esa opción:** [una o dos frases]
- **Qué pasa si falla:** [cómo responde la app si se acaba la cuota o no hay
conexión]

## Cómo la he construido

- **Herramientas:** [Gemini en Colab, Copilot, Cursor, Claude Code, Codex,
Gemini CLI...]
- **Fichero de contexto del agente:** [enlace a vuestro AGENTS.md, CLAUDE.md
o GEMINI.md]
- **Prompts clave:** [los 3 a 5 prompts que más han servido, copiados tal
cual]
- **Qué delegué al agente y qué revisé a mano:** [ejemplos concretos]

## Prueba y mejora

| Quién la probó | Qué probó | Qué pasó | Qué cambié |
|---|---|---|---|
| [un compañero, o yo como usuario] | | | |

## Ejecutar en local (opcional)

```bash
pip install -r requirements.txt
# Ruta A: poned la clave en .streamlit/secrets.toml y ejecutad
streamlit run app.py
# Ruta B: exportad la clave y ejecutad
export GEMINI_API_KEY="..." && python app.py
```

## Capturas

10/16/26, 12:33 AMDocumento
Page 6 of 13<https://learn.obsbusiness.school/ultra/courses/_248910_1/document/_11288207_1?view=content&state=view>
[La app funcionando, la app ante un caso límite, un momento de vuestro
trabajo con la IA y la prueba. Sin ninguna clave a la vista.]
