# Nutri-guía — contexto para Claude Code

Sistema de planes de alimentación basado en equivalentes nutricionales SMAE (Sistema Mexicano de
Alimentos Equivalentes), para dos personas: **Dan** y **Pau** (uso personal, 1-2 usuarios
concurrentes como máximo — no se está construyendo para escalar a muchos usuarios). Esta fase del
proyecto es: instalar MongoDB, cargar los menús ya reconciliados, y construir una app Streamlit
("build your menu") donde el usuario arma su día eligiendo recetas de un banco y ajustando
porciones en pasos de equivalente completo, con validación en vivo de qué le falta o le sobra.

La fase anterior (parsear Excels/ODS desordenados hacia JSON) ya terminó — este documento y los de
abajo son contexto de generación/DB/UI, no el historial de esa reconciliación (para eso ver
`agosto26-dan-notas.md` en el Project).

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
