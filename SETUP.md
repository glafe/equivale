# Setup — instalación en la máquina Linux (para Claude Code)

Instrucciones para dejar corriendo el entorno Python en la máquina Linux a la que se accede por
SSH. Ejecutar en orden. Si algún paso falla, diagnosticar antes de continuar — no saltarse pasos
de verificación.

**Ya ejecutado una vez** (2026-08-24, migrado de MongoDB a SQLite el 2026-09-04 — ver
`BUGS.md` `KC-002` y `CHANGELOG.md` para el porqué) — este documento ahora sirve doble propósito:
la receta original de instalación, Y la referencia de cómo quedó configurado el servidor real. Si
el servidor ya existe y solo se necesita redesplegar código nuevo, ir directo a la sección
"Redesplegar cambios de código" al final.

**No hay una base de datos que instalar.** EquiVale usa SQLite (`sqlite3`, incluido en la
librería estándar de Python) — un archivo único en `data/equivale.db`, sin servicio ni
dependencia del sistema operativo. Esto es justo lo que hace posible instalar EquiVale igual en
Windows/Linux/Mac sin las fricciones que sí tenía MongoDB (ver nota histórica al final de este
documento).

## 1. Entorno Python

```bash
cd equivale   # o el nombre que tenga el repo clonado
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` (crear si no existe):
```
streamlit>=1.38
python-dotenv>=1.0
pytest>=8.0
```

## 2. `.env` (opcional — solo si se quiere una ruta distinta a la default)

```
SQLITE_PATH=data/equivale.db
```

Si se omite `.env` por completo, `nutriguia/db.py` usa `data/equivale.db` por default —
suficiente para la mayoría de los casos. Confirmar que `.gitignore` incluye `.env`, `.venv/` y
`data/*` antes del primer commit (ya están, si se clonó el repo tal cual).

## 3. Cargar los datos iniciales

