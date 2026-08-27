# Setup — instalación en la máquina Linux (para Claude Code)

Instrucciones para dejar corriendo MongoDB + el entorno Python en la máquina Linux a la que se
accede por SSH. Ejecutar en orden. Si algún paso falla, diagnosticar antes de continuar — no
saltarse pasos de verificación.

**Ya ejecutado una vez** (2026-08-24) — este documento ahora sirve doble propósito: la receta
original de instalación, Y la referencia de cómo quedó configurado el servidor real (pasos 1 y 8
incluyen notas de gotchas/decisiones ya resueltas). Si el servidor ya existe y solo se necesita
redesplegar código nuevo, ir directo a la sección "Redesplegar cambios de código" en el paso 8.

## 0. Detectar la distro antes de instalar nada

```bash
cat /etc/os-release
```

Los comandos de abajo son para **Debian/Ubuntu** (`apt`). Si la distro es RHEL/Fedora/Rocky
(`dnf`/`yum`) o Arch (`pacman`), traducir los mismos pasos al gestor de paquetes correspondiente y
a la guía oficial de instalación de MongoDB para esa distro — no asumir `apt` sin haber
confirmado la distro primero.

## 1. Instalar MongoDB Community Edition (Debian/Ubuntu)

```bash
# Importar la llave GPG oficial de MongoDB
curl -fsSL https://pgp.mongodb.com/server-8.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor

# Agregar el repo (ajustar 'jammy'/'noble'/etc. según $VERSION_CODENAME de /etc/os-release)
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/8.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list

sudo apt update
sudo apt install -y mongodb-org

# Levantar el servicio y dejarlo persistente entre reinicios
sudo systemctl start mongod
sudo systemctl enable mongod
sudo systemctl status mongod   # confirmar "active (running)" antes de seguir
```

Si `apt install` falla por falta de `gnupg`/`curl`, instalar esos dos primero
(`sudo apt install -y gnupg curl`) y reintentar.

**Gotcha real encontrado (2026-08-24)**: en kernels Linux 6.19 a 7.0.13, `mongod` se niega a
arrancar (`MongoDB cannot start: Linux kernel versions 6.19 and newer has a known incompatibility`)
por un bug de TCMalloc/rseq — afecta a MongoDB 8.0.x en cualquier instalación (paquete, Docker,
etc.), no es específico de esta máquina. Verificar con `uname -r` si el kernel cae en ese rango. Si
`systemctl status mongod` muestra `Failed with result 'exit-code'` después de instalar, revisar
`journalctl -u mongod` — si aparece ese mensaje, el workaround (sin necesitar tocar el kernel) es:

```bash
sudo mkdir -p /etc/systemd/system/mongod.service.d
sudo tee /etc/systemd/system/mongod.service.d/override.conf <<'EOF'
[Service]
Environment=GLIBC_TUNABLES=glibc.pthread.rseq=1
EOF
sudo systemctl daemon-reload
sudo systemctl restart mongod
```

(Ya aplicado en el servidor actual — dejarlo documentado por si se reinstala Mongo o se migra a otra
máquina con un kernel en ese rango. Kernel 7.0.14+ ya no lo necesita.)

## 2. Verificar que Mongo responde

```bash
mongosh --eval "db.runCommand({ ping: 1 })"
```

Debe regresar `{ ok: 1 }`. Si `mongosh` no está instalado, viene en el paquete
`mongodb-mongosh` — `sudo apt install -y mongodb-mongosh`.

## 3. Crear usuario de aplicación (no usar el admin/sin auth en producción-personal tampoco)

```bash
mongosh <<'EOF'
use nutriguia
db.createUser({
  user: "nutriguia_app",
  pwd: "CAMBIAR_ESTO",   // generar un password real, no dejar el placeholder
  roles: [ { role: "readWrite", db: "nutriguia" } ]
})
EOF
```

Guardar el password generado en `.env` (paso 5) — nunca en un archivo commiteado a git.

## 4. Entorno Python

```bash
cd nutri-guia   # o el nombre que tenga el repo clonado
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` (crear si no existe):
```
pymongo>=4.8
streamlit>=1.38
python-dotenv>=1.0
pytest>=8.0
```

## 5. `.env` (nunca commitear — agregar a `.gitignore`)

Crear `.env` en la raíz del repo:
```
MONGO_URI=mongodb://nutriguia_app:CAMBIAR_ESTO@localhost:27017/nutriguia
MONGO_DB=nutriguia
```

Confirmar que `.gitignore` incluye `.env` y `.venv/` antes del primer commit.

## 6. Cargar los datos iniciales

**El repo es público desde 2026-08-27 — `data/` está en `.gitignore` y NO se trae con
`git clone`.** Hay que conseguir estos archivos aparte (fuera de git, ej. una copia local o un
respaldo privado) y ponerlos en `data/` antes de este paso:
- `Json-outputs-sin-notas/catalogo-alimentos.json`
- `Json-outputs-sin-notas/*.json` (17 archivos de menús históricos)
- `recetas.json`
- `personas_y_objetivos.json` — `{"vigente_desde": "YYYY-MM-DD", "personas": [{"persona": ...,
  "equivalentes_diarios": [{"grupo": ..., "cantidad": ...}, ...]}, ...]}` (ver
  `nutriguia/import_data.py` → `importar_personas_y_objetivos` para el formato exacto)

```bash
python -m nutriguia.import_data
```

Imprime un resumen de conteos por colección al terminar (17 menús, 159 recetas, ~80 alimentos, 2
personas, 2 objetivos) — usarlo para confirmar que la carga fue completa. Si falta
`personas_y_objetivos.json` no truena, solo avisa y deja esas dos colecciones como estaban. **Ojo**:
desde que existe el Editor de recetas, este comando se niega a sobreescribir `recetas` si ya tiene
datos (para no borrar ediciones hechas en vivo) — solo lo hace con `--force-recetas` explícito. Ver
`ARCHITECTURE.md` → decisión 3.

## 7. Correr los tests de validación

```bash
pytest tests/ -v
```

Todos los menús históricos deben validar en verde (ver `VALIDATION.md`). Si alguno falla, es una
señal de bug en `validation.py` o en el import — NO en los datos (los datos ya se validaron
manualmente antes de llegar aquí, ver `agosto26-dan-notas.md` en el Project).

## 8. Correr la app como servicio systemd (así quedó desplegada, no a mano)

`streamlit run app.py` a mano funciona para probar, pero no sobrevive un reinicio del servidor ni
se reinicia solo si truena. Se dejó como servicio systemd, igual patrón que `mongod`:

```bash
sudo tee /etc/systemd/system/equivale.service <<'EOF'
[Unit]
Description=EquiVale Streamlit App
After=network.target mongod.service

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
