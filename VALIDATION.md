# Validación — contrato de `nutriguia/validation.py`

Módulo puro (sin Mongo, sin Streamlit, sin I/O) que implementa TODA la aritmética de equivalentes.
Se importa desde `import_data.py`, `tests/test_validation.py`, y `app.py`. No duplicar esta lógica
en ningún otro lado del código.

## Convención de signo (importante — fijar esto primero)

`delta = objetivo - actual`, por grupo:
- **positivo** → falta ese equivalente (el usuario va corto, tiene que agregar)
- **negativo** → se pasó (el usuario tiene que quitar)
- **cero** → exacto

Esta convención debe ser consistente en todo el código y en la UI (ver `UI-BUILD-YOUR-MENU.md`).

## Funciones requeridas

```python
def sumar_por_grupo(items: list[dict], campo_grupo: str, campo_cantidad: str) -> dict[str, int]:
    """
    Suma 'campo_cantidad' agrupando por 'campo_grupo'. Ignora items donde campo_grupo es None
    (alimentos 'libres'). NO usar un dict-comprehension que sobreescriba llaves repetidas —
    agregar con +=. Ejemplo de uso:
        sumar_por_grupo(tiempo["equivalentes"], "grupo", "cantidad")
        sumar_por_grupo(ingredientes, "grupo_smae", "equivalentes")
    """

def delta_objetivo(objetivo: dict[str, int], actual: dict[str, int]) -> dict[str, int]:
    """
    objetivo - actual, por grupo. Incluye la UNION de llaves de ambos dicts (un grupo ausente en
    uno de los dos cuenta como 0), aunque el resultado sea 0 para ese grupo.
    Ejemplo: objetivo={"AOA":4,"Verdura":2}, actual={"AOA":4,"Cereal":1}
          -> {"AOA":0, "Verdura":2, "Cereal":-1}
    """

GRUPOS_INTERCAMBIABLES: list[tuple[str, str]] = [("Cereal", "Leguminosa")]
    # Fijo (no varía por persona/periodo) -- ver comentario junto a la constante en el código.

def ajustar_delta_por_intercambios(delta: dict[str, int], pares: list[tuple[str, str]] = GRUPOS_INTERCAMBIABLES) -> dict[str, int]:
    """
    Redistribuye `delta` (salida de `delta_objetivo()`) entre pares de grupos intercambiables --
    "un cereal puede ser intercambiable por 1 leguminosa" (2026-08-30, a pedido del usuario). Si un
    grupo del par tiene delta positivo (falta) y el otro negativo (excedido), usa el excedente del
    segundo para cubrir parte o todo el faltante del primero, hasta agotar el menor de los dos en
    valor absoluto. No hace nada si ambos tienen el mismo signo (no hay excedente que redirigir) o
    si algún grupo del par no aparece en `delta`. Devuelve un delta NUEVO, no muta el original.
    Ejemplo: delta={"Cereal":2,"Leguminosa":-1} -> {"Cereal":1,"Leguminosa":0}
    El orden del par no importa -- el excedente puede estar en cualquiera de los dos.
    """

def es_exacto(delta: dict[str, int]) -> bool:
    """True si todos los valores de delta son 0."""

def estado_por_grupo(delta: dict[str, int]) -> dict[str, str]:
    """
    Por grupo: "exacto" si delta==0, "falta" si delta>0, "excedido" si delta<0.
    Esto es lo que la UI pinta en verde/amarillo/rojo (ver UI-BUILD-YOUR-MENU.md).
    """

def validar_tiempo(tiempo: dict) -> tuple[bool, dict]:
    """
    Reimplementación formal del validate() usado en todos los build scripts históricos:
    compara tiempo["equivalentes"] (declarado) contra la suma de
    tiempo["platillos"][*]["ingredientes"][*] (real). Regresa (es_valido, delta_por_grupo).
    """

def validar_menu(menu: dict) -> tuple[bool, dict, list[tuple[str, dict]]]:
    """
    Compara menu["equivalentes_diarios"] contra la suma de todos los tiempos.
    Regresa (es_valido_dia, delta_diario, [(nombre_tiempo, delta_tiempo) para cada tiempo inválido]).
    """

def paso_equivalente(alimento: str, catalogo_por_nombre: dict) -> str:
    """
    Dado el nombre de un alimento (ya normalizado, ver 'recetas' en schema.md) y el catálogo
    aplanado {alimento: {grupo, cantidad_por_equivalente, asuncion}}, regresa el
    'cantidad_por_equivalente' de ese alimento (ej. "30 g", "1/2 taza", "10 piezas") — esto es
    literalmente CUÁNTO representa UN paso del stepper +/- en la UI para ese ingrediente
    específico. Si el alimento no está en el catálogo (ej. "Fruta suelta" placeholder, o un
    ingrediente compuesto como "Nopal y Pimiento"), regresar None — esos ingredientes no son
    ajustables por stepper en la UI, se agregan/quitan completos.
    """

def fusionar_ingredientes_duplicados(ingredientes: list[dict]) -> list[dict]:
    """
    Colapsa ingredientes con el mismo 'alimento' (2+ ocurrencias) en uno solo, sumando sus
    'equivalentes' -- no cambia el total por grupo (misma suma repartida en 1 fila en vez de N),
    así que es seguro aplicarla sin revisar caso por caso. 'opcional'/'bloqueado'/'asuncion' quedan
    en True si CUALQUIER ocurrencia los tenía en True; 'cantidad'/'grupo_smae' se toman de la
    primera ocurrencia. Preserva el orden de primera aparición. Usada en `views/configuracion.py`
    y `views/editor_ingredientes.py` -- reemplazar el nombre de un ingrediente huérfano por uno
    que la receta YA tenía dejaba dos filas con el mismo 'alimento' en vez de fusionarlas
    (detectado 2026-08-30).
    """

def renombrar_ingrediente_en_menu_guardado(documento: dict, nombre_viejo: str, nombre_nuevo: str) -> bool:
    """
    Renombra 'nombre_viejo' -> 'nombre_nuevo' dentro de un 'menus_construidos' YA GUARDADO
    (mutado in place, ver schema.md -- un día guardado es un snapshot completo, no una referencia
    viva al banco de recetas). Devuelve True si 'nombre_viejo' aparecía en algún ingrediente (y ya
    mutó 'documento'), False si no había nada que hacer. Aplica 'fusionar_ingredientes_duplicados()'
    por instancia (mismo caso que arriba: la receta ya podía tener un ingrediente con el nombre
    nuevo) y recalcula 'actual'/'actual_diario'/'delta_diario'/'estado' -- 'objetivo_diario' NO se
    toca, sigue siendo el snapshot original de cuando se guardó ese día. Usada en
    `views/configuracion.py` y `views/editor_ingredientes.py` junto con
    `fusionar_ingredientes_duplicados()` -- limpiar/renombrar un alimento del catálogo solo tocaba
    `recetas`, dejando el nombre viejo huérfano para siempre en cualquier día ya guardado que lo
    usara (BUG-013, detectado 2026-08-30: "Leche"/"Leche semi" fusionadas a "Leche descremada" en
    el catálogo y en `recetas`, pero "Lista del súper" las seguía mostrando como "Sin grupo /
    libre" en vez de AOA porque los días ya guardados nunca se tocaron).
    """
```

