# Arquitectura — Nutri-guía (fase DB + generador + UI)

Este documento define QUÉ se construye y CÓMO se acomodan las piezas. `SETUP.md` trae los pasos
de instalación, `VALIDATION.md` el contrato exacto de la lógica de negocio, `UI-BUILD-YOUR-MENU.md`
la interacción de la pantalla principal, y `BUILD-PLAN.md` el orden de ejecución. Este repo es de
uso personal (dos personas, 1-2 usuarios concurrentes como máximo) — las decisiones de abajo están
optimizadas para simplicidad de mantenimiento, no para escalar a muchos usuarios.

## Componentes

```
┌─────────────────────┐
│  SQLite (data/*.db)  │  ← fuente de verdad: catalogo_alimentos, recetas,
│                       │     objetivos, menus_construidos, asignacion_semanal,
│                       │     duplicados_descartados, personas
└──────────┬───────────┘
           │ sqlite3 (stdlib)
┌──────────┴───────────┐
│  nutriguia/ (paquete  │  ← lógica pura, sin UI: validation.py (reglas de equivalentes),
│  Python compartido)   │     db.py (conexión + funciones nombradas), import_data.py (carga inicial)
└──────────┬───────────┘
           │ import
┌──────────┴───────────┐
│  app.py (Streamlit)   │  ← "Menú del día": picker de recetas + stepper +/- por
│                       │     ingrediente + validación en vivo (verde/rojo por grupo)
└───────────────────────┘
```

La regla de oro: **toda la aritmética de equivalentes vive en `nutriguia/validation.py`**, un solo
módulo puro (sin dependencias de la base de datos ni de Streamlit) que tanto los tests, como el
import, como la UI importan. Nunca reimplementar la suma/comparación de equivalentes en otro lado
— eso es exactamente el tipo de bug silencioso que ya vimos en el histórico (declarados que no
cuadraban).

## Stack elegido y por qué

- **SQLite** (desde 2026-09-04, reemplaza a MongoDB — ver `BUGS.md` `KC-002` y `CHANGELOG.md`
  para el porqué del cambio: MongoDB 8.x sigue roto en kernels Linux ≥6.19 por un bug de
  TCMalloc/rseq sin fecha de fix, y el plan de distribuir EquiVale como app instalable en
  Windows/Linux hacía que depender de un servicio de base de datos aparte fuera la fricción
  equivocada). Un archivo único, sin servicio que instalar/mantener, incluido en la librería
  estándar de Python — corre igual en Windows/Linux/Mac. Cada tabla tiene columnas reales solo
  para lo que se usa como clave/filtro, más una columna `datos` con el resto del documento como
  JSON — `nutriguia/validation.py` ya son funciones puras que reciben/devuelven esos dicts
  anidados tal cual, así que no hace falta normalizar a tablas relacionales (no hay reportes ni
  queries analíticas que se beneficien de eso). `nutriguia/db.py` expone funciones nombradas por
  caso de uso real (`obtener_dia`, `guardar_receta`, `buscar_recetas_con_ingrediente`, ...) en vez
  de un ORM/shim genérico tipo Mongo.
- **Python** — mismo lenguaje que ya se usó para construir/validar todos los JSON históricos;
  reutilizar esa lógica es directo.
- **Streamlit** en vez de un backend API + frontend JS separados — para 1-2 usuarios, correr
  `streamlit run app.py` y acceder por navegador (vía túnel SSH o red local, o localmente en la
  propia máquina) es la opción de menor mantenimiento. Streamlit es reactivo por diseño: cambiar
  un stepper recalcula y repinta la validación sin que haya que escribir JS ni manejar estado de
  sesión a mano. Si el proyecto crece a "herramienta de nutriología para más gente", ahí sí se
  justifica separar en API (FastAPI, reusando `nutriguia/validation.py` tal cual) + frontend
  propio — pero no antes.
- **pytest** para validar `validation.py` contra TODOS los menús históricos ya reconciliados
  (deben dar 100% válidos — es la prueba de regresión más barata que existe, porque ya sabemos
  la respuesta correcta). Desde la migración a SQLite, `nutriguia/db.py` también tiene su propia
  cobertura (`tests/test_db.py`, contra `sqlite3.connect(":memory:")`) — con Mongo esto no era
  practicable sin una instancia viva.

## Estructura de carpetas del repo

