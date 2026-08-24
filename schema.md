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
  "persona": string,               // "Dan" | "Pau" — canónico, sin variantes
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
  "nota"?: string                   // presente solo en Json-outputs/ (no en -sin-notas/)
}
```

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
  "personas_vistas": [string, ...], // "Dan" y/o "Pau" — para qué persona(s) ya se usó este platillo
  "vector_equivalentes": { grupo: int, ... },  // suma de equivalentes por grupo_smae — usar esto para el solver
  "ingredientes": [ Ingrediente, ... ],         // misma forma que Ingrediente en la colección menus
  "veces_visto": int,               // cuántas veces apareció con exactamente estos ingredientes
  "origen": [ { persona, periodo, tab_origen, menu_id, tiempo }, ... ]  // trazabilidad, no necesario para generar
}
```

Cuando el mismo `nombre` de platillo tiene más de una combinación de ingredientes distinta (ej.
porción más chica para Pau, o variantes de fruta/verdura de acompañamiento a lo largo de los
meses), cada combinación es una receta separada con sufijo `-v1`, `-v2`, etc. — 44 de los 98
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
usuario el 2026-08-24 para el periodo Agosto-Septiembre 2026 (Dan: `equivalentes_diarios_indicados`
de `Junio26-Dany.json`; Pau: `equivalentes_diarios` del `menu_id 1` de `PauJunio26.json`, ya que
Pau no trae `equivalentes_diarios_indicados` en ningún archivo 2026 — decisión explícita del
usuario, ver historial de commits).

**Decisión de diseño (confirmada con el usuario, 2026-08-24): el objetivo es diario, no por
tiempo.** No importa cómo se reparta entre comidas (una persona puede comer todo en una sola
comida o en seis) — lo único que se valida de forma dura es el total del día. `por_tiempo`, si se
llega a poblar, NO es una meta prescriptiva por comida — sería un resumen derivado de cómo terminó
repartiéndose un día ya armado, no un target contra el que se valide. Por ahora se deja
ausente/vacío.

```
{
  "persona": string,                // "Dan" | "Pau"
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

```
{
  "persona": string,
  "fecha": string,                  // fecha ISO del día que se está armando, o null si es "borrador libre"
  "estado": string,                 // "en_progreso" | "completo"
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
  "actual": { grupo: int, ... },     // = sumar_por_grupo() de todas las RecetaInstancia, cacheado al guardar
  "delta": { grupo: int, ... }       // = delta_objetivo(objetivo_de_ese_tiempo, actual), cacheado al guardar
}
```

**RecetaInstancia** — una receta del banco tal como quedó tras los ajustes +/- del usuario:
```
{
  "receta_id": string,               // referencia a `recetas.receta_id`
  "ajustes": [                       // solo los ingredientes que el usuario movió del valor base
    { "alimento": string, "equivalentes_delta": int }   // ej. +1 o -2 respecto al vector_equivalentes original
  ],
  "vector_resultante": { grupo: int, ... }  // vector_equivalentes de la receta + ajustes aplicados, ya calculado
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
