# EquiVale (nutri-guía) — contexto para Claude Code

Sistema de planes de alimentación basado en equivalentes nutricionales SMAE (Sistema Mexicano de
Alimentos Equivalentes), para dos personas: **Dan** y **Pau** (uso personal, 1-2 usuarios
concurrentes como máximo — no se está construyendo para escalar a muchos usuarios). Nombre del
proyecto: **EquiVale** (repo privado `glafe/equivale` en GitHub). Esta fase del proyecto es:
instalar MongoDB, cargar los menús ya reconciliados, y construir una app Streamlit ("build your
menu") donde el usuario arma su día eligiendo recetas de un banco y ajustando porciones en pasos de
equivalente completo, con validación en vivo de qué le falta o le sobra.

La fase anterior (parsear Excels/ODS desordenados hacia JSON) ya terminó — este documento y los de
abajo son contexto de generación/DB/UI, no el historial de esa reconciliación (para eso ver
`agosto26-dan-notas.md` en el Project).

## Estado actual (actualizar esta sección al final de cada sesión de trabajo)

Al 2026-08-25: **Fases 0 a 3.5 completas** (ver checklist en `BUILD-PLAN.md`) — Mongo corriendo,
datos importados, `nutriguia/validation.py` con 35/35 tests en verde, app Streamlit multipágina
("Build your menu" + "Editor de recetas") corriendo en producción. Falta Fase 4 (día completo +
guardado a `menus_construidos`) en adelante.

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

## Personas (canónico)

- **`"Dan"`** — un solo persona_id. Los archivos de origen usaban a veces "Dany" como nombre del tab
  de Excel, pero el campo `persona` en TODO el JSON ya está normalizado a `"Dan"`.
- **`"Pau"`** — persona distinta, propio set de archivos y objetivos de equivalentes diarios
  (generalmente ~12-14 AOA/día vs. ~13-15 de Dan — varía por periodo, no asumir un valor fijo).

No hay terceras personas. No inventar un persona_id nuevo sin que el usuario lo pida.

## Los 7 grupos SMAE (canónico)

`AOA`, `Cereal`, `Verdura`, `Fruta`, `Aceite s/p`, `Aceite c/p`, `Leguminosa`.

Ojo: dos archivos (Junio26-Dany.json, PauJunio26.json) originalmente usaban `"Legumin"` en vez de
`"Leguminosa"` — ya normalizado. Si aparece `"Legumin"` en cualquier dato nuevo, es el mismo grupo
y se debe guardar como `"Leguminosa"`.

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

`data/recetas.json` trae 159 platillos reales, ya cocinados en algún menú anterior de
Dan o Pau, cada uno con su `vector_equivalentes` ya calculado (suma por grupo_smae). Generar un
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
   buscar en `SMAE_CONSULTA.csv` (tabla oficial SMAE completa) si ese archivo está disponible en el
   repo. Si tampoco está ahí, marcar `"asuncion": true` y explicar en `"nota"` el criterio usado
   (no inventar sin dejarlo señalado).
6. Placeholder literal: un ingrediente `"Fruta"` o `"Fruta suelta"` con `cantidad: "1"` y sin
   alimento específico = 1 Fruta libre a elección de la persona. No tratarlo como si le faltara
   nombre.
7. Notación `"N V"` (ej. `"2 V"`) en el campo `cantidad` = N equivalentes de Verdura directo, sin
   cantidad medida — no intentar convertirlo a tazas/gramos.
8. Al reutilizar un platillo ya existente para la otra persona (ej. adaptar un platillo de Dan para
   Pau), no asumir que el `equivalentes` declarado se ajustó correctamente solo porque la porción
   cambió — validar la suma real contra los ingredientes.
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
     gramajes de pollo, Dan/Pau), "Jícama o Zanahoria" (+ variantes Tajín/rallada/Manzana), "Huevos
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
`tiempo_tipico` y `vector_equivalentes.<grupo>`; `catalogo_alimentos` → único sobre `alimento`.

No commitear credenciales de conexión a Mongo — usar `.env` fuera de git (ver `SETUP.md`).

## Empezar a trabajar

No improvisar el orden — seguir `BUILD-PLAN.md` fase por fase. Cada fase tiene un criterio de
"hecho" explícito antes de pasar a la siguiente. Si algo no está claro en estos documentos,
preguntarle al usuario en vez de asumir — son documentos de diseño, no una especificación
exhaustiva de cada decisión posible.
