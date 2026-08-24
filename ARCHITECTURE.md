# Arquitectura — Nutri-guía (fase DB + generador + UI)

Este documento define QUÉ se construye y CÓMO se acomodan las piezas. `SETUP.md` trae los pasos
de instalación, `VALIDATION.md` el contrato exacto de la lógica de negocio, `UI-BUILD-YOUR-MENU.md`
la interacción de la pantalla principal, y `BUILD-PLAN.md` el orden de ejecución. Este repo es de
uso personal (Dan y Pau, 1-2 usuarios concurrentes como máximo) — las decisiones de abajo están
optimizadas para simplicidad de mantenimiento, no para escalar a muchos usuarios.

## Componentes

```
┌─────────────────────┐
│   MongoDB (local)    │  ← fuente de verdad: catalogo_alimentos, recetas, menus,
│                       │     objetivos, menus_construidos
└──────────┬───────────┘
           │ pymongo
┌──────────┴───────────┐
│  nutriguia/ (paquete  │  ← lógica pura, sin UI: validation.py (reglas de equivalentes),
│  Python compartido)   │     db.py (conexión), import_data.py (carga inicial)
└──────────┬───────────┘
           │ import
┌──────────┴───────────┐
│  app.py (Streamlit)   │  ← "Build your menu": picker de recetas + stepper +/- por
│                       │     ingrediente + validación en vivo (verde/rojo por grupo)
└───────────────────────┘
```

La regla de oro: **toda la aritmética de equivalentes vive en `nutriguia/validation.py`**, un solo
módulo puro (sin dependencias de Mongo ni de Streamlit) que tanto los tests, como el import, como
la UI importan. Nunca reimplementar la suma/comparación de equivalentes en otro lado — eso es
exactamente el tipo de bug silencioso que ya vimos en el histórico (declarados que no cuadraban).

## Stack elegido y por qué

- **MongoDB** — ya era el plan original del usuario, encaja bien porque cada colección
  (`catalogo_alimentos`, `recetas`, `menus`, `objetivos`, `menus_construidos`) es un documento
  anidado autocontenido — no hay necesidad real de joins relacionales.
- **Python + pymongo** — mismo lenguaje que ya se usó para construir/validar todos los JSON
  históricos; reutilizar esa lógica es directo.
- **Streamlit** en vez de un backend API + frontend JS separados — para 1-2 usuarios, correr
  `streamlit run app.py` en la máquina Linux y acceder por navegador (vía túnel SSH o red local)
  es la opción de menor mantenimiento. Streamlit es reactivo por diseño: cambiar un stepper
  recalcula y repinta la validación sin que haya que escribir JS ni manejar estado de sesión a
  mano. Si el proyecto crece a "herramienta de nutriología para más gente", ahí sí se justifica
  separar en API (FastAPI, reusando `nutriguia/validation.py` tal cual) + frontend propio — pero
  no antes.
- **pytest** para validar `validation.py` contra TODOS los menús históricos ya reconciliados
  (deben dar 100% válidos — es la prueba de regresión más barata que existe, porque ya sabemos
  la respuesta correcta).

## Estructura de carpetas del repo

```
nutri-guia/
  CLAUDE.md
  ARCHITECTURE.md
  SETUP.md
  VALIDATION.md
  UI-BUILD-YOUR-MENU.md
  BUILD-PLAN.md
  schema.md
  .env.example
  requirements.txt
  data/
    catalogo-alimentos.json
    recetas.json
    Json-outputs-sin-notas/        # menús históricos, solo para import/referencia
  nutriguia/                       # paquete Python compartido (sin UI)
    __init__.py
    db.py                          # conexión a Mongo (lee MONGO_URI de .env)
    validation.py                  # ver VALIDATION.md — contrato exacto
    import_data.py                 # script: carga catalogo/recetas/menus/objetivos a Mongo
  app.py                           # Streamlit — "build your menu" (ver UI-BUILD-YOUR-MENU.md)
  tests/
    test_validation.py             # corre validation.py contra los menús históricos
    test_import.py                 # smoke test: conteos esperados tras importar
```

## Decisiones de diseño ya tomadas (no re-derivar)

1. **`catalogo_alimentos` se aplana** al importar: un documento por alimento
   (`{alimento, grupo, cantidad_por_equivalente, asuncion}`), no el JSON anidado por grupo tal
   cual — más fácil de indexar/buscar por nombre. `import_data.py` hace esta transformación.
2. **Los menús históricos (`menus`) se importan tal cual, de solo lectura** — son el archivo/la
   prueba de que el sistema funciona, no se editan desde la UI.
3. **`recetas` se importa tal cual** desde `recetas.json` — es el banco de bloques de
   construcción para la UI y el generador.
4. **Aumentar/disminuir porción = pasos de 1 equivalente completo, nunca fracciones.** Ver
   `schema.md` (sección "ajuste de porción") y `VALIDATION.md` (función `paso_equivalente`) para
   el mecanismo exacto de cuánta `cantidad` real representa un paso, usando
   `catalogo_alimentos.cantidad_por_equivalente`.
5. **La validación es de signo explícito**: `delta = objetivo - actual` por grupo. Positivo =
   falta (te quedaste corto), negativo = sobra (te pasaste), cero = exacto. Ver `VALIDATION.md`.
