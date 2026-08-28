# EquiVale (nutri-guía) — contexto para Claude Code

Sistema de planes de alimentación basado en equivalentes nutricionales SMAE (Sistema Mexicano de
Alimentos Equivalentes), para dos personas: **Persona A** y **Persona B** (uso personal, 1-2
usuarios concurrentes como máximo — no se está construyendo para escalar a muchos usuarios).
Nombre del proyecto: **EquiVale** (repo `glafe/equivale` en GitHub — el código es público, los
datos reales de nutrición/menús viven solo en Mongo y fuera de git, ver `.gitignore` y `SETUP.md`).
Esta fase del proyecto es: instalar MongoDB, cargar los menús ya reconciliados, y construir una app
Streamlit ("build your menu") donde el usuario arma su día eligiendo recetas de un banco y
ajustando porciones en pasos de equivalente completo, con validación en vivo de qué le falta o le
sobra.

La fase anterior (parsear Excels/ODS desordenados hacia JSON) ya terminó — este documento y los de
abajo son contexto de generación/DB/UI, no el historial de esa reconciliación (esas notas viven
fuera del repo, no en control de versiones).

## Estado actual (actualizar esta sección al final de cada sesión de trabajo)

**Versión:** `0.5.2` (ver `nutriguia/__init__.py` y `CHANGELOG.md`) · **Última commit:** correr
`git log -1 --oneline` para el hash exacto — no se repite aquí para no quedar desactualizado.
**Nota:** `0.5.2` (checkbox opt-in en el editor de ingredientes para también quitar un alimento
eliminado de las recetas que lo usaban, no solo del catálogo — ver `CHANGELOG.md`) se hizo desde
otra sesión/interfaz en paralelo a esta misma — ya está commiteada, pusheada y desplegada; no es
un cambio pendiente de esta sesión.