**El repo es público desde 2026-08-27 — `data/` está en `.gitignore` y NO se trae con
`git clone`.** Para arrancar con datos propios ya reconciliados (no es necesario para una
instalación nueva desde cero — sin estos archivos, `import_data.py` simplemente no encuentra nada
que cargar y la app arranca con catálogo/recetas vacíos, listos para construirse desde "Editor de
ingredientes"/"Editor de recetas"), conseguir estos archivos aparte (fuera de git) y ponerlos en
`data/`:
- `Json-outputs-sin-notas/catalogo-alimentos.json`
- `recetas.json`
- `personas_y_objetivos.json` — `{"vigente_desde": "YYYY-MM-DD", "personas": [{"persona": ...,
  "equivalentes_diarios": [{"grupo": ..., "cantidad": ...}, ...]}, ...]}` (ver
  `nutriguia/import_data.py` → `importar_personas_y_objetivos` para el formato exacto)

```bash
python -m nutriguia.import_data
```

Imprime un resumen de conteos al terminar (catalogo_alimentos, recetas, personas, objetivos) —
usarlo para confirmar que la carga fue completa. Si falta `personas_y_objetivos.json` no truena,
solo avisa y deja personas/objetivos como estaban. **Ojo**: desde que existe el Editor de recetas,
este comando se niega a sobreescribir `recetas` si ya tiene datos (para no borrar ediciones hechas
en vivo) — solo lo hace con `--force-recetas` explícito. Ver `ARCHITECTURE.md` → decisión 3.

## 4. Correr los tests

```bash
pytest tests/ -v
```

`nutriguia/validation.py` corre contra los menús históricos si `data/Json-outputs-sin-notas/`
existe (se salta si no); todo lo demás (incluida `nutriguia/db.py`, contra
`sqlite3.connect(":memory:")`) corre siempre, en cualquier clon del repo público, sin datos reales.

## 5. Correr la app como servicio systemd (así quedó desplegada, no a mano)

`streamlit run app.py` a mano funciona para probar, pero no sobrevive un reinicio del servidor ni
se reinicia solo si truena. Se dejó como servicio systemd:

```bash
sudo tee /etc/systemd/system/equivale.service <<'EOF'
[Unit]
Description=EquiVale Streamlit App
After=network.target

[Service]
Type=simple
User=glafe
WorkingDirectory=/home/glafe/equivale
ExecStart=/home/glafe/equivale/.venv/bin/streamlit run app.py --server.headless true --server.address 0.0.0.0 --server.port 8501
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable equivale
sudo systemctl start equivale
sudo systemctl status equivale   # confirmar "active (running)"
```

`--server.address 0.0.0.0` (no `127.0.0.1`) para que sea accesible desde cualquier dispositivo de
la red local del usuario en `http://192.168.68.59:8501`, sin necesidad de túnel SSH. Si hay
firewall (`ufw status`), abrir el puerto: `sudo ufw allow 8501/tcp`.

**Servidor actual**: Ubuntu 24.04 en `192.168.68.59`, usuario `glafe`. Acceso SSH por llave (sin
password) desde la máquina de desarrollo — ver `~/.ssh/config` local para el alias, si existe. Este
IP es de red local (LAN), no expuesto a internet por sí solo.

**Nota de seguridad**: la app no tiene login propio — cualquiera en la red local puede entrar y
guardar/editar. Aceptable para uso doméstico personal; si el router llegara a reenviar ese puerto a
internet quedaría expuesta públicamente (fuera del control de esta app).

### Redesplegar cambios de código

El servidor clona el repo por SSH con una **deploy key de solo lectura** (no puede hacer push) — el
flujo normal es: editar y pushear desde la máquina de desarrollo, y en el servidor:

```bash
cd ~/equivale
git pull
sudo systemctl restart equivale   # systemd no hace hot-reload del código
```

Si el cambio afecta `requirements.txt`, correr `source .venv/bin/activate && pip install -r
requirements.txt` antes del restart. Verificar que levantó bien:
`curl -sf http://localhost:8501/_stcore/health` debe regresar `ok`.

**Desde 2026-08-27, `sudo systemctl restart|status equivale` no pide contraseña** (regla
`NOPASSWD` agregada a propósito en `visudo` para agilizar el ciclo editar→probar en vivo durante
una sesión de trabajo — acotada a esos dos comandos sobre ese único servicio, no sudo genérico).
Si se reinstala el servidor desde cero, agregar de nuevo algo como:
```
<usuario> ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart equivale, /usr/bin/systemctl status equivale
```
`journalctl -u equivale` (sin sudo) también funciona para ver logs/warnings de la app sin pedir
contraseña, salvo que el sistema tenga journald configurado para requerir privilegios de lectura.

## Nota histórica: de MongoDB a SQLite (2026-09-04)

Hasta el 2026-09-04, EquiVale corría sobre MongoDB Community Edition instalado en el mismo
servidor, con un workaround de kernel necesario (`GLIBC_TUNABLES=glibc.pthread.rseq=1`, ver
`BUGS.md` `KC-002`) porque MongoDB 8.x tiene una incompatibilidad sin resolver con kernels Linux
≥6.19 (bug de TCMalloc/rseq, sin fecha de fix por parte de Google/MongoDB). Se migró a SQLite
para poder eventualmente distribuir EquiVale como app instalable en Windows/Linux sin depender de
un servicio de base de datos aparte en cada máquina.

El corte de producción se hizo con `scripts/migraciones/2026-09-04-mongo-a-sqlite.py` (no
destructivo, solo lee de Mongo) — reporta conteos por tabla antes/después para verificar que la
copia fue 1:1. Después de verificar la app funcionando sobre SQLite, Mongo se detuvo/deshabilitó
(`sudo systemctl stop mongod && sudo systemctl disable mongod`, reversible) como red de seguridad
temporal antes de desinstalarlo por completo.
