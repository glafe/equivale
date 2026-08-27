# Schema — Nutri-guía

Forma de los documentos usados en este proyecto. Basado en los archivos ya entregados en
`Json-outputs-sin-notas/`. Los tipos son JSON/Mongo (string, int, bool, array, object). Para las
reglas de construcción del proyecto (arquitectura, instalación, UI), ver `ARCHITECTURE.md`,
`SETUP.md`, `VALIDATION.md`, `UI-BUILD-YOUR-MENU.md`, `BUILD-PLAN.md`.

## Colección `catalogo_alimentos` — un documento por alimento (aplanado en Mongo)

Fuente del archivo: `catalogo-alimentos.json` (anidado por grupo). **Decisión ya tomada**: al
importar a Mongo se aplana a un documento por alimento — más fácil de indexar/buscar por nombre,
y es lo que usa `paso_equivalente()` (ver `VALIDATION.md`) para saber cuánto vale un paso del
stepper en la UI.

Forma del documento en Mongo (colección `catalogo_alimentos`):
```
{
  "alimento": string,                  // nombre canónico, ej. "Pollo"
  "grupo": string,                     // uno de los 7 grupos canónicos (ver abajo)
  "cantidad_por_equivalente": string,  // ej. "1/2 taza", "30 g", "10 piezas"
  "asuncion"?: bool                    // true = sin dato exacto confirmado, se infirió
}
```
Índice recomendado: único sobre `alimento`.

Forma del archivo fuente (`catalogo-alimentos.json`, tal como llega, antes de aplanar):
```
{
  "fuente_referencia": string,
  "grupos": {
    "AOA": [ CatalogoEntry, ... ],
    "Cereal": [ CatalogoEntry, ... ],
    "Verdura": [ CatalogoEntry, ... ],
    "Fruta": [ CatalogoEntry, ... ],
    "Aceite s/p": [ CatalogoEntry, ... ],
    "Aceite c/p": [ CatalogoEntry, ... ],
    "Leguminosa": [ CatalogoEntry, ... ]
  },
  "libres": {
    "alimentos": [ { "alimento": string, "nota"?: string }, ... ]
  }
}
```
`CatalogoEntry` = `{ "alimento": string, "cantidad_por_equivalente": string, "asuncion"?: bool }`.
`libres.alimentos` = alimentos que NO cuentan como ningún equivalente SMAE (cantidad libre/al
gusto) — no se aplanan a `catalogo_alimentos` (no tienen grupo); si se quiere consultarlos desde
la app, importarlos aparte o como una lista simple embebida en config.

Los 7 nombres de `grupos` son fijos y canónicos — no crear grupos nuevos sin confirmar con el
usuario: `AOA`, `Cereal`, `Verdura`, `Fruta`, `Aceite s/p`, `Aceite c/p`, `Leguminosa`.
`"Leguminosa"` es el nombre correcto (no usar `"Legumin"`).

## Colección `menus` — histórico, de solo lectura (un documento por persona + periodo)

```
{
  "persona": string,               // persona_id canónico, sin variantes (ver colección `personas`)
  "periodo": string,                // "YYYY-MM", ej. "2026-06"
  "tab_origen": string,             // nombre del tab de Excel de origen (histórico/auditoría)
  "sistema_referencia": "SMAE",
  "fase": string,                   // ej. "mantenimiento"
  "grupos_intercambiables"?: [ [string, string], ... ],
    // ej. [["Leguminosa","Cereal"]] — presente solo en periodos donde el nutriólogo declaró
    // que un grupo puede cubrir la cuota de otro. Opcional — ausente en la mayoría de periodos.
  "equivalentes_diarios_indicados"?: [ EquivalenteGrupo, ... ],
    // objetivo diario "oficial" indicado por el nutriólogo para la persona, independiente de
    // menu_id. Solo presente en tabs de la serie 2026 (Marzo26, Junio26). Opcional. Es la fuente
    // por default para poblar la colección `objetivos` (ver abajo) — confirmar con el usuario.
  "menus": [ MenuVariante, MenuVariante ]   // normalmente 2 variantes (días alternos)
}
```

