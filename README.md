# Crypto Portfolio Dashboard

Dashboard personal para analizar un portafolio de Binance: balances en tiempo real, historial de transacciones, análisis DCA de Bitcoin, P&L, ROI, IRR y gráficos de evolución temporal.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI (Python 3.12), SQLAlchemy 2.0 async |
| Base de datos | PostgreSQL 15 |
| Caché | Redis 7 |
| Scheduler | APScheduler (proceso separado) |
| Deploy | Docker Compose |

---

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose v2
- Claves de API de Binance (solo lectura es suficiente)

---

## Instalación rápida

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd crypto-portfolio
```

### 2. Crear el fichero de entorno

```bash
cp .env.example .env
```

Edita `.env` y rellena los valores obligatorios:

```bash
# Contraseña de la base de datos
POSTGRES_PASSWORD=una_contraseña_segura

# Clave para firmar los JWT — genera con:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<32_bytes_hex>

# Clave AES-256 para cifrar las API Keys de Binance en BD — genera con:
# python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
ENCRYPTION_KEY=<32_bytes_base64_urlsafe>

# Contraseña de acceso a la interfaz web
APP_PASSWORD=tu_contraseña_de_acceso
```

Los demás valores tienen defaults razonables y no es necesario cambiarlos para empezar.

### 3. Arrancar todos los servicios

```bash
docker compose up -d
```

Este comando:
1. Levanta PostgreSQL y Redis con health checks
2. Construye la imagen del API (Python)
3. Ejecuta las migraciones de Alembic automáticamente
4. Arranca el servidor FastAPI en el puerto 8000
5. Arranca el scheduler de sincronización
6. Construye y arranca el frontend Next.js en el puerto 3000

### 4. Abrir la aplicación

Accede a [http://localhost:3000](http://localhost:3000) e inicia sesión con la `APP_PASSWORD` que configuraste.

---

## Primera configuración — Añadir claves de Binance

Después del primer login, ve a **Ajustes** y añade tus claves de API de Binance:

- Ve a Binance → Gestión de API → Crear API
- Permisos necesarios: **solo lectura** (Enable Reading)
- No es necesario habilitar operaciones de trading ni retiros
- Copia la API Key y el Secret Key en los ajustes de la aplicación

Una vez guardadas las claves, pulsa **Sincronizar ahora** para importar tus transacciones y balances. La primera sincronización puede tardar unos minutos dependiendo del historial.

---

## Uso diario

La sincronización automática se ejecuta cada `SYNC_INTERVAL_MINUTES` (por defecto 5 minutos). También puedes forzarla manualmente desde cualquier página usando el botón de refresco en la barra superior.

### Secciones del dashboard

| Sección | Descripción |
|---------|-------------|
| **Overview** | Resumen ejecutivo: valor total, P&L, ROI, IRR, top activos y evolución 30 días |
| **Rendimiento** | Evolución temporal con selector de rango (7D / 30D / 90D / 1A / Todo) y drawdown máximo |
| **DCA Bitcoin** | Análisis de la estrategia DCA: sats acumuladas, precio medio de compra (VWAP), historial de compras |
| **Transacciones** | Listado completo de operaciones importadas desde Binance |
| **Fiscal** | (Próximamente) Informe de ganancias/pérdidas para declaración |
| **Ajustes** | Gestión de claves de API y preferencias |

Todos los valores monetarios se muestran en **EUR** (primario) con referencia en USD.

---

## Desarrollo local (sin Docker)

Si prefieres ejecutar los servicios directamente en tu máquina:

### Backend (FastAPI)

```bash
cd apps/api

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Variables de entorno (necesitas PostgreSQL y Redis corriendo localmente)
export DATABASE_URL=postgresql+asyncpg://portfolio:password@localhost:5432/portfolio
export DATABASE_SYNC_URL=postgresql+psycopg2://portfolio:password@localhost:5432/portfolio
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=<tu_secret_key>
export ENCRYPTION_KEY=<tu_encryption_key>
export APP_PASSWORD=<tu_contraseña>

# Ejecutar migraciones
alembic upgrade head

# Arrancar el servidor
uvicorn main:app --reload --port 8000
```

### Scheduler (sincronización automática)

```bash
cd apps/api
# Con el mismo entorno virtual y variables de entorno activos:
python -m sync.scheduler
```

### Frontend (Next.js)

```bash
cd apps/web

npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