Al 2026-08-27: **Fases 0 a 4 completas** (ver checklist en `BUILD-PLAN.md`) — Mongo corriendo,
datos importados, `nutriguia/validation.py` con 35/35 tests en verde (más suites adicionales
sobre datos sintéticos/públicos que corren en cualquier clon del repo — `tests/
test_validation_samples.py`, `test_cantidades.py`, `test_smae_csv.py`, `test_texto.py`, 51/51 en
total, ver más abajo), app Streamlit multipágina ("Build your menu", "Editor de recetas", "Editor
de ingredientes", "Personas") corriendo en producción. "Build your menu" ya cubre el día completo
(los 5 tiempos vía tabs), guarda por `(persona, fecha)` en `menus_construidos`, y tiene historial
de planes guardados con round-trip verificado. El "Editor de ingredientes" (2026-08-27) permite
limpiar/fusionar el catálogo de alimentos (con cascada de renombrado a `recetas`) y agregar
alimentos nuevos desde `SMAE_CONSULTA.csv` (commiteado al repo — ver "Editor de ingredientes" en
`UI-BUILD-YOUR-MENU.md`). Falta Fase 5 (pulido) — no empezarla sin haber usado la Fase 4 unos
días en la vida real.

**Identidad visual "Barro" (2026-08-27)**: paleta/tipografía/radios propios sobre los 7 colores
de grupo SMAE (que NO cambiaron — son funcionales). Aprobada primero como maqueta interactiva
(artefacto fuera del repo) antes de tocar código. Implementada en `.streamlit/config.toml` +
`nutriguia/estilo.py` (inyectado una vez desde `app.py`), con las filas de ingrediente
reestructuradas en `views/build_your_menu.py` y `views/editor_recetas.py` para verse bien también
en teléfono (Streamlit apila `st.columns` bajo ~640px). Detalle completo, incluida la convención
de `key=` para CSS dirigido (`menos_`/`mas_`/`receta_card_`/`status_`), en `UI-BUILD-YOUR-MENU.md`
→ "Identidad visual Barro y responsividad". Verificado en vivo (escritorio + viewport de
teléfono) vía Playwright contra el servidor — ver [[feedback-playwright-fullpage]] en memoria si
vuelves a hacer esto: `full_page=True` de Playwright NO captura toda la página en esta app
(`document.body.scrollHeight` da 0, el scroll real es de un contenedor interno) — hay que hacer
`scroll_into_view_if_needed()` al elemento que te interesa antes de la captura, o vas a
"encontrar" bugs que en realidad solo están fuera del viewport.

**Desde 2026-08-27 el proyecto lleva versión (SemVer) y changelog** — ver `CHANGELOG.md` (qué
cambió y cuándo, por versión) y `BUGS.md` (bugs/caveats/feature requests con detalle técnico,
templates en `Prompt-Coding_Best_Practices-main/practices-and-principles.md` — carpeta de
referencia externa, fuera de git). Mensajes de commit desde esa fecha usan prefijo
`feat:`/`fix:`/`docs:`/`refactor:`/`test:`/`chore:`; los commits anteriores no se reescriben.
Al cerrar un bug o feature, agregar una línea a `CHANGELOG.md` con el ID de `BUGS.md`. No se
adoptó un `AGENTS.md` separado ni el layout `src/` de esa referencia — este repo ya tiene un
único asistente (Claude Code) y una documentación de dominio (`CLAUDE.md` + los `.md` listados
abajo) que cumple el mismo rol; reestructurar carpetas en un repo ya desplegado (rutas de
systemd, `SETUP.md`, etc.) no se justificaba solo por seguir la convención al pie de la letra.

El repo se hizo público el 2026-08-27 — se reescribió toda la historia de git para purgar datos
reales (ver nota de privacidad arriba); `data/` y `scripts/migraciones/` ya no viajan con
`git clone`, viven fuera de git.

El banco de `recetas` ya no tiene 159 documentos como en la importación original — se dedupicó por
nombre el 2026-08-25 y quedó en 97 (ver regla 9 abajo y `scripts/migraciones/`), y una segunda
pasada el mismo día (nombres solo parecidos, no exactos — ver regla 9 nivel 2) la dejó en 86. Es
normal y esperado que el conteo en vivo de Mongo no coincida con el de `recetas.json`;
`import_data.py` protege contra que un re-import accidental lo revierta (ver `ARCHITECTURE.md`).

**La app YA está desplegada y corriendo** en un servidor Linux (Ubuntu 24.04) en la red local del
usuario, como servicio systemd — no hay que "levantarla" de cero. Ver `SETUP.md` sección final para
la IP, cómo redesplegar cambios (`git pull` + `systemctl restart`), y gotchas ya resueltos (una
incompatibilidad de kernel que le impedía arrancar a Mongo). Antes de asumir que hay que reinstalar
algo desde cero, revisar si ya existe y solo necesita un redeploy.

## Índice de documentos — leer en este orden

1. **Este archivo (`CLAUDE.md`)** — contexto de dominio: personas, grupos SMAE, convenciones.
2. **`ARCHITECTURE.md`** — componentes del sistema, stack elegido y por qué, estructura de carpetas.
3. **`SETUP.md`** — pasos concretos de instalación (MongoDB, Python, `.env`) en la máquina Linux.
4. **`schema.md`** — forma exacta de cada colección de Mongo (`catalogo_alimentos`, `menus`,
   `recetas`, `objetivos`, `menus_construidos`).
5. **`VALIDATION.md`** — contrato exacto del módulo `nutriguia/validation.py` (toda la aritmética
   de equivalentes vive ahí, en un solo lugar).
6. **`UI-BUILD-YOUR-MENU.md`** — especificación de interacción de la app Streamlit.
7. **`BUILD-PLAN.md`** — orden de ejecución por fases, con criterio de "hecho" en cada una. **Este
   es el punto de entrada para empezar a trabajar** — sigue sus fases en orden.
8. **`CHANGELOG.md`** — qué cambió y cuándo, por versión (formato Keep a Changelog).
9. **`BUGS.md`** — bugs/caveats/feature requests con detalle técnico (bugs ya resueltos, límites
   conocidos que no son bugs, e ideas pendientes con su justificación).

## Personas (canónico)

Los nombres reales de las dos personas viven solo en Mongo (`personas.persona`, y como valor de
`persona`/`personas_vistas` en `menus`/`recetas`/`objetivos`) y fuera de este repo público — acá se
habla de **Persona A** y **Persona B** como placeholders genéricos.

- **Persona A** — un solo persona_id. Los archivos de origen usaban a veces una variante del nombre
  como tab de Excel, pero el campo `persona` en TODO el JSON ya está normalizado a un solo valor.
- **Persona B** — persona distinta, propio set de archivos y objetivos de equivalentes diarios
  (generalmente ~12-14 AOA/día vs. ~13-15 de Persona A — varía por periodo, no asumir un valor
  fijo).

No hay terceras personas. No inventar un persona_id nuevo sin que el usuario lo pida.

**Nota de privacidad (repo público desde 2026-08-27)**: los nombres reales, valores concretos de
objetivos/porciones, y cualquier dato nutricional específico de cada persona NO se escriben en
estos documentos de diseño — viven solo en Mongo (privado) y en archivos fuera de git (ver
`.gitignore`). Estos documentos hablan en términos genéricos (Persona A/Persona B, "el objetivo de
esa persona") a propósito. Si haces un cambio que involucre valores reales, ponlos en Mongo/el
`.env`/un archivo ignorado — no en un `.md` que se commitea.

**Excepción explícita — `SMAE_CONSULTA.csv`**: es la tabla oficial pública del sistema SMAE
(equivalentes nutricionales genéricos por alimento), sin ningún dato de las personas que usan
esta app — sí vive en git a propósito desde 2026-08-27 (ver `.gitignore`). No confundir con los
archivos de `data/` (menús/recetas/objetivos reales), que siguen fuera de git.

## Los 7 grupos SMAE (canónico)

`AOA`, `Cereal`, `Verdura`, `Fruta`, `Aceite s/p`, `Aceite c/p`, `Leguminosa`.

Ojo: dos de los archivos de origen (uno por persona, periodo junio) originalmente usaban
`"Legumin"` en vez de `"Leguminosa"` — ya normalizado. Si aparece `"Legumin"` en cualquier dato
nuevo, es el mismo grupo y se debe guardar como `"Leguminosa"`.

`Leguminosa` es intercambiable con `Cereal` en algunos periodos (campo `grupos_intercambiables`,
ver schema.md) — al generar un menú nuevo, un platillo puede satisfacer su cuota de Cereal usando
Leguminosa o viceversa, si el periodo lo declara así.

## Fuente de verdad para conversiones: `catalogo-alimentos.json`

Antes de inventar cuántos gramos/tazas de un alimento equivalen a 1 porción SMAE, **consultar este
catálogo primero**. Si el alimento no está, es candidato a agregarse (con el mismo formato:
`{"alimento": "...", "cantidad_por_equivalente": "..."}`, opcionalmente `"asuncion": true` +
`"nota"` si no hay dato exacto confirmado).

El catálogo trae dos archivos gemelos:
- `data/Json-outputs/catalogo-alimentos.json` — versión completa con notas de por qué se decidió
  cada valor (útil para auditoría/histórico, NO para generación).
- `data/Json-outputs-sin-notas/catalogo-alimentos.json` — mismos datos, sin los campos
  `nota`/`_nota*`. **Usar esta versión como contexto de trabajo día a día** — es ~45% más chica y
  no tiene prosa explicativa que no aporta a la generación.

## Generar menús nuevos: usar el banco de recetas, no inventar desde cero

`data/recetas.json` trae 159 platillos reales, ya cocinados en algún menú anterior de alguna de las
dos personas, cada uno con su `vector_equivalentes` ya calculado (suma por grupo_smae). Generar un
menú nuevo es un problema de encontrar combinaciones de recetas cuyo vector sume el objetivo del
tiempo/día — resolver esto con un solver determinístico (Python), no pidiéndole a un modelo que
haga la aritmética en texto. El LLM sirve para elegir entre candidatos válidos (variedad, qué no
se ha repetido), no para calcular las sumas. Ver `schema.md` → sección `recetas` para el detalle.
Solo si el banco no tiene ninguna combinación que cuadre con un objetivo específico vale la pena
generar un platillo nuevo desde el catálogo — y ahí sí aplican las reglas de abajo.

## Reglas para construir/validar un platillo (nuevo o del banco)

1. Cada `ingrediente` tiene un `grupo_smae` (uno de los 7 de arriba) y un `equivalentes` (entero,
   casi siempre — ver excepción de "2 V" abajo).
2. La suma de `equivalentes` de los ingredientes de un `tiempo`, agrupada por `grupo_smae`, debe
   igualar exactamente la lista `equivalentes` declarada de ese tiempo.
3. La suma de los `equivalentes` de todos los tiempos de un `menu`, agrupada por grupo, debe
   igualar `equivalentes_diarios` de ese menú.
4. Cada persona/periodo suele tener 2 variantes de menú (`menu_id: 1` y `2`, para días alternos —
   ver `dias` en cada uno). Ambos menús normalmente apuntan a los mismos objetivos diarios totales,
   aunque no es una regla estricta (revisar el periodo específico).
5. Antes de fijar la cantidad de un alimento, buscarlo en `catalogo-alimentos.json`. Si no está,
   buscar en `SMAE_CONSULTA.csv` (tabla oficial SMAE completa, commiteada al repo desde
   2026-08-27 — es información pública, no de personas reales, ver nota de privacidad; también
   disponible desde la app en "Editor de ingredientes" → "Agregar de SMAE"). Si tampoco está ahí,
   marcar `"asuncion": true` y explicar en `"nota"` el criterio usado (no inventar sin dejarlo
   señalado).
6. Placeholder literal: un ingrediente `"Fruta"` o `"Fruta suelta"` con `cantidad: "1"` y sin
   alimento específico = 1 Fruta libre a elección de la persona. No tratarlo como si le faltara
   nombre.
7. Notación `"N V"` (ej. `"2 V"`) en el campo `cantidad` = N equivalentes de Verdura directo, sin
   cantidad medida — no intentar convertirlo a tazas/gramos.
8. Al reutilizar un platillo ya existente para la otra persona (ej. adaptar un platillo de Persona A
   para Persona B), no asumir que el `equivalentes` declarado se ajustó correctamente solo porque
   la porción cambió — validar la suma real contra los ingredientes.
9. **Criterio para fusionar recetas "duplicadas" del banco** — dos niveles, según si el `nombre`
   coincide exacto o solo se parece:
   - **Mismo `nombre` exacto** (normalizado sin distinguir mayúsculas/espacios): fusionar siempre,
     de forma mecánica (usado 2026-08-25, ver `scripts/migraciones/2026-08-25-fusionar-recetas-por-
     nombre.py` — 156→97 recetas). Un ingrediente presente en TODAS las variantes de ese nombre se
     mantiene fijo (ajustable con el stepper como siempre); uno presente solo en ALGUNAS se marca
     `Ingrediente.opcional` (ver `schema.md`) — esto también cubre "ingrediente A en una variante,
     alternativa B en otra" (ej. papa vs arroz): ambos quedan opcionales independientes, y el
     usuario incluye uno/excluye el otro en "Build your menu" para reconstruir la variante que
     quiera. Conocido efecto secundario menor: si el mismo alimento real aparece escrito distinto
     entre variantes (ej. "Atún" vs "Atún en agua", "Proteína" vs "Proteína en polvo"), el script no
     los reconoce como el mismo ingrediente y quedan como dos opcionales separados en vez de uno —
     no se persiguió exhaustivamente, corregible a mano desde el Editor si se nota al usar la app.
   - **Nombres solo parecidos, no exactos** (usado 2026-08-24 en "filete de pescado", y de nuevo el
     2026-08-25 en una pasada más amplia — ver `scripts/migraciones/2026-08-25-unificar-recetas-
     similares.py`, 95→86 recetas): NO fusionar automático — solo si de verdad es el mismo platillo
     (misma proteína/base, difiere una porción o un ingrediente extra) se fusiona igual que arriba.
     Si la diferencia real es el carbohidrato o la verdura base (ej. papa vs arroz, nopales vs
     mezcla de verdura — caso de "filete de pescado", se dejó igual en la pasada del 2026-08-25), son
     platillos distintos aunque se llamen parecido — mejorar el `nombre` de cada uno para
     desambiguar en el picker, no fusionar. Fusionados el 2026-08-25: "Ceviche de atún" (+ variante
     "Salmas"), "Espagueti Boloñesa" (+ variante "Uvas"), "Fajitas de pollo con papas" (dos
     gramajes de pollo, uno por persona), "Jícama o Zanahoria" (+ variantes Tajín/rallada/Manzana), "Huevos
     duros con zanahoria" (+ variante pepino), "Omelet de champiñones", "Manzana". Se renombró
     "Fajitas de Pollo" (con tortilla) a "Fajitas de pollo con tortilla" para no confundirse con la
     recién fusionada "Fajitas de pollo con papas". La misma pasada también corrigió ~16 casos del
     efecto secundario de ingrediente-con-ortografía-distinta descrito abajo (ej. "Aceite de oliva"
     / "Aceite oliva", "Tortilla de maíz" / "Tortilla maíz") — sigue sin perseguirse exhaustivamente
     en el resto del banco, solo se corrigió donde se detectó.

## Dónde vive cada cosa

- `data/Json-outputs/` — JSON final por persona/periodo, con notas de auditoría/decisiones. Nombre
  de archivo: `{Persona}{Periodo}.json` o `{Periodo}-{Persona}.json` (la convención de nombre no es
  100% uniforme entre archivos viejos y nuevos — no depender del nombre de archivo para saber la
  persona/periodo, siempre leer los campos `persona` y `periodo` del JSON).
- `data/Json-outputs-sin-notas/` — mismos archivos sin campos de nota. Preferir esta carpeta como
  fuente para poblar MongoDB y como contexto de trabajo — es la más liviana.
- `data/recetas.json` — banco de 159 platillos reutilizables extraídos de los menús históricos,
  cada uno con su vector de equivalentes ya calculado. Punto de partida para generar menús nuevos.
- `schema.md` — forma exacta de cada colección/documento. Leer antes de generar o validar un menú.
- `scripts/migraciones/` — registro histórico de cambios hechos directo en Mongo (ej. fusiones de
  recetas duplicadas) — Mongo no tiene git, así que estos scripts documentan qué cambió y por qué.
  No están diseñados para volver a correrse.

## Convenciones para la base de datos (MongoDB)

Colecciones: `personas`, `catalogo_alimentos`, `recetas`, `menus`, `objetivos`,
`menus_construidos`. Ver `schema.md` para la forma exacta de cada documento — incluye las dos
colecciones nuevas de esta fase (`objetivos` y `menus_construidos`, para la app "build your
menu"). Índices recomendados: `menus` → compuesto `(persona, periodo, menu_id)`; `recetas` →
`tiempo_tipico` y `vector_equivalentes.<grupo>`; `catalogo_alimentos` → único sobre `alimento`;
`menus_construidos` → único compuesto `(persona, fecha)` (una persona no puede tener dos planes
guardados para la misma fecha — se sobreescribe, no se duplica; el índice se crea perezosamente
desde `views/build_your_menu.py` al primer guardado, no desde `import_data.py`).

No commitear credenciales de conexión a Mongo — usar `.env` fuera de git (ver `SETUP.md`).

## Empezar a trabajar

No improvisar el orden — seguir `BUILD-PLAN.md` fase por fase. Cada fase tiene un criterio de
"hecho" explícito antes de pasar a la siguiente. Si algo no está claro en estos documentos,
preguntarle al usuario en vez de asumir — son documentos de diseño, no una especificación
exhaustiva de cada decisión posible.