**MenuVariante**:
```
{
  "menu_id": int,                   // 1 o 2
  "dias": [string, ...],            // ej. ["lunes","miercoles","viernes"]
  "equivalentes_diarios": [ EquivalenteGrupo, ... ],  // debe = suma de "equivalentes" de "tiempos"
  "tiempos": [ Tiempo, ... ]
}
```

**EquivalenteGrupo**: `{ "grupo": string, "cantidad": int }` — nota: el mismo `grupo` puede
aparecer más de una vez en la misma lista (ej. dos entradas de `"Cereal"`); al sumar, agregar por
clave, NO usar un dict/objeto que sobreescriba duplicados (ver `sumar_por_grupo()` en
`VALIDATION.md`).

**Tiempo**:
```
{
  "tiempo": string,                 // "al_despertar" | "desayuno" | "colacion" | "comida" | "cena"
  "icono": string,                  // emoji, ej. "🌅"
  "equivalentes": [ EquivalenteGrupo, ... ],   // debe = suma de "equivalentes" de "platillos.ingredientes", agrupado por grupo_smae
  "platillos": [ Platillo, ... ]
}
```

**Platillo**: `{ "nombre": string, "ingredientes": [ Ingrediente, ... ] }`

**Ingrediente**:
```
{
  "cantidad": string,               // ej. "1/2 taza", "150 g", "2 pza", "2 V" (shorthand, ver CLAUDE.md)
  "alimento": string,
  "grupo_smae": string | null,      // uno de los 7 grupos canónicos, o null si no cuenta (libre)
  "equivalentes": int,
  "asuncion"?: bool,
  "bloqueado"?: bool,                // ver nota abajo — solo aplica dentro de `recetas`, no en `menus`
  "opcional"?: bool,                 // ver nota abajo — solo aplica dentro de `recetas`, no en `menus`
  "nota"?: string                   // presente solo en Json-outputs/ (no en -sin-notas/)
}
```

**`bloqueado`** (agregado 2026-08-24 para el editor de recetas — solo relevante en la colección
`recetas`, los `Ingrediente` de `menus` son histórico de solo lectura y lo ignoran): por default,
si un `alimento` tiene `cantidad_por_equivalente` en `catalogo_alimentos` es ajustable con el
stepper +/- en "Build your menu" (ver `paso_equivalente()` en `VALIDATION.md`). `bloqueado: true`
fuerza a que NO sea ajustable aunque el catálogo sí resuelva un paso — para ingredientes que el
usuario decide fijos en una receta concreta (ej. una guarnición base que no debería tocarse).
Ausente o `false` = se comporta según el catálogo (default, sin cambios).

**`opcional`** (agregado 2026-08-24, mismo alcance que `bloqueado` — solo `recetas`): marca un
ingrediente que no siempre forma parte del platillo — ej. un extra de queso que algunas veces se
agrega y otras no. En "Build your menu", un ingrediente `opcional: true` se agrega con un checkbox
**Incluir** (default: incluido, para que la receta reproduzca su versión más completa salvo que el
usuario decida quitarlo) — si se desmarca, no cuenta en la suma de equivalentes de ese tiempo, pero
sigue siendo parte de la definición de la receta (no hay que borrarlo ni crear una receta aparte).
Distinto de `bloqueado`: `opcional` decide si el ingrediente participa o no; `bloqueado` decide si,
estando presente, su cantidad se puede ajustar con el stepper. Los dos son independientes entre sí.
Se agregó específicamente para poder fusionar recetas casi idénticas que solo diferían en un
ingrediente extra (ver limpieza del banco de "filete de pescado" en el historial de commits) en vez
de mantenerlas como documentos separados.

## Colección `recetas` — banco de platillos reutilizables (para generación y para la UI)

Fuente: `recetas.json`, extraído automáticamente el 2026-08-24 de los 17 menús ya reconciliados en
`Json-outputs-sin-notas/`. Son 159 platillos reales (ya cocinados, con equivalentes validados) —
esta es la pieza que tanto el generador automático como el picker de la UI ("build your menu")
usan como bloques de construcción, en vez de inventar ingredientes/cantidades desde cero.