```
nutri-guia/
  README.md
  CLAUDE.md
  ARCHITECTURE.md
  SETUP.md
  VALIDATION.md
  UI-BUILD-YOUR-MENU.md
  BUILD-PLAN.md
  CHANGELOG.md                     # qué cambió y cuándo, por versión (Keep a Changelog)
  BUGS.md                          # bugs/caveats/feature requests con detalle técnico
  schema.md
  .env.example
  requirements.txt
  SMAE_CONSULTA.csv                # tabla oficial SMAE (pública, sin datos de personas) --
                                    #   fuente de "Agregar de SMAE" en el editor de ingredientes
  .streamlit/
    config.toml                    # tema "Barro" (colores base) -- ver UI-BUILD-YOUR-MENU.md
  data/
    equivale.db                    # SQLite -- fuente de verdad en vivo (real, fuera de git)
    catalogo-alimentos.json
    recetas.json
    Json-outputs-sin-notas/        # menús históricos, solo para import/referencia (real, fuera de git)
    samples/                       # datos 100% ficticios, SÍ van en git — ver tests/test_validation_samples.py
  nutriguia/                       # paquete Python compartido (sin UI)
    __init__.py                    # __version__ (SemVer, ver CHANGELOG.md)
    db.py                          # conexión SQLite (lee SQLITE_PATH de .env) + funciones
                                    #   nombradas por colección (obtener_dia, guardar_receta, ...)
    validation.py                  # ver VALIDATION.md — contrato exacto
    colores.py                     # paleta fija por grupo SMAE (UI, no aritmética)
    cantidades.py                  # escalar_cantidad(): "30 g" x3 -> "90 g" (UI, no aritmética)
    estilo.py                      # CSS compartido "Barro" (fuentes, radios, sombras) -- se
                                    #   inyecta una vez desde app.py, ver UI-BUILD-YOUR-MENU.md
    smae_csv.py                    # lee SMAE_CONSULTA.csv, clasifica a los 7 grupos canónicos
                                    #   (UI, no aritmética -- usado por el editor de ingredientes)
    texto.py                       # normalizar_busqueda(): quita acentos/mayúsculas para buscar
    chequeos.py                    # detección de problemas de integridad (Configuración + badge)
    streamlit_data.py              # loaders cacheados compartidos entre páginas de Streamlit
    import_data.py                 # script: carga catalogo/recetas/personas/objetivos a SQLite
  app.py                           # entrypoint Streamlit: st.navigation entre las páginas de views/
  views/                           # páginas de la app multipágina (NO llamarla "pages/" — Streamlit
                                    #   auto-detecta esa carpeta para su mecanismo viejo de MPA y
                                    #   choca con st.navigation/st.Page, ver ARCHITECTURE.md abajo)
    menu_del_dia.py                # bitácora real: arma y guarda un día por fecha, con historial
    menu_semanal.py                # plantillas reutilizables por día de la semana + cobertura
    editor_recetas.py
    editor_ingredientes.py         # catálogo de alimentos: tabla + editar/eliminar + "Agregar de SMAE"
    personas.py
    configuracion.py               # admin: buscar relaciones + chequeos de integridad entre colecciones
    guia.py                        # ayuda: diagrama interactivo de relaciones + pasos para armar un menú
  tests/
    test_validation.py             # corre validation.py contra los menús históricos (skip si no hay datos reales)
    test_validation_samples.py     # mismo contrato, contra data/samples/ -- siempre corre, incluso en un clon público fresco
    test_db.py                     # nutriguia/db.py contra sqlite3.connect(":memory:")
    test_cantidades.py             # formatear_decimal_como_fraccion()
    test_smae_csv.py               # lectura/clasificación de SMAE_CONSULTA.csv (commiteado, corre en cualquier clon)
    test_texto.py                  # normalizar_busqueda()
```

## Decisiones de diseño ya tomadas (no re-derivar)

1. **`catalogo_alimentos` se aplana** al importar: un documento por alimento
   (`{alimento, grupo, cantidad_por_equivalente, asuncion}`), no el JSON anidado por grupo tal
   cual — más fácil de indexar/buscar por nombre. `import_data.py` hace esta transformación.
2. **Los menús históricos (`menus`) se importan tal cual, de solo lectura** — son el archivo/la
   prueba de que el sistema funciona, no se editan desde la UI.
3. **`recetas` se importa tal cual** desde `recetas.json` — es el banco de bloques de
   construcción para la UI y el generador. **Desde 2026-08-24 esto ya no es 100% cierto**: el
   Editor de recetas (`views/editor_recetas.py`) edita `recetas` en vivo en Mongo — esas ediciones
   NO se reflejan de vuelta en `recetas.json`. `import_data.py` ahora se niega a sobreescribir
   `recetas` si ya tiene datos, salvo `--force-recetas` explícito (que sí las destruiría). Tratar
   `recetas.json` como la semilla histórica inicial, no como la fuente de verdad continua.
4. **Aumentar/disminuir porción = pasos de 1 equivalente completo, nunca fracciones.** Ver
   `schema.md` (sección "ajuste de porción") y `VALIDATION.md` (función `paso_equivalente`) para
   el mecanismo exacto de cuánta `cantidad` real representa un paso, usando
   `catalogo_alimentos.cantidad_por_equivalente`.
5. **La validación es de signo explícito**: `delta = objetivo - actual` por grupo. Positivo =
   falta (te quedaste corto), negativo = sobra (te pasaste), cero = exacto. Ver `VALIDATION.md`.
6. **Las páginas multipágina de Streamlit viven en `views/`, nunca en una carpeta llamada
   `pages/`.** Encontrado 2026-08-24: si existe una carpeta `pages/` junto a `app.py`, Streamlit la
   auto-detecta con su mecanismo viejo de multipage (basado en archivos) además de/en conflicto con
   `st.navigation`/`st.Page` usado en `app.py` — al entrar por una URL directa a una subpágina
   (ej. refrescar o compartir el link de una página específica) se ve una barra lateral duplicada y
   rota, sin los títulos/iconos configurados. Renombrar la carpeta evita el conflicto por completo.