El frontend estará disponible en [http://localhost:3000](http://localhost:3000).

---

## Comandos útiles

### Ver logs de un servicio

```bash
docker compose logs -f api        # logs del backend
docker compose logs -f scheduler  # logs del scheduler
docker compose logs -f web        # logs del frontend
```

### Reiniciar un servicio tras cambios

```bash
docker compose restart api
docker compose restart web
```

### Reconstruir imágenes (tras cambios en Dockerfile o dependencias)

```bash
docker compose up -d --build api
docker compose up -d --build web
```

### Migraciones de base de datos

```bash
# Aplicar todas las migraciones pendientes
docker compose exec api alembic upgrade head

# Crear una nueva migración
docker compose exec api alembic revision --autogenerate -m "descripcion_del_cambio"

# Ver el historial de migraciones
docker compose exec api alembic history

# Revertir la última migración
docker compose exec api alembic downgrade -1
```

### Tests del backend

```bash
docker compose exec api pytest tests/ -v

# Con cobertura
docker compose exec api pytest tests/ --cov=. --cov-report=term-missing
```

### Acceder a la base de datos

```bash
docker compose exec postgres psql -U portfolio -d portfolio
```

### Parar todos los servicios

```bash
docker compose down          # para los contenedores, conserva los datos
docker compose down -v       # para los contenedores y borra los volúmenes (¡borra todos los datos!)
```

---

## Estructura del proyecto

```
crypto-portfolio/
├── docker-compose.yml
├── .env.example
├── apps/
│   ├── api/                     # Backend FastAPI
│   │   ├── main.py              # Punto de entrada
│   │   ├── requirements.txt
│   │   ├── alembic/             # Migraciones de BD
│   │   ├── routers/             # Endpoints (/api/v1/*)
│   │   ├── services/            # Lógica financiera (FIFO, VWAP, IRR...)
│   │   ├── models/              # Modelos SQLAlchemy
│   │   ├── sync/                # Cliente Binance + scheduler
│   │   ├── core/                # Config, seguridad, dependencias
│   │   └── tests/
│   └── web/                     # Frontend Next.js
│       ├── app/                 # App Router (páginas)
│       ├── components/          # Componentes React
│       │   ├── charts/          # Gráficos Recharts
│       │   ├── dashboard/       # Widgets de cada sección
│       │   └── layout/          # Sidebar, topbar
│       └── lib/                 # Utils, formatters, tipos
└── docs/
    └── SRS.md                   # Especificación de requisitos
```

---

## Variables de entorno — referencia completa

| Variable | Obligatoria | Default | Descripción |
|----------|-------------|---------|-------------|
| `POSTGRES_PASSWORD` | Sí | — | Contraseña de PostgreSQL |
| `SECRET_KEY` | Sí | — | Clave para firmar JWT (32 bytes hex) |
| `ENCRYPTION_KEY` | Sí | — | Clave AES-256 para cifrar API Keys (base64 URL-safe) |
| `APP_PASSWORD` | Sí | — | Contraseña de acceso a la web |
| `POSTGRES_DB` | No | `portfolio` | Nombre de la base de datos |
| `POSTGRES_USER` | No | `portfolio` | Usuario de PostgreSQL |
| `POSTGRES_PORT` | No | `5432` | Puerto de PostgreSQL |
| `REDIS_PORT` | No | `6379` | Puerto de Redis |
| `API_PORT` | No | `8000` | Puerto expuesto del backend |
| `WEB_PORT` | No | `3000` | Puerto expuesto del frontend |
| `APP_ENV` | No | `production` | `development` o `production` |
| `LOG_LEVEL` | No | `INFO` | Nivel de logs del backend |
| `SYNC_INTERVAL_MINUTES` | No | `5` | Frecuencia de sync (mínimo 5) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Duración del token JWT |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | URL del API accesible desde el navegador |
| `BINANCE_API_BASE_URL` | No | `https://api.binance.com` | URL de la API de Binance (permite testnet) |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Orígenes CORS permitidos (separados por coma) |

---

## Reglas de seguridad

- Las API Keys de Binance se almacenan **cifradas** en la BD con AES-256-GCM
- El fichero `.env` nunca debe commitearse al repositorio
- La aplicación está diseñada para **uso personal**: un solo usuario, sin registro público
- El frontend nunca llama directamente a Binance; todo pasa por el backend
- En producción, el API desactiva automáticamente `/docs` y `/redoc`
