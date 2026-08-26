# EquiVale

Sistema personal de planeación de menús basado en **Equivalentes SMAE** (Sistema Mexicano de
Alimentos Equivalentes), para dos personas: **Dan** y **Pau**. La app ("Build your menu") arma el
día eligiendo recetas de un banco reutilizable y ajustando porciones en pasos de equivalente
completo, con validación en vivo de qué falta o sobra por grupo.

Repo privado, uso personal (1-2 usuarios concurrentes como máximo) — no está pensado para escalar
a muchos usuarios ni tiene login propio (ver nota de seguridad en `SETUP.md`).

## Estado actual

**Fases 0 a 3.5 completas** — Mongo corriendo, datos importados, `nutriguia/validation.py` con
34/34 tests en verde, app Streamlit multipágina ("Build your menu" + "Editor de recetas")
desplegada y corriendo en producción como servicio systemd. Sigue la Fase 4 (día completo +
guardado a `menus_construidos`). Ver el checklist completo en `BUILD-PLAN.md`.

## Documentación — leer en este orden

| Documento | Qué trae |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Contexto de dominio: personas, grupos SMAE, convenciones, reglas para construir/validar platillos |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Componentes del sistema, stack elegido y por qué, estructura de carpetas |
| [`SETUP.md`](SETUP.md) | Instalación paso a paso (MongoDB, Python, `.env`) y despliegue en el servidor |
| [`schema.md`](schema.md) | Forma exacta de cada colección de Mongo |
| [`VALIDATION.md`](VALIDATION.md) | Contrato exacto de `nutriguia/validation.py` (toda la aritmética de equivalentes) |
| [`UI-BUILD-YOUR-MENU.md`](UI-BUILD-YOUR-MENU.md) | Especificación de interacción de la app Streamlit |
| [`BUILD-PLAN.md`](BUILD-PLAN.md) | Orden de ejecución por fases, con criterio de "hecho" en cada una |

## Stack

MongoDB + Python (pymongo) + Streamlit + pytest. Toda la aritmética de equivalentes vive en un
solo módulo puro (`nutriguia/validation.py`), reutilizado por el import, los tests y la UI — ver
el razonamiento completo en `ARCHITECTURE.md`.

## Quick start

Instalación completa (incluye instalar MongoDB y dejar la app como servicio systemd) en
`SETUP.md`. Resumen para entorno ya instalado:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # editar MONGO_URI con las credenciales reales

python -m nutriguia.import_data   # carga catálogo, recetas, menús históricos y objetivos
pytest tests/ -v                  # 34/34 menús históricos deben validar en verde

streamlit run app.py
```

## Producción

La app corre desplegada como servicio systemd en un servidor Linux de la red local del usuario —
no hay que levantarla de cero. Para redesplegar cambios de código, ver "Redesplegar cambios de
código" al final de `SETUP.md` (`git pull` + `systemctl restart`).
