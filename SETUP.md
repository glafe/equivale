# Setup — instalación en la máquina Linux (para Claude Code)

Instrucciones para dejar corriendo MongoDB + el entorno Python en la máquina Linux a la que se
accede por SSH. Ejecutar en orden. Si algún paso falla, diagnosticar antes de continuar — no
saltarse pasos de verificación.

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

Los archivos fuente (`catalogo-alimentos.json`, `recetas.json`, `Json-outputs-sin-notas/*.json`)
deben copiarse a `data/` dentro del repo antes de este paso (vienen del Project de Claude o de la
carpeta `Nutri` del usuario en su máquina Windows — pedirle al usuario que los pase si no están).

```bash
python -m nutriguia.import_data
```

Este script (a escribir según `schema.md` y `BUILD-PLAN.md` fase 1) debe imprimir un resumen de
conteos por colección al terminar — usarlo para confirmar que la carga fue completa antes de
seguir a la fase de validación.

## 7. Correr los tests de validación

```bash
pytest tests/ -v
```

Todos los menús históricos deben validar en verde (ver `VALIDATION.md`). Si alguno falla, es una
señal de bug en `validation.py` o en el import — NO en los datos (los datos ya se validaron
manualmente antes de llegar aquí, ver `agosto26-dan-notas.md` en el Project).

## 8. Correr la app

```bash
streamlit run app.py
```

Por default Streamlit sirve en `localhost:8501`. Si se accede por SSH, abrir un túnel:
```bash
ssh -L 8501:localhost:8501 usuario@la-maquina-linux
```
y luego abrir `http://localhost:8501` en el navegador local.