```
{
  "receta_id": string,              // slug único, ej. "ceviche-de-atun-v3"
  "nombre": string,                 // nombre del platillo tal como aparecía en el menú de origen
  "tiempo_tipico": [string, ...],   // en qué tiempo(s) se vio: desayuno/comida/cena/colacion/al_despertar
  "personas_vistas": [string, ...], // persona_id(s) — para qué persona(s) ya se usó este platillo
  "vector_equivalentes": { grupo: int, ... },  // suma de equivalentes por grupo_smae — usar esto para el solver
  "ingredientes": [ Ingrediente, ... ],         // misma forma que Ingrediente en la colección menus
  "veces_visto": int,               // cuántas veces apareció con exactamente estos ingredientes
  "origen": [ { persona, periodo, tab_origen, menu_id, tiempo }, ... ]  // trazabilidad, no necesario para generar
}
```

Cuando el mismo `nombre` de platillo tiene más de una combinación de ingredientes distinta (ej.
porción más chica para una persona, o variantes de fruta/verdura de acompañamiento a lo largo de
los meses), cada combinación es una receta separada con sufijo `-v1`, `-v2`, etc. — 44 de los 98
nombres de platillo tienen 2+ variantes así. Nombres de alimento en `ingredientes` ya se
normalizaron contra `catalogo-alimentos.json` (sin emojis, ortografía unificada) antes de
deduplicar.

**Cómo generar un menú nuevo con este banco**: dado un objetivo por tiempo (ej. Comida:
Verdura=2, Cereal=2, AOA=4, Aceite s/p=1), buscar en `recetas` las que tengan
`tiempo_tipico` compatible y `vector_equivalentes` que sume exacto (o combinar 2 recetas
pequeñas — ej. un platillo principal + una guarnición suelta). Esto es un problema de
bin-packing/mochila, resolver con código determinístico (Python), no pidiéndole a un LLM que
haga la suma. El LLM entra para: elegir entre varias recetas que califican (variedad, qué se ha
repetido últimamente), redactar el resultado final legible, y proponer recetas nuevas cuando el
banco no tiene ninguna combinación que cuadre con el objetivo.

## Colección `objetivos` — objetivo diario vigente, por persona

**No viene de un archivo fuente** — se construyó en Fase 1 de `BUILD-PLAN.md`, confirmado con el
usuario el 2026-08-24 para el periodo Agosto-Septiembre 2026 a partir de
`equivalentes_diarios_indicados` (o, si no estaba presente en los archivos 2026 de esa persona,
`equivalentes_diarios` del `menu_id 1` más reciente disponible — decisión explícita del usuario,
ver historial de commits) de cada persona.

**Decisión de diseño (confirmada con el usuario, 2026-08-24): el objetivo es diario, no por
tiempo.** No importa cómo se reparta entre comidas (una persona puede comer todo en una sola
comida o en seis) — lo único que se valida de forma dura es el total del día. `por_tiempo`, si se
llega a poblar, NO es una meta prescriptiva por comida — sería un resumen derivado de cómo terminó
repartiéndose un día ya armado, no un target contra el que se valide. Por ahora se deja
ausente/vacío.

```
{
  "persona": string,                // persona_id (ver colección `personas`)
  "vigente_desde": string,          // fecha ISO, ej. "2026-08-24" — para poder tener historial de objetivos
  "equivalentes_diarios": [ EquivalenteGrupo, ... ],
  "por_tiempo"?: { ... }            // opcional, ver nota arriba — no es un target por comida, no poblado en Fase 1
}
```
La UI (`UI-BUILD-YOUR-MENU.md`) usa `equivalentes_diarios` como presupuesto del día completo; a
medida que se arma cada tiempo, el panel de estado muestra cuánto queda del presupuesto diario, no
una comparación contra un objetivo fijo de esa comida en particular. `validar_tiempo()`/
`validar_menu()` (`VALIDATION.md`) siguen usándose igual para validar los `menus` históricos
(consistencia interna declarado-vs-real), que es un concepto distinto de este presupuesto diario.

**Pendiente futuro** (ver `BUILD-PLAN.md` → "Ideas para más adelante"): que el objetivo de cada
persona sea editable desde la propia UI, con perfiles por persona — hoy solo se puede cambiar
insertando un nuevo documento con `vigente_desde` más reciente directamente en Mongo.

## Colección `menus_construidos` — lo que arma el usuario en la UI

