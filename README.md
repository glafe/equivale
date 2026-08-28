# EquiVale

**Versión actual: `0.5.1`** (ver [`CHANGELOG.md`](CHANGELOG.md) — [Versionado Semántico](https://semver.org/lang/es/))

Sistema personal de planeación de menús basado en **Equivalentes SMAE** (Sistema Mexicano de
Alimentos Equivalentes), para dos personas. La app ("Build your menu") arma el día eligiendo
recetas de un banco reutilizable y ajustando porciones en pasos de equivalente completo, con
validación en vivo de qué falta o sobra por grupo.

Código abierto/público, uso personal (1-2 usuarios concurrentes como máximo) — no está pensado para
escalar a muchos usuarios ni tiene login propio (ver nota de seguridad en `SETUP.md`). Los datos
reales de nutrición/menús de las personas que lo usan NO viven en este repo — ver `.gitignore` y
la nota de privacidad en `CLAUDE.md`.

## Estado actual

**Fases 0 a 4 completas** — Mongo corriendo, datos importados, `nutriguia/validation.py` con
35/35 tests en verde (más una suite adicional sobre datos sintéticos, `tests/test_validation_samples.py`,
que corre incluso en un clon fresco del repo sin los datos reales), app Streamlit multipágina
("Build your menu", "Editor de recetas", "Personas") desplegada y corriendo en producción como
servicio systemd, con día completo + guardado por fecha + historial. Sigue la Fase 5 (pulido,
solo tras uso real). Ver el checklist completo en `BUILD-PLAN.md`.

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
| [`CHANGELOG.md`](CHANGELOG.md) | Qué cambió y cuándo, por versión |
| [`BUGS.md`](BUGS.md) | Bugs, límites conocidos y feature requests, con detalle técnico |

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
pytest tests/ -v                  # 35/35 en verde con datos reales; sin ellos, test_validation.py
                                   # se salta y solo corre test_validation_samples.py (datos ficticios)

streamlit run app.py
```

## Producción

La app corre desplegada como servicio systemd en un servidor Linux de la red local del usuario —
no hay que levantarla de cero. Para redesplegar cambios de código, ver "Redesplegar cambios de
código" al final de `SETUP.md` (`git pull` + `systemctl restart`).