## Regla de prueba de regresión (obligatoria antes de tocar la UI)

`tests/test_validation.py` debe cargar CADA archivo de `data/Json-outputs-sin-notas/*.json`
(excepto `catalogo-alimentos.json`), correr `validar_menu()` sobre cada `menu` de cada archivo, y
afirmar que los 17 archivos × 2 menús = 34 variantes dan `es_valido_dia == True`. Estos datos ya
fueron validados a mano uno por uno durante la reconciliación (ver `agosto26-dan-notas.md` en el
Project) — si algo aquí falla, el bug está en `validation.py`, no en los datos.

## Ejemplo end-to-end

```python
tiempo_objetivo = {"AOA": 4, "Cereal": 2, "Verdura": 2}
receta_elegida = {  # "Ceviche de atún" v2, ver recetas.json
    "vector_equivalentes": {"AOA": 4, "Cereal": 1, "Verdura": 1}
}
actual = receta_elegida["vector_equivalentes"]
delta = delta_objetivo(tiempo_objetivo, actual)
# delta == {"AOA": 0, "Cereal": 1, "Verdura": 1}  -> faltan 1 Cereal y 1 Verdura
estado = estado_por_grupo(delta)
# {"AOA": "exacto", "Cereal": "falta", "Verdura": "falta"}
```

El usuario ahora usa el stepper +/- sobre "Galleta Salma" (Cereal) para subir de 3pza (1
equivalente) a 6pza (2 equivalentes) — `paso_equivalente("Galleta Salma", catalogo)` le dice a la
UI que un paso son "3 piezas (1 paquetito)" — y agrega otro platillo o ajusta Pico de gallo para
cubrir el Verdura faltante. Cuando `delta` da todo ceros, `es_exacto(delta) == True` y la UI
habilita "guardar" sin advertencia.