**Actualizado en Fase 4 (2026-08-27)** respecto al diseño original de este documento — ver notas
inline abajo de qué cambió y por qué (priorizando que el round-trip guardar→volver a abrir sea
exacto, criterio de "hecho" explícito de `BUILD-PLAN.md` → Fase 4).

```
{
  "persona": string,
  "fecha": string,                  // fecha ISO del día -- ya NO es opcional en Fase 4 (a pedido
                                     // del usuario: varios planes por persona, uno por fecha, con
                                     // historial). Único índice recomendado: (persona, fecha).
  "estado": string,                 // "completo" si delta_diario da todo cero, si no "en_progreso"
  "objetivo_diario": { grupo: int, ... },  // snapshot del objetivo vigente al momento de guardar
                                            // (por si el objetivo de la persona cambia después)
  "actual_diario": { grupo: int, ... },    // suma de todos los tiempos, cacheado al guardar
  "delta_diario": { grupo: int, ... },     // delta_objetivo(objetivo_diario, actual_diario)
  "tiempos": {
    "desayuno"?: TiempoConstruido,
    "comida"?: TiempoConstruido,
    "cena"?: TiempoConstruido,
    "colacion"?: TiempoConstruido,
    "al_despertar"?: TiempoConstruido
  }
}
```

**TiempoConstruido**:
```
{
  "seleccion": [ RecetaInstancia, ... ],
  "actual": { grupo: int, ... }     // = sumar_por_grupo() de los ingredientes incluidos, cacheado
}
```
Ya NO trae `delta` por tiempo — con el objetivo rediseñado como diario (no por tiempo, ver más
arriba), un "delta de este tiempo" no tiene un significado fijo por sí solo; el `delta_diario` a
nivel del documento es lo que sí se valida. El presupuesto restante por tiempo que se muestra en
vivo en la UI (objetivo diario menos lo ya usado en otros tiempos) es una vista calculada al vuelo,
no algo que se persiste.

**RecetaInstancia** — snapshot completo de la receta tal como quedó tras los ajustes del usuario
(ya NO delta-encoded contra la receta base — se cambió a guardar el estado completo para garantizar
un round-trip exacto sin tener que re-resolver `receta_id` contra el banco al reabrir, que pudo
haber cambiado desde entonces):
```
{
  "receta_id": string,               // referencia informativa a `recetas.receta_id`
  "nombre": string,
  "ingredientes": [                  // mismo shape que Ingrediente (schema.md arriba), + estos dos:
    { "alimento": string, "grupo_smae": string | null, "equivalentes": int,
      "bloqueado"?: bool, "opcional"?: bool,
      "incluido": bool               // solo relevante si opcional=true -- si el usuario lo excluyó
    }
  ]
}
```

Ajustar un ingrediente con el stepper +/- SIEMPRE se hace en pasos de 1 equivalente completo (ver
`VALIDATION.md` → `paso_equivalente()`) — nunca fracciones. Un ingrediente sin
`cantidad_por_equivalente` resoluble en el catálogo (placeholders como "Fruta suelta", o
ingredientes compuestos como "Nopal y Pimiento") no es ajustable por stepper — se agrega/quita
completo.

## Validación (aplica al generar, al importar, y a lo construido en la UI)

Para cada `tiempo`: `sum(ingrediente.equivalentes agrupado por grupo_smae) == tiempo.equivalentes`
(como lista de EquivalenteGrupo, agregando duplicados). Ver `VALIDATION.md` para el contrato
formal de funciones (`validar_tiempo`, `validar_menu`, `delta_objetivo`).

Para cada `menu` (variante): `sum(tiempo.equivalentes de todos los tiempos, agrupado por grupo)
== menu.equivalentes_diarios`.

## Sobre `Json-outputs/` vs `Json-outputs-sin-notas/`

Mismo schema exacto, la única diferencia es que `Json-outputs/` incluye `"nota"` en cada
ingrediente/entrada donde hubo una decisión editorial, y campos top-level `_nota*` con contexto de
por qué se resolvió así. `Json-outputs-sin-notas/` quita TODOS los campos `nota` y `_nota*`
recursivamente — mismo dato estructurado, sin la prosa. Usar `-sin-notas` para poblar Mongo y como
contexto de trabajo; usar la versión con notas solo si se necesita auditar una decisión específica.
