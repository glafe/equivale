# BUGS — bugs, caveats y feature requests

Registro vivo del *por qué* y *cómo* de cada problema/idea. `CHANGELOG.md` es la versión corta
para quien solo quiere saber *qué* cambió y *cuándo*; este archivo tiene el detalle. Al cerrar un
bug o enviar un feature, `CHANGELOG.md` recibe una línea con el ID de acá.

IDs son secuenciales y nunca se reutilizan dentro de cada serie.

## Contents

### Bugs
- Resueltos: [BUG-001](#bug-001--status-rv), [BUG-002](#bug-002--status-rv),
  [BUG-003](#bug-003--status-rv), [BUG-004](#bug-004--status-rv), [BUG-005](#bug-005--status-rv),
  [BUG-006](#bug-006--status-rv), [BUG-007](#bug-007--status-rv), [BUG-008](#bug-008--status-c),
  [BUG-009](#bug-009--status-rv), [BUG-010](#bug-010--status-rv), [BUG-011](#bug-011--status-rv),
  [BUG-012](#bug-012--status-rv), [BUG-013](#bug-013--status-rv)

### Known Caveats
- Abiertos: [KC-001](#kc-001), [KC-002](#kc-002), [KC-003](#kc-003), [KC-004](#kc-004)

### Feature Requests
- Propuestos: [FR-001](#fr-001), [FR-005](#fr-005), [FR-006](#fr-006), [FR-009](#fr-009)
- Parcialmente Shipped: [FR-003](#fr-003)
- Shipped: [FR-002](#fr-002), [FR-004](#fr-004), [FR-007](#fr-007), [FR-008](#fr-008)

## Severity guide

`Critical` (crash/pérdida de datos/falla total) · `High` (rotura mayor, sin workaround) ·
`Medium` (degradado, hay workaround) · `Low` (cosmético/menor/caso raro) · `Enh` (mejora menor).

## Status definitions

- Bugs: `O` Open · `IP` In Progress · `R` Resolved · `RV` Resolved & Verified · `C` Closed
- Caveats: `Active` · `Historical` · `Resolved <fecha>`
- Feature Requests: `Proposed` · `Planned` · `In Progress` · `Shipped` · `Declined`

---

## Bugs

### Detailed Entries

#### BUG-013 · [STATUS: RV]
**Title:** Ingredientes fusionados/renombrados en el catálogo quedaban huérfanos en días ya
guardados, mostrados como "Sin grupo / libre" en "Lista del súper"
**Severity:** Medium
**Reported Date:** 2026-08-30
**Release Fixed:** 0.24.0

##### Observable Problem
El usuario reportó, tras organizar/fusionar entradas de "Leche" en el catálogo (a "Leche
descremada"), que "Lista del súper" mostraba esa leche como "Sin grupo / libre" en vez de AOA --
como si no hiciera falta comprar una cantidad real, cuando sí la hace.

##### Fix Explanation (Exec Level — No Code)
Renombrar o fusionar un alimento en el catálogo (Editor de ingredientes, o "🔗 Usar este" en
Configuración) solo actualizaba el banco de recetas -- pero un día ya guardado en "Menú del día"
es una fotografía completa de cómo quedó ese día, no una referencia que se actualice sola cuando
cambia el banco. "Leche"/"Leche semi" se habían fusionado correctamente a "Leche descremada" en el
catálogo y en las recetas, pero varios días ya guardados seguían con el nombre viejo -- y como ese
nombre viejo ya no existía en el catálogo, se veía como "libre" en vez de como lo que realmente es
(AOA). Además, el chequeo de Configuración que detecta este tipo de problema solo miraba el banco
de recetas, así que este caso en particular (huérfano SOLO en días guardados, banco ya limpio) no
aparecía en ningún lado para poder corregirlo.

##### Fix Details (Technical)
Nueva función pura `renombrar_ingrediente_en_menu_guardado()` en `nutriguia/validation.py` (ver
`VALIDATION.md`): renombra un ingrediente dentro de un `menus_construidos` ya guardado, fusiona
duplicados por instancia con `fusionar_ingredientes_duplicados()` (mismo caso que `BUG-009`, pero
aplicado a un día guardado en vez de a una receta del banco) y recalcula `actual`/`actual_diario`/
`delta_diario`/`estado` -- `objetivo_diario` no se toca, sigue siendo el snapshot original.
`_renombrar_en_menus_construidos()` (duplicada en `views/configuracion.py` y
`views/editor_ingredientes.py`, mismo patrón que `_renombrar_en_recetas()`) la aplica sobre todos
los días guardados y escribe de vuelta. Se llama junto con `_renombrar_en_recetas()` en los tres
lugares donde se puede renombrar/fusionar un alimento (el flujo de "Editar un alimento" en el
Editor de ingredientes, y "🔗 Usar este" en Configuración). El chequeo "🥕 Ingredientes que ya no
están en el catálogo" (antes "... de recetas que ya no están...") ahora también escanea
`menus_construidos`, mostrando por separado en dónde aparece cada huérfano ("En recetas: ..." /
"En días ya guardados: ..."), para que un caso como este sí se pueda encontrar y corregir con un
clic. De paso, `agrupar_alimentos_por_grupo()` (`nutriguia/html_lista_super.py`) distingue ahora
un alimento **huérfano** (`SIN_CATALOGAR`, nueva sección "⚠️ Sin catalogar") de uno **libre a
propósito** (`grupo: null` en el catálogo, ej. una especia) -- antes ambos cayían en la misma
sección "Sin grupo / libre", ocultando el problema incluso después de corregirlo en otro lugar
distinto a como se reportó originalmente. Las 8 apariciones ya afectadas en producción ("Leche"/
"Leche semi" en 5 días guardados de Dan y Pau) se corrigieron con la misma herramienta ya
desplegada, no con un script aparte.

##### Workaround
Ninguno necesario tras el fix -- antes, revisar a mano cada día guardado desde "Menú del día" y
corregir el ingrediente ahí.

#### BUG-012 · [STATUS: RV]
**Title:** "Agregar de SMAE" mostraba nombres con acentos corruptos ("CafÃ©") y no encontraba
algunos alimentos al buscarlos con acento
**Severity:** Low
**Reported Date:** 2026-08-30
**Release Fixed:** 0.23.0

##### Observable Problem
El usuario reportó dos cosas a la vez, que resultaron ser la misma causa: (1) al buscar "Café" (con
o sin acento) en "Agregar de SMAE", el nombre aparecía mostrado como "CafÃ©" en vez de "Café"; y
(2) "Café en polvo" no aparecía en los resultados de esa búsqueda -- solo las variantes
descafeinadas.

##### Fix Explanation (Exec Level — No Code)
`SMAE_CONSULTA.csv` mezcla dos codificaciones de caracteres entre secciones (parte en Latin-1,
parte en UTF-8) y se lee entera como Latin-1 -- las filas que en realidad están en UTF-8 quedan
con los acentos mal formados ("mojibake": los bytes de "é" se leen como dos caracteres sueltos,
"Ã" y "©"). Eso explica el problema (1). El problema (2) es consecuencia del mismo daño: la
función que le quita el acento a una palabra para poder compararla sin importar mayúsculas/acentos
(`normalizar_busqueda()`) le quitaba a "CafÃ©" el carácter equivocado y el resultado no volvía a
coincidir con "café" al buscar -- por eso "Café en polvo" (con el acento corrupto) no aparecía,
mientras que "Café descafeinado" sí (esa coincidencia no dependía del acento corrupto). Ahora el
texto se repara antes de mostrarlo o compararlo, así que ambos problemas se resuelven con el mismo
arreglo.

##### Fix Details (Technical)
Nueva función pura `_reparar_mojibake()` en `nutriguia/smae_csv.py`: re-codifica el string (ya
decodificado como Latin-1) de vuelta a bytes Latin-1 -- eso nunca falla -- y trata de decodificar
esos bytes como UTF-8; si funciona, eran bytes UTF-8 mal leídos y devuelve el resultado corregido;
si truena (`UnicodeDecodeError`), el texto sí era Latin-1 genuino y se deja igual. Heurística
estándar para archivos de codificación mixta (la misma que usa la librería `ftfy`), sin agregar
una dependencia nueva. Se aplica a `alimento`, `unidad` (dentro de `cantidad_por_equivalente`) y
`tipo_original` en `cargar_filas_smae()` antes de devolver cada fila. La clasificación por
categoría (`grupo_smae`) no se tocó -- ya era inmune, porque solo compara el prefijo ASCII de
`Tipo Equivalente`. `tests/test_smae_csv.py` cubre la reparación (recupera mojibake real, no toca
Latin-1 genuino) y el caso reportado ("Café en polvo" aparece y se encuentra buscando "café").

##### Workaround
Ninguno necesario tras el fix -- antes, buscar por una palabra que no incluyera el acento
corrupto (ej. "descafeinado" en vez de "café").

#### BUG-011 · [STATUS: RV]
**Title:** "🧬 Clonar" (Menú del día) podía sobreescribir sin aviso un plan ya guardado de la
persona destino
**Severity:** Medium
**Reported Date:** 2026-08-30
**Release Fixed:** 0.21.0

##### Observable Problem
Encontrado en revisión de código previa a un release (a pedido del usuario, "revisa y valida
antes de liberar"), no reportado por uso real. Al clonar un día a otra persona (`FR-008`, shipped
0.19.0), si esa persona YA tenía un plan guardado para la fecha elegida (default: hoy), clonar lo
sobreescribía sin ningún aviso -- a diferencia de "Guardar menú del día", donde lo que se va a
sobreescribir está a la vista en pantalla (es el mismo plan que se está editando), acá el plan de
la persona destino nunca se muestra antes de confirmar.

##### Fix Explanation (Exec Level — No Code)
El popover "🧬 Clonar" ahora revisa si la persona destino ya tiene un plan para la fecha elegida
antes de mostrar el botón de confirmar, y si lo hay, avisa con el nombre de ese plan (si tiene) y
dice explícitamente que clonar lo va a sobreescribir -- igual se puede confirmar (mismo criterio
de "avisar, no bloquear" que el resto de la app), pero ya no a ciegas.

##### Fix Details (Technical)
`db().menus_construidos.find_one({"persona": destino, "fecha": fecha_destino.isoformat()})` justo
antes del botón "Clonar", dentro del mismo popover -- `st.warning()` si existe. No cambia
`_clonar_a_persona()`, que sigue haciendo el mismo upsert por `(persona, fecha)`.

##### Workaround
Ninguno necesario tras el fix -- antes, revisar a mano el historial de la persona destino antes
de clonar.

#### BUG-010 · [STATUS: RV]
**Title:** "Lista del súper" podía perder un alimento silenciosamente si su grupo no era uno de
los 7 canónicos
**Severity:** Low
**Reported Date:** 2026-08-30
**Release Fixed:** 0.21.0

##### Observable Problem
Encontrado en revisión de código previa a un release (a pedido del usuario, "revisa y valida
antes de liberar"), no reportado por uso real -- no debería pasar con datos limpios (`schema.md`
exige que `catalogo_alimentos.grupo` sea uno de los 7 grupos canónicos o `null`), pero si el
catálogo llegara a tener un dato sucio (ej. un typo de grupo), ese alimento desaparecía de la
lista de compras sin ningún aviso, en vez de aparecer en una sección "no reconocida" -- tanto en
el HTML descargable como en la vista previa en pantalla, que además duplicaban la misma lógica de
agrupación en dos archivos distintos (con el mismo bug en ambos, encontrado y corregido a la vez).

##### Fix Explanation (Exec Level — No Code)
La función que agrupa los alimentos de la lista por grupo SMAE ahora nunca descarta uno --
cualquier grupo que no sea de los 7 canónicos (ni `null`/libre) aparece en su propia sección al
final, en vez de perderse. De paso, la vista previa en pantalla de "Lista del súper" dejó de tener
su propia copia de esta lógica (que tenía el mismo bug) y ahora usa la misma función que el HTML
descargable -- una sola fuente de verdad.

##### Fix Details (Technical)
`agrupar_alimentos_por_grupo()` en `nutriguia/html_lista_super.py` (renombrada de `_agrupar_por_
grupo`, ahora pública) agrega un tercer bloque -- grupos no listados en `ORDEN_GRUPOS` y distintos
de `None`, ordenados alfabéticamente -- antes de la sección final `None`/libre.
`views/lista_super.py` ya no arma su propio `por_grupo`/`grupos_en_orden` a mano para la vista
previa, importa y llama a `agrupar_alimentos_por_grupo()` directamente. De paso se unificó el
color de fallback ("Sin grupo/no reconocido") a `COLOR_POR_DEFECTO` (`nutriguia/colores.py`) en
`html_lista_super.py` y `html_semanal.py`, que antes tenían cada uno su propio hex hardcodeado
(`#8A8378` vs `#555555`) -- inconsistencia menor, sin impacto funcional, corregida de paso.

##### Workaround
Ninguno necesario tras el fix -- antes, revisar "Posibles duplicados en el catálogo" en
Configuración para detectar el dato sucio a mano.

#### BUG-009 · [STATUS: RV]
**Title:** "🔗 Usar este" (reemplazar huérfano) dejaba ingredientes duplicados dentro de una receta
**Severity:** Medium
**Reported Date:** 2026-08-30
**Release Fixed:** 0.17.0

##### Observable Problem
El usuario notó, limpiando el catálogo a mano, que varias recetas tenían el mismo ingrediente
listado dos (o hasta tres) veces -- ej. "Crema de cacahuate" tres veces en "Pan tostado con
plátano", o "Res molida" dos veces en "Espagueti Boloñesa". Corrigió algunas a mano y pidió
revisar si quedaban más -- una consulta directa a Mongo encontró 4 recetas afectadas en total.

##### Fix Explanation (Exec Level — No Code)
"Editor de ingredientes" y "Configuración" tienen un botón "🔗 Usar este" para cuando un
ingrediente huérfano (sin catalogar) en realidad es el mismo alimento que uno que ya existe --
renombra el huérfano al nombre del existente en todas las recetas que lo usaban. El bug: si una
receta YA tenía un ingrediente con ese nombre (ej. la receta ya usaba "Nopales" Y tenía un
huérfano que también era, en el fondo, "Nopales" con otra ortografía), el renombrado dejaba DOS
filas con el mismo nombre en vez de fusionarlas en una -- inflando el conteo de equivalentes de
ese grupo sin que se notara a simple vista.

##### Fix Details (Technical)
Nueva función pura `fusionar_ingredientes_duplicados()` en `nutriguia/validation.py` (ver
`VALIDATION.md`): colapsa ingredientes con el mismo `alimento` sumando sus `equivalentes` -- el
total por grupo no cambia (es la misma suma repartida en una fila en vez de N), así que fusionar
es seguro sin revisar caso por caso. `_renombrar_en_recetas()` (duplicada en
`views/configuracion.py` y `views/editor_ingredientes.py`) ahora la llama después de renombrar, y
recalcula `vector_equivalentes`. Nuevo chequeo en Configuración,
"🔁 Ingredientes duplicados dentro de una misma receta" (`_check_ingredientes_duplicados_en_
receta()`), con un botón "Fusionar" por receta afectada -- se usó ese mismo botón, ya desplegado,
para limpiar las 4 recetas que quedaban en producción en vez de un script de migración aparte
(no se persiguió con un script porque la herramienta en la app ya cubre el caso permanentemente).

##### Workaround
Ninguno necesario tras el fix -- antes, corregir a mano desde el Editor de recetas.

#### BUG-008 · [STATUS: C]
**Title:** Los enlaces `<a href>` del diagrama de "Guía" no navegaban al hacer clic
**Severity:** Low
**Reported Date:** 2026-08-29
**Resolved Date:** 2026-08-29

##### Observable Problem
Al probar el diagrama de "Guía" con Playwright, hacer clic en un nodo no cambiaba la URL de la
página bajo prueba — parecía que el clic no hacía nada.

##### Fix Explanation (Exec Level — No Code)
No era un bug de la app: Streamlit fuerza `target="_blank" rel="noopener noreferrer"` en TODO
`<a>` que renderiza vía markdown (incluso con `unsafe_allow_html=True`, e incluso para un href
relativo/interno como estos) — el clic sí funcionaba, solo que abría la página destino en una
**pestaña nueva** del navegador en vez de navegar en el mismo lugar. El script de prueba
verificaba la URL de la MISMA pestaña, así que nunca iba a ver el cambio.

##### Fix Details (Technical)
Primer intento (equivocado): se agregó `onclick="window.location.href=...; return false;"` a
cada nodo, asumiendo que algo suprimía el comportamiento por default del `<a>`. Ese `onclick` no
hacía nada — Streamlit también elimina cualquier atributo `onclick` de un `<a>` renderizado vía
markdown (medida de sanitización, no configurable) — pero como el `target="_blank"` de por sí sí
funcionaba, el clic "se veía arreglado" cuando en realidad el `onclick` nunca se ejecutó. Se
confirmó la causa real usando `page.context.expect_page()` de Playwright (esperar una pestaña
nueva) en vez de revisar la URL de la pestaña original. Se quitó el `onclick` (inerte) y se
actualizó el texto de la página para decir "se abre en una pestaña nueva" en vez de implicar
navegación en el mismo lugar.

##### Workaround
Ninguno necesario — el comportamiento real (abrir en pestaña nueva) es aceptable para una página
de ayuda; solo hacía falta que el texto de la UI lo describiera bien.

#### BUG-007 · [STATUS: RV]
**Title:** Los nodos del diagrama de "Guía" se veían como enlaces azules subrayados, no como tarjetas
**Severity:** Low
**Reported Date:** 2026-08-29
**Release Fixed:** 0.8.1

##### Observable Problem
En la página "Guía", el texto dentro de cada cuadro del diagrama (ej. "Personas", "Recetas")
salía en azul y subrayado -- el estilo de enlace por default del navegador, no el diseño de
tarjeta pensado (fondo, borde, texto oscuro sin subrayado).

##### Fix Details (Technical)
Streamlit aplica su propio color/subrayado a los `<a>` dentro de contenido markdown con un
selector más específico que una sola clase CSS (`.eqv-node`) -- por eso no le ganaba. Cambiado a
`a.eqv-node` (selector más específico) + `!important` en `color`/`text-decoration`, mismo
recurso que ya usa `nutriguia/estilo.py` para pelear contra estilos nativos de Streamlit.
Encontrado en QA visual con Playwright antes de anunciar el cambio como terminado (mismo hábito
que descubrió `BUG-005`/`BUG-006`).

#### BUG-006 · [STATUS: RV]
**Title:** "Total de este tiempo" en Menú semanal mostraba el HTML del chip como texto plano
**Severity:** Low
**Reported Date:** 2026-08-29
**Release Fixed:** 0.6.1

##### Observable Problem
En el editor de "Menú semanal", debajo de las recetas de un tiempo, la línea "Total de este
tiempo" mostraba el `<span style="...">` completo como texto literal en vez de la pastilla de
color esperada.

##### Fix Details (Technical)
`views/menu_semanal.py` usaba `st.caption(texto + _chips(...))` en vez de
`st.markdown(..., unsafe_allow_html=True)` para esa línea en particular -- el resto de los usos
de `_chips()` en el mismo archivo sí pasaban por `st.markdown` con `unsafe_allow_html=True` y se
veían bien; encontrado en QA visual con Playwright antes de anunciar el cambio como terminado
(mismo hábito que descubrió `BUG-005`).

#### BUG-005 · [STATUS: RV]
**Title:** El CSS de la identidad "Barro" se mostraba como texto plano en vez de aplicarse
**Severity:** High
**Reported Date:** 2026-08-27
**Release Fixed:** 0.4.2

##### Observable Problem
Al desplegar la identidad visual "Barro", el bloque completo de reglas CSS aparecía como texto
literal visible arriba del título de cada página, en vez de aplicarse silenciosamente. El resto
del estilo (colores, tipografía de encabezados, chips) sí se aplicaba — solo la sección final del
CSS se veía como texto.

##### Steps to Reproduce
1. Cargar cualquier página de la app tras desplegar `nutriguia/estilo.py`.
2. Esperado: sin texto visible de CSS, solo la app estilizada. Actual: el CSS completo aparece
   como un párrafo de texto plano antes del título.

##### Fix Explanation (Exec Level — No Code)
El código que inyecta el estilo visual mandaba las etiquetas de fuentes (Google Fonts) y el
bloque de estilos juntos en una sola instrucción. El intérprete de texto de Streamlit cortó ese
bloque a la mitad en la primera línea en blanco que encontró dentro del CSS, y mostró el resto
como texto normal en vez de aplicarlo como estilo.

##### Fix Details (Technical)
Streamlit renderiza `st.markdown(..., unsafe_allow_html=True)` pasando el contenido por un
parser tipo CommonMark antes de insertarlo en el DOM. Los tags `<link>` en `GOOGLE_FONTS_LINK`
califican como bloque HTML "tipo 6" (lista fija de tags), que termina en la primera línea en
blanco; al concatenarlos con `<style>...</style>` en la misma llamada sin una línea en blanco de
separación, el parser seguía dentro de ese bloque tipo 6 al llegar a `<style>` (en vez de
reconocerlo como el inicio de un bloque tipo 1 -- script/pre/style/textarea -- que sí tolera
líneas en blanco adentro), y la primera línea en blanco DENTRO del CSS cortaba el bloque a la
mitad. `nutriguia/estilo.py::inyectar_css()` ahora hace dos `st.markdown()` separados: uno para
los `<link>` de fuentes y otro, empezando limpio en su propia línea, para el `<style>`.

##### Workaround
Ninguno necesario tras el fix — no se detectó en producción real (encontrado en QA visual con
Playwright antes de anunciar el cambio como terminado).

#### BUG-004 · [STATUS: RV]
**Title:** El grupo SMAE no se auto-llenaba al elegir un alimento del catálogo en el editor
**Severity:** Medium
**Reported Date:** 2026-08-25
**Release Fixed:** 0.3.5

##### Observable Problem
Al elegir un alimento ya catalogado en el editor de recetas, la variable interna sí se
actualizaba pero el `selectbox` de Grupo en pantalla seguía mostrando el valor anterior (o vacío).

##### Fix Details (Technical)
`st.selectbox` ignora un `value`/`index` nuevo si su `key` ya tiene una entrada en
`st.session_state` de un render anterior. Fix: escribir explícitamente
`st.session_state[f"grupo_{fila_id}"]` con el grupo del catálogo *antes* de que ese widget se
vuelva a instanciar en el mismo run. Ver `views/editor_recetas.py`.

#### BUG-003 · [STATUS: RV]
**Title:** Botón "Eliminar" no aparecía inmediatamente tras crear una receta nueva
**Severity:** Low
**Reported Date:** 2026-08-24
**Release Fixed:** 0.3.5

##### Observable Problem
Después de guardar una receta recién creada, el botón "Eliminar" (que solo debe verse para
recetas ya existentes) no aparecía hasta refrescar manualmente.

##### Fix Details (Technical)
`receta_id` se asignaba después del `st.rerun()` en vez de antes, así que el rerun repintaba con
el `receta_id` viejo (vacío). Fix: mover la asignación antes del `rerun()`.

#### BUG-002 · [STATUS: RV]
**Title:** El campo `cantidad` de un ingrediente se podía perder al editar una receta
**Severity:** High
**Reported Date:** 2026-08-24
**Release Fixed:** 0.3.5

##### Observable Problem
El editor de recetas no traía un campo para `cantidad` en el formulario de ingredientes; al
guardar una receta editada, ese campo se sobreescribía con `""`, borrando el dato real de
`cantidad_por_equivalente` histórico (afectó a `alambre-de-pollo-v2`: "150 g"/"½ tz" perdidos).

##### Fix Details (Technical)
Se agregó el campo `cantidad` al formulario de ingredientes en `views/editor_recetas.py`. El
documento corrupto en Mongo se restauró manualmente con los valores originales.

##### Prevention
Este es el caso concreto que motivó **BUG-002 (Enh) → auto-llenado de cantidad desde el
catálogo** (ver 5d7399e / 1aa2f83): si el alimento está catalogado, `cantidad` ahora se deriva de
`equivalentes` y deja de ser editable a mano, eliminando esta clase de error.

#### BUG-001 · [STATUS: RV]
**Title:** Crash del editor con ingredientes "libres" (`grupo_smae: null`, `equivalentes: 0`)
**Severity:** Critical
**Reported Date:** 2026-08-25
**Release Fixed:** 0.3.5

##### Observable Problem
Abrir cualquier receta con un ingrediente libre (ej. Canela, Salsa casera, Gelatina — 18 recetas
afectadas) tiraba `StreamlitValueBelowMinError` en el editor.

##### Steps to Reproduce
1. Abrir el editor de recetas.
2. Elegir una receta con un ingrediente sin grupo SMAE (ej. "Tinga de Pollo").
3. Esperado: el ingrediente se muestra con equivalentes=0. Actual: excepción, página rota.

##### Fix Explanation (Exec Level — No Code)
El stepper de equivalentes tenía un mínimo de 1 fijo para todos los ingredientes, pero los
ingredientes "libres" (sin grupo, cantidad al gusto) legítimamente valen 0 equivalentes.

##### Fix Details (Technical)
`number_input(min_value=1, ...)` aplicado incondicionalmente → cambiado a
`min_value = 0 if grupo_smae is None else 1`, más un clamp defensivo del `session_state` si el
usuario reasigna un grupo real a un ingrediente que era libre. Diagnosticado leyendo el
traceback embebido en un HAR de red (`Hars/192.168.68.59.har`, fuera de git) sin acceso directo a
logs del servidor.

---

## Known Caveats

### Detailed Entries

#### KC-004
**Title:** Elegir "Dark" a mano en el menú de Streamlit no oscurece el HTML propio de la app si el
sistema operativo sigue en modo claro
**Date Identified:** 2026-08-30
**Status:** Active

##### Exec Description
La vista oscura de EquiVale sigue la preferencia del sistema operativo/navegador (`prefers-color-
scheme`), no el selector System/Light/Dark que Streamlit agrega en su menú ⋮. Si alguien fuerza
"Dark" ahí mientras su sistema operativo sigue en claro, Streamlit sí oscurece sus componentes
nativos (fondo, tarjetas, inputs), pero el diagrama de "Guía" y los acentos de borde/sombra de
las tarjetas de "Menú del día" (HTML/CSS propio de la app, no de Streamlit) se quedan en su
versión clara hasta que el sistema operativo también cambie -- un desajuste visual, no un bug que
rompa nada funcionalmente.

##### Eng Description
Streamlit no expone su tema activo (el que resulta de System/Light/Dark) como una variable CSS
reutilizable en ningún elemento del DOM -- confirmado inspeccionando la app en vivo con
DevTools/Playwright: ni `:root` ni `.stApp` traen `--primary-color`/`--background-color`/etc.,
cada componente nativo recibe su color por JS/emotion de forma interna, sin dejar rastro
reutilizable. El HTML/CSS propio (`nutriguia/estilo.py`, `views/guia.py`) no puede correr
JavaScript para leer el tema real por la misma razón que el diagrama de Guía usa `:has()` en vez
de JS (ver `BUG-005`) -- así que la única señal disponible para ese CSS es `prefers-color-scheme`,
que refleja el sistema operativo, no la elección manual dentro de Streamlit. No hay arreglo limpio
mientras Streamlit no exponga su tema activo a CSS/JS de alguna forma.

##### Workaround
Dejar el selector de Streamlit en "System" (el default) -- así el sistema operativo controla todo
consistentemente. Si de verdad hace falta forzar "Dark" con el sistema en claro, el diagrama de
Guía y los acentos de tarjeta se ven un poco menos integrados, pero siguen siendo legibles.

#### KC-003
**Title:** "Lista del súper" muestra cantidad 0 (o "al gusto × 0") para algunos alimentos libres
**Date Identified:** 2026-08-30
**Status:** Active

##### Exec Description
Un alimento sin grupo SMAE (ej. una especia, "al gusto") en la sección "Sin grupo / libre" de
"Lista del súper" a veces muestra una cantidad de "0" (ej. "0 cucharadita" de canela) en vez de
una cantidad útil para comprar -- se ve raro en una lista de compras, aunque no es incorrecto
dado cómo está modelado el dato.

##### Eng Description
`cantidad_real()` escala `cantidad_por_equivalente` por el total de `equivalentes` sumado de ese
alimento en la semana. Para un ingrediente libre (`grupo_smae: null`), `equivalentes` no cuenta
para ningún presupuesto -- algunas recetas del banco lo dejaron en `0` al capturarse (ej. "Canela
en polvo", "Limón y tajín"), otras en un valor arbitrario distinto de cero (ej. "Mermelada sin
azúcar" con `equivalentes: 3`) -- no hay un criterio consistente en los datos existentes porque
nunca importó (`sumar_por_grupo()` los ignora en todos los demás usos). "Lista del súper" es el
primer lugar donde ese número sí se usa para algo visible (escalar una cantidad real), y expone la
inconsistencia. Workaround: revisar a ojo la sección "Sin grupo / libre" al hacer el súper --
suelen ser alimentos de despensa que no se compran por cantidad exacta de todas formas (especias,
"al gusto"). Arreglo de raíz pendiente: normalizar `equivalentes` de ingredientes libres a un
valor consistente (ej. siempre 1 por aparición) en el banco de recetas, o mostrar la cantidad tal
cual del catálogo sin escalar cuando `grupo_smae` es `null` -- no se hizo todavía por no tener
claro cuál de las dos es la corrección correcta sin uso real de la lista.

#### KC-002
**Title:** Kernels Linux 6.19–7.0.13 crashean MongoDB 8.0.x (bug de TCMalloc/rseq)
**Date Identified:** 2026-08-24
**Status:** Active (mientras el servidor corra un kernel en ese rango)

##### Exec Description
MongoDB no arrancaba en el servidor de producción hasta aplicar un workaround de compatibilidad
de kernel — no es un bug de este proyecto.

##### Eng Description
Bug conocido de glibc/TCMalloc con la syscall `rseq` en esa ventana de versiones de kernel.
Workaround: override de systemd con `Environment=GLIBC_TUNABLES=glibc.pthread.rseq=1` (ver
`SETUP.md`). No requiere cambios de código, solo de configuración del servicio.

##### Alternative Solutions
1. **Elegido** — override de systemd (`GLIBC_TUNABLES`), no invasivo, documentado en `SETUP.md`.
2. Downgrade de kernel — descartado, complica actualizaciones de seguridad del SO.
3. Downgrade de MongoDB — descartado, no atacaba la causa raíz.

#### KC-001
**Title:** Ingredientes con el mismo alimento real pero ortografía distinta quedan como
opcionales separados tras la fusión mecánica de recetas
**Date Identified:** 2026-08-25
**Status:** Active

##### Exec Description
Al fusionar recetas duplicadas por nombre exacto, si el mismo alimento aparecía escrito distinto
entre variantes (ej. "Atún" vs "Atún en agua", "Proteína" vs "Proteína en polvo"), el script de
fusión no los reconoció como el mismo ingrediente y quedaron como dos ingredientes opcionales
separados en la receta fusionada, en vez de uno solo.

##### Eng Description
`scripts/migraciones/2026-08-25-fusionar-recetas-por-nombre.py` compara nombres de ingrediente de
forma exacta (normalizado solo en mayúsculas/espacios) para decidir "está en todas las variantes"
vs. "solo en algunas" → opcional. No hay matching difuso. La pasada del 2026-08-25 (nombres
parecidos) corrigió ~16 casos detectados a mano, pero no se persiguió exhaustivamente en el resto
del banco (86 recetas).

##### Alternative Solutions
1. **Elegido (por ahora)** — corregir a mano desde el Editor de recetas si se nota al usar la
   app; bajo impacto (duplica un ingrediente opcional, no rompe la aritmética de equivalentes).
2. Matching difuso de nombres en el script de fusión — no implementado, riesgo de falsos
   positivos (fusionar alimentos que en realidad son distintos) mayor que el beneficio para un
   banco de 86 recetas.

---

## Feature Requests

### Detailed Entries

#### FR-009
**Title:** "EquiVale ChefBOT" — descubrir qué se puede cocinar según los ingredientes que usas
seguido
**Date Requested:** 2026-08-30
**Status:** Proposed (investigado, sin decidir todavía entre dos variantes -- ver abajo)

##### Exec Description
Inspirado en [supercook.com](https://www.supercook.com/), como un sub-modo de "EquiVale Chef"
(el editor de recetas): marcar qué alimentos usas seguido (no necesariamente "lo que tienes en
este momento", sino tus básicos habituales) y un botón "Descubrir platillos" que sugiere cuáles
se pueden cocinar ya, o casi (falta 1-2 ingredientes) -- limitado a recetas de máximo 6
ingredientes. Cada sugerencia mostrada ya viene "digerida" en equivalentes SMAE (grupo/cantidad
por ingrediente), y trae un botón para usarla directo.

##### Investigación de viabilidad (2026-08-30, a pedido del usuario, antes de decidir el diseño)
**Supercook.com no tiene API pública** -- no publica documentación para desarrolladores, y bloquea
acceso automatizado directo al sitio (403 fuera de un navegador normal); tampoco se encontró
ninguna API no-oficial mantenida. Integrarlo de verdad requeriría scraping frágil y probablemente
en contra de sus términos de servicio -- **no se recomienda**.

La alternativa real con API oficial es **Spoonacular** (endpoint `Find Recipes by Ingredients`,
bien documentado), pero con costos/complejidad relevantes para este proyecto: tier gratis de solo
50 puntos/día (probablemente un puñado de búsquedas), $29/mes el siguiente escalón; sus datos
están en inglés, así que cada receta importada necesitaría mapear sus ingredientes a mano contra
nuestro catálogo en español antes de poder "digerirla" en equivalentes (parecido a `asuncion:
true`, pero mucho más trabajo por receta); y agrega una dependencia externa nueva (API key,
`.env`, límites) para una app de 1-2 usuarios.

Dos variantes posibles, sin decidir todavía cuál construir:

**Variante A -- solo contra nuestro propio banco (procedural, gratis, sin dependencias)**
- **Ingredientes habituales**: qué alimentos del catálogo usa la persona seguido. Persistir por
  persona (colección nueva, ej. `ingredientes_habituales`: `{persona, alimentos: [string, ...]}`,
  un documento por persona, se sobreescribe) en vez de un checklist que se resetea cada vez --
  cambia poco día a día. Un `st.multiselect` sobre `cargar_nombres_alimentos()` para editarla.
- **Filtro de longitud**: solo recetas con `len(receta["ingredientes"]) <= 6` entran a la
  comparación.
- **Coincidencia**: para cada receta que pasa el filtro, contar cuántos de sus ingredientes NO
  están en los habituales de la persona -- 0 faltantes = "✅ la puedes hacer ya", 1-2 faltantes =
  "🔺 casi, te falta(n): X, Y" (como supercook.com con sus recetas "casi completas"), 3+ no se
  muestra. Los placeholders genéricos (`"Fruta"`/`"Fruta suelta"`, regla 6 de `CLAUDE.md`) cuentan
  como "siempre disponibles". Función pura, testable con datos sintéticos, sin Mongo.
- Como la receta sugerida YA es de nuestro banco, "agregar a mi recetario" no aplica tal cual (ya
  está ahí) -- el botón sería más bien "Usar en Menú del día" (agrega esa receta al tiempo que se
  esté armando, mismo mecanismo que el picker de recetas ya existente).
- Limitación honesta: solo redescubre las 86 recetas que ya existen en el banco, no trae nada
  nuevo -- el valor es "recuérdame qué de lo que ya cocino aplica hoy", no descubrimiento real.

**Variante B -- integrar Spoonacular (descubrimiento real de recetas nuevas)**
- Mismo mecanismo de "ingredientes habituales", pero la búsqueda va contra la API de Spoonacular
  en vez del banco propio -- si trae algo interesante, "Agregar a mi recetario" sí tendría sentido
  literal: crear una receta nueva en `recetas` a partir del resultado, con sus ingredientes
  mapeados a mano (o con `asuncion: true` + revisión) al catálogo antes de guardarla.
  Requiere: cuenta/API key de Spoonacular, manejo de su límite diario, y una pantalla de mapeo
  ingrediente-por-ingrediente antes de poder guardar (no se puede automatizar bien el
  español↔inglés + unidades sin revisión humana).
- **Requisitos adicionales, anotados 2026-08-30 (solo si algún día se paga la API -- no es
  dependencia de ningún release, ni siquiera de terminar Fase 5; es una idea a futuro, nada más)**:
  - **Traer de a 10 recetas por consulta** (no una lista larga de golpe) -- un "lote" por cada vez
    que se pulsa "Descubrir platillos", para no gastar el límite diario de golpe ni saturar la
    pantalla.
  - Además de "Agregar a mi recetario", cada receta sugerida necesita dos botones más:
    - **"Revisar luego"**: la guarda en una cola de pendientes (nueva, ej. colección
      `descubrimientos_pendientes: {persona, spoonacular_id, datos_crudos, ...}`) para volver a
      verla después sin gastar otra consulta a la API ni que se pierda entre lotes nuevos.
    - **"No volver a mostrar"**: la descarta permanentemente -- se guarda su id de Spoonacular en
      una lista de descartados por persona (ej. `descubrimientos_descartados: {persona,
      spoonacular_ids: [...]}`), y los lotes siguientes (de esta sesión o de otra futura) la
      excluyen filtrando por ese id antes de mostrar resultados -- no debe volver a aparecer
      nunca, ni al pedir otro lote ni en una sesión distinta.

##### Dependencies
Variante A: `recetas`/`catalogo_alimentos` (ya existen), ninguna dependencia nueva. Variante B:
cuenta de Spoonacular (o similar) + `.env` nuevo.

#### FR-008 · [STATUS: Shipped 0.19.0]
> **Shipped en 0.19.0 (2026-08-30)** — botón "🧬 Clonar" (`st.popover`) junto a "Abrir" en el
> historial de "Menú del día", con selector de persona destino y fecha. `_clonar_a_persona()`
> guarda el clon directo en Mongo para la persona destino (sin cambiar la persona que se está
> editando) y recalcula objetivo/actual/delta contra el objetivo de destino. Si el nombre original
> ya está en uso por otra fecha de destino, se guarda sin nombre (evita violar "nombre único por
> persona") y se avisa. Ver `UI-BUILD-YOUR-MENU.md` → "Menú del día" 6.1 y `CHANGELOG.md` 0.19.0.

**Title:** Clonar un menú de una persona a otra
**Date Requested:** 2026-08-30
**Status:** Proposed

##### Exec Description
Poder copiar un día ya armado y guardado con nombre (ej. "Menú 1" de Persona A) hacia otra
persona, para usarlo como punto de partida en vez de armar todo desde cero -- y después poder
ajustar cantidades/ingredientes ya del lado de la persona destino sin afectar el original.

##### Eng Description
Distinto de `FR-005` (duplicar un día para la MISMA persona): aquí el `persona` cambia. Reutiliza
`_instancia_desde_guardado()` de `views/menu_del_dia.py` para clonar cada `RecetaInstancia` con
`instancia_id` nuevo (ya lo hace hoy al "Abrir" un día del historial), pero el documento
resultante debe guardarse con el `persona` destino y, probablemente, sin arrastrar el `nombre`
tal cual (para no chocar con la regla de nombre único por persona -- aunque como es OTRA persona
técnicamente no colisiona, puede ser confuso tener "Menú 1" en dos personas por separado sin
dejarlo claro en la UI). El `objetivo_diario`/`estado`/`delta_diario` deben recalcularse contra el
objetivo de la persona destino, no copiarse tal cual -- los equivalentes de las recetas clonadas
casi seguro no van a cuadrar exacto con el objetivo de la nueva persona, y esa es justo la parte
que el usuario espera "ajustar después" (steppers ya existentes en "Menú del día", ninguna
herramienta nueva ahí). Probablemente vive como un botón "Clonar a otra persona" junto a "Abrir"
en el historial de "Menú del día", con un selector de persona destino.

##### Dependencies
Ninguna -- reutiliza mecanismos ya existentes de "Menú del día".

#### FR-007 · [STATUS: Shipped 0.19.0]
> **Shipped en 0.19.0 (2026-08-30)** — `st.expander("➕ Agregar un ingrediente suelto (sin
> receta)")` colapsado debajo del picker de recetas de cada tiempo, buscando en
> `cargar_nombres_alimentos()`. `_nueva_instancia_suelta()` crea una `RecetaInstancia` sintética
> de un solo ingrediente con `receta_id: None` (ver `schema.md`) -- reutiliza el mismo
> stepper/colapso que una receta normal. `_check_recetas_huerfanas()` en Configuración se ajustó
> para ignorar `receta_id: None` explícitamente. Ver `UI-BUILD-YOUR-MENU.md` → "Menú del día" 6.2
> y `CHANGELOG.md` 0.19.0.

**Title:** Agregar ingredientes sueltos directo a "Menú del día" (sin pasar por una receta)
**Date Requested:** 2026-08-30
**Status:** Proposed

##### Exec Description
A veces conviene comer un alimento suelto (ej. una fruta) sin que forme parte de ninguna receta
del banco -- poder agregarlo directo a un tiempo de "Menú del día", igual que se agrega una
receta, en vez de tener que crear una "receta" de un solo ingrediente en el banco solo para eso.

##### Eng Description
`dia["tiempos"][tiempo]` es una lista de `RecetaInstancia` (`instancia_id`, `receta_id`, `nombre`,
`ingredientes`) -- un ingrediente suelto encajaría como una `RecetaInstancia` sintética con un
solo ingrediente y sin `receta_id` real (o un `receta_id` sentinela tipo `None`/`"__suelto__"`
para no confundirse con una receta de verdad al buscar "dónde se usa"). Necesita un picker
separado del de recetas (buscar directo en `cargar_nombres_alimentos()`/`catalogo_alimentos` en
vez de en `cargar_recetas()`), con su propio stepper de equivalentes (reutiliza
`paso_equivalente()`/`escalar_cantidad()` igual que cualquier ingrediente ajustable). Revisar que
`_check_recetas_huerfanas()`/`_buscar_uso_de_receta()` en Configuración no truenen con instancias
sin `receta_id` real.

##### Dependencies
Ninguna.

#### FR-006
**Title:** Detector de posibles duplicados en el catálogo de ingredientes
**Date Requested:** 2026-08-29
**Status:** Proposed

##### Exec Description
En el Editor de ingredientes, un botón que compare los nombres del catálogo por similitud (no
exacta) y muestre pares sospechosos para revisar y fusionar con un clic, en vez de encontrarlos a
ojo mientras se usa la app.

##### Eng Description
Cierra `KC-001` de raíz (ej. "Aceite de oliva" vs "Aceite oliva"). La fusión ya existe en
`views/editor_ingredientes.py` (ver el flujo de colisión de nombre al renombrar) — esto solo
automatiza encontrar los candidatos, probablemente con una distancia de edición simple
(Levenshtein) sobre los nombres normalizados de `nutriguia/texto.py`.

##### Dependencies
Editor de ingredientes (Shipped en `FR-002`).

#### FR-005
**Title:** Duplicar un día ya guardado como punto de partida
**Date Requested:** 2026-08-29
**Status:** Proposed

##### Exec Description
Un botón "Duplicar" junto a "Abrir" en el historial de "Menú del día" (o "Empezar como ayer" al
abrir la página) que clona un día ya guardado en vez de armar todo desde cero.

##### Eng Description
Reutiliza casi tal cual `_instancia_desde_guardado()` de `views/menu_del_dia.py` — la pieza más
barata identificada en la revisión de producto de 2026-08-29 (ver historial de conversación; no
hay un documento aparte, este es el registro canónico).

##### Dependencies
Ninguna.

#### FR-004 · [STATUS: Shipped 0.20.0]
> **Shipped en 0.20.0 (2026-08-30)** — página nueva "Lista del súper" (`views/lista_super.py`, en
> "Tu día a día"). `st.multiselect` de personas (no un solo selectbox) para el caso de dos
> personas que hacen un solo súper. Suma una ocurrencia de cada ingrediente incluido por cada DÍA
> de la semana que use ese menú (`_ingredientes_de_la_semana()`, sobre `asignacion_semanal` +
> `menus_construidos`), consolidada por alimento con `sumar_por_grupo(ingredientes, "alimento",
> "equivalentes")` -- resultó no hacer falta una función `sumar_por_alimento()` nueva, esa función
> ya era lo bastante genérica. Agrupada por grupo SMAE (resuelto contra `catalogo_alimentos`, no
> contra `grupo_smae` de un ingrediente en particular) para mostrarse. "🖨️ Descargar HTML para
> imprimir" con `nutriguia/html_lista_super.py` (mismo patrón que `nutriguia/html_semanal.py`,
> con checkbox `☐` por alimento para tachar en el súper). No cubre todavía generar la lista sobre
> un solo día suelto sin depender de `asignacion_semanal` -- ver `UI-BUILD-YOUR-MENU.md` → "Lista
> del súper" para el detalle completo.

**Title:** Lista de súper generada
**Date Requested:** 2026-08-29
**Status:** Proposed

##### Exec Description
Un botón que suma los ingredientes de un día o de una semana planeada en una lista consolidada de
compras (ej. "Pollo: 90 g", "Tortilla: 6 piezas"), en vez de tener que releer cada receta.

##### Eng Description
Con `menus_construidos.nombre` + `asignacion_semanal` (ver `schema.md`, corregido 2026-08-29) ya
existe de dónde sacar "qué se come toda la semana": para cada día de la semana con un nombre
asignado, resolver el `menus_construidos` correspondiente (por `persona`+`nombre`), sumar sus
ingredientes reales (no solo el vector por grupo — hace falta una función nueva tipo
`sumar_por_alimento`, ver `nutriguia/validation.py` si se generaliza), y formatear la cantidad
total con `escalar_cantidad()`. También podría operar solo sobre un día de `menus_construidos`
sin esperar a tener una semana completa armada.

**Actualizado 2026-08-30, a pedido del usuario**: la selección de persona debe poder ser
**múltiple** (no una sola), para el caso de dos personas que viven juntas y hacen un solo súper —
sumar los ingredientes de ambas asignaciones semanales en una sola lista consolidada (mismo
alimento de Persona A y Persona B se suma en una sola línea, no dos separadas).

##### Dependencies
`menus_construidos.nombre`/`asignacion_semanal` (Shipped 2026-08-29, corregido el mismo día — ver
`CHANGELOG.md` 0.9.0) para la versión semanal; ninguna para una versión que solo opere sobre un
día de `menus_construidos`.

#### FR-003
**Title:** Fase 5 — pulido (semana completa, exportar imprimible, sugerencia automática de hueco)
**Date Requested:** 2026-08-24
**Status:** Parcialmente Shipped -- "exportar imprimible" salió en 0.12.0 (2026-08-29), adelantada
a pedido explícito del usuario como prueba, sin esperar al resto de la Fase 5. Las otras dos
(repetir semana completa, sugerencia automática de hueco) siguen bloqueadas a propósito.

##### Exec Description
Tres mejoras de pulido: repetir el flujo de día completo por semana (con aviso de repetición),
exportar un plan a formato imprimible, y sugerir automáticamente un ingrediente suelto del
catálogo cuando ningún combo del banco de recetas cuadra exacto con un objetivo.

##### Eng Description
Ver `BUILD-PLAN.md` → Fase 5 para el detalle de cada una. No empezar el resto sin haber usado la
Fase 4 en la vida real — puede cambiar qué vale la pena pulir primero.

> **"Exportar imprimible" shipped en 0.12.0** — `nutriguia/pdf_semanal.py` (ReportLab), botón en
> "Menú semanal". Ver `CHANGELOG.md` 0.12.0 y `UI-BUILD-YOUR-MENU.md` → "Menú semanal" para el
> detalle. Es una primera versión ("hagamos la prueba", palabras del usuario) -- falta ajustar
> tamaños/diseño según feedback de uso real antes de darla por terminada del todo.
>
> **Motor cambiado de PDF a HTML en 0.18.0 (2026-08-30)** — a pedido del usuario, que prefiere que
> EquiVale genere el HTML y usar el "Imprimir a PDF" de su propio navegador (control total de
> márgenes/escala). `nutriguia/pdf_semanal.py` (ReportLab) se retiró; `nutriguia/html_semanal.py`
> lo reemplaza con el mismo diseño visual. Ver `CHANGELOG.md` 0.18.0 y `UI-BUILD-YOUR-MENU.md` →
> "Del PDF al HTML".

##### Dependencies
Fase 4 (día completo + guardado + historial) — completa desde 2026-08-27.

#### FR-002 · [STATUS: Shipped 0.5.0]
> **Shipped en 0.5.0** — implementado como página nueva "Editor de ingredientes"
> (`views/editor_ingredientes.py`) en vez de dentro del editor de recetas: tabla del catálogo
> completo con edición/eliminación (con cascada de renombrado a `recetas`, ver
> `UI-BUILD-YOUR-MENU.md`), más el buscador "Agregar de SMAE" descrito abajo.
> `SMAE_CONSULTA.csv` se commiteó al repo (es información pública, ver nota de privacidad en
> `CLAUDE.md`) en vez de depender de que cada quien lo consiga aparte.

**Title:** "EquiVale Chef" — integración con `SMAE_CONSULTA.csv` para agregar alimentos nuevos al
catálogo desde el propio editor
**Date Requested:** 2026-08-24

##### Exec Description
Cuando un alimento nuevo no está en `catalogo_alimentos`, poder buscarlo en la tabla oficial SMAE
(`SMAE_CONSULTA.csv`) y fijar su equivalencia sin salir del editor de recetas.

##### Eng Description
Si el alimento tampoco está en `SMAE_CONSULTA.csv`, marcar `asuncion: true` y pedir confirmación
del criterio usado — mismo criterio que la regla 5 de `CLAUDE.md`. Ver `BUILD-PLAN.md` → "Ideas
para más adelante" para el detalle completo.

##### Dependencies
Editor de recetas (Fase 3.5) — ya construido, esto es la extensión pendiente.

#### FR-001
**Title:** Historial de versiones del objetivo por persona
**Date Requested:** 2026-08-27
**Status:** Proposed

##### Exec Description
Poder ver qué objetivo diario tenía una persona en una fecha pasada, no solo el vigente.

##### Eng Description
La página "Personas" (Fase 3.6) solo mantiene UN documento `objetivos` vigente por persona
(upsert in-place). El schema ya deja `vigente_desde` listo para esto, pero no se guarda
histórico de valores anteriores al hacer un nuevo upsert. Retomar solo si hace falta consultar
"qué objetivo tenía tal persona en tal fecha".

##### Dependencies
Ninguna — se puede implementar en cualquier momento cambiando el upsert por un insert +
`vigente_desde`/`vigente_hasta`.
