**BINANCE PORTFOLIO DASHBOARD**

Software Requirements Specification (SRS)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Versión 1.0

Febrero 2026

*Estado: Borrador para desarrollo*


# **1. Introducción y Visión General del Proyecto**
## **1.1 Propósito del Documento**
Este documento es la Especificación de Requisitos de Software (SRS) para el proyecto Binance Portfolio Dashboard, un sistema personal de gestión y análisis de portafolio de criptomonedas. Define exhaustivamente los requisitos funcionales, no funcionales, restricciones de diseño, casos de uso y arquitectura técnica necesarios para que cualquier agente de desarrollo pueda implementar el sistema sin ambigüedad.

## **1.2 Alcance del Sistema**
El sistema consiste en una aplicación web full-stack de uso personal que se conecta a la API de Binance para obtener datos del portafolio del usuario (balances, historial de transacciones, trades, depósitos, retiros y datos de precios), los almacena en una base de datos propia para minimizar llamadas a la API, y expone dashboards interactivos con métricas avanzadas de rendimiento, análisis de DCA (Dollar Cost Averaging) y analítica histórica.

## **1.3 Objetivos de Negocio**
- Ofrecer al usuario una visión completa y en tiempo near-real de su portafolio de criptomonedas en Binance.
- Reducir la dependencia de llamadas directas a la API de Binance mediante caché persistente en base de datos propia.
- Analizar el rendimiento de estrategias DCA sobre Bitcoin y otros activos a lo largo del tiempo.
- Calcular métricas financieras avanzadas: P&L realizado/no realizado, ROI, IRR, valor promedio de compra, etc.
- Visualizar la evolución del portafolio con granularidad configurable (diaria, semanal, mensual, anual).

## **1.4 Partes Interesadas**
- Usuario final: propietario del portafolio (único usuario del sistema, uso personal).
- API de Binance: fuente de datos externa (Binance REST API v3).
- Agentes de desarrollo: destinatarios de este documento para la implementación.

## **1.5 Definiciones y Acrónimos**

|**DCA**|Dollar Cost Averaging — estrategia de compra periódica de un activo a precio de mercado independientemente del mismo.|
| :- | :- |

|**P&L**|Profit and Loss — ganancia o pérdida, realizada o no realizada.|
| :- | :- |

|**ROI**|Return on Investment — porcentaje de retorno sobre el capital invertido.|
| :- | :- |

|**IRR**|Internal Rate of Return — tasa interna de retorno, ajustada por timing de flujos de caja.|
| :- | :- |

|**API Key**|Par de claves (API Key + Secret) de Binance con permisos de lectura únicamente.|
| :- | :- |

|**Near-real-time**|Datos actualizados con un desfase máximo configurable (por defecto 5 minutos).|
| :- | :- |


# **2. Requisitos Funcionales**
## **2.1 Módulo de Configuración y Autenticación**
### **RF-01 — Gestión de API Keys de Binance**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RF-01.1**|ALTA|El sistema debe permitir al usuario introducir, guardar y actualizar su API Key y API Secret de Binance de forma segura (cifrado en reposo con AES-256 o equivalente).|
|**RF-01.2**|ALTA|El sistema debe validar las credenciales contra la API de Binance al guardarlas, verificando que tienen permisos de lectura y que no tienen permisos de trading ni de retiro.|
|**RF-01.3**|ALTA|El sistema debe mostrar el estado de la conexión con la API (activa, error de clave, límite de rate excedido).|
|**RF-01.4**|MEDIA|El sistema debe permitir configurar múltiples cuentas de Binance (subaccounts) y agrupar datos entre ellas.|
|**RF-01.5**|ALTA|El sistema debe proporcionar autenticación de acceso a la propia aplicación web mediante usuario/contraseña o pin, ya que contiene información financiera sensible.|

## **2.2 Módulo de Sincronización y Caché de Datos**
### **RF-02 — Sincronización con la API de Binance**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RF-02.1**|ALTA|El sistema debe sincronizar automáticamente los balances actuales de todas las monedas del usuario a intervalos configurables (mínimo 5 minutos).|
|**RF-02.2**|ALTA|El sistema debe importar el historial completo de transacciones desde el inicio de la cuenta: trades (compras/ventas), depósitos en fiat y cripto, retiros, conversiones Binance Convert y pagos P2P.|
|**RF-02.3**|ALTA|El sistema debe almacenar todos los datos importados en la base de datos local y solo consultar la API de Binance para datos que no existan o que estén desactualizados.|
|**RF-02.4**|ALTA|El sistema debe gestionar el rate limiting de Binance de forma transparente, respetando los límites de peso de peticiones (request weight) y reintentando con backoff exponencial.|
|**RF-02.5**|ALTA|El sistema debe realizar sincronización incremental: solo pedir a la API datos posteriores al último timestamp registrado en la base de datos, no re-descargar datos históricos ya existentes.|
|**RF-02.6**|MEDIA|El sistema debe importar precios históricos de OHLCV (klines) de todos los pares relevantes del portafolio para calcular valoraciones históricas sin depender de llamadas en tiempo real.|
|**RF-02.7**|BAJA|El sistema debe mostrar un log de sincronizaciones con timestamps, número de registros importados y errores ocurridos.|
|**RF-02.8**|MEDIA|El sistema debe permitir forzar una re-sincronización manual completa o parcial desde la UI.|

## **2.3 Módulo de Análisis de Portafolio**
### **RF-03 — Métricas de Rendimiento del Portafolio**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RF-03.1**|ALTA|El sistema debe calcular y mostrar el valor total actual del portafolio en USD, EUR y BTC.|
|**RF-03.2**|ALTA|El sistema debe calcular el capital total invertido (suma de todos los depósitos de fiat netos de retiros de fiat).|
|**RF-03.3**|ALTA|El sistema debe calcular el P&L total no realizado (valor actual menos capital invertido) en valor absoluto y en porcentaje.|
|**RF-03.4**|ALTA|El sistema debe calcular el P&L realizado histórico (ganancias/pérdidas de trades ya cerrados).|
|**RF-03.5**|ALTA|El sistema debe mostrar el ROI total del portafolio desde el inicio.|
|**RF-03.6**|MEDIA|El sistema debe calcular la IRR (tasa interna de retorno) del portafolio, ajustada por el timing de los flujos de caja de cada depósito/retiro.|
|**RF-03.7**|ALTA|El sistema debe calcular el rendimiento por activo: valor actual, porcentaje del portafolio, precio medio de compra, P&L en USD y % por cada moneda.|
|**RF-03.8**|ALTA|El sistema debe mostrar la evolución histórica del valor total del portafolio con granularidad diaria, semanal, mensual y anual.|
|**RF-03.9**|MEDIA|El sistema debe calcular métricas de riesgo básicas: drawdown máximo, volatilidad (desviación estándar de retornos diarios), ratio de Sharpe simplificado.|
|**RF-03.10**|BAJA|El sistema debe comparar el rendimiento del portafolio contra benchmarks: precio de BTC, ETH, y un índice hipotético de DCA puro en BTC.|

## **2.4 Módulo de Análisis DCA**
### **RF-04 — Seguimiento de estrategia DCA en Bitcoin**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RF-04.1**|ALTA|El sistema debe identificar y agrupar automáticamente todas las compras de BTC del historial como eventos DCA.|
|**RF-04.2**|ALTA|El sistema debe calcular el precio promedio de compra ponderado por volumen (VWAP) de BTC acumulado a lo largo del tiempo.|
|**RF-04.3**|ALTA|El sistema debe mostrar una curva histórica del precio promedio de compra vs precio de mercado de BTC para visualizar el efecto del DCA.|
|**RF-04.4**|ALTA|El sistema debe calcular cuántas sats (satoshis) totales se han acumulado y su equivalente en USD/EUR al precio actual.|
|**RF-04.5**|MEDIA|El sistema debe permitir al usuario definir un plan DCA futuro (importe periódico + frecuencia) y proyectar escenarios de precio para los próximos 12/24/36 meses.|
|**RF-04.6**|MEDIA|El sistema debe calcular el análisis DCA para cualquier activo del portafolio, no solo BTC.|
|**RF-04.7**|ALTA|El sistema debe mostrar un calendario de compras DCA con los importes y precios de cada evento histórico.|
|**RF-04.8**|MEDIA|El sistema debe calcular el porcentaje del tiempo que el precio actual está por encima/debajo del precio promedio de compra.|

## **2.5 Módulo de Dashboards y Visualizaciones**
### **RF-05 — Dashboards Interactivos**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RF-05.1**|ALTA|Dashboard Overview: resumen ejecutivo con valor total, P&L total, top gainers/losers del día, y gráfico de evolución de 30 días.|
|**RF-05.2**|ALTA|Dashboard Portfolio: distribución por activo (pie chart y tabla), con filtros por tipo de activo (spot, earn, locked staking).|
|**RF-05.3**|ALTA|Dashboard Performance: gráficos de rendimiento temporal con selector de rango (7d, 30d, 90d, 1y, todo), comparativa vs benchmarks.|
|**RF-05.4**|ALTA|Dashboard DCA Bitcoin: todas las métricas DCA de RF-04 en un dashboard dedicado con timeline de compras y curva de precio promedio.|
|**RF-05.5**|MEDIA|Dashboard Transacciones: historial completo de todas las operaciones con filtros por tipo, activo, rango de fechas y exportación a CSV.|
|**RF-05.6**|MEDIA|Dashboard Fiscalidad: agrupación de trades por año fiscal para facilitar el cálculo de ganancias/pérdidas a declarar (método FIFO por defecto, LIFO opcional).|
|**RF-05.7**|BAJA|Dashboard Heatmap: mapa de calor de rendimiento diario/mensual estilo GitHub contributions para visualizar días buenos vs malos.|
|**RF-05.8**|MEDIA|Todos los gráficos deben ser interactivos (zoom, hover para ver valores exactos, descarga como PNG/SVG).|
|**RF-05.9**|ALTA|El sistema debe soportar modo oscuro y claro.|
|**RF-05.10**|MEDIA|La UI debe ser responsive y usable en móvil.|


# **3. Requisitos No Funcionales**
## **3.1 Rendimiento**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RNF-01**|ALTA|El tiempo de carga de cualquier dashboard no debe superar 2 segundos en condiciones normales, ya que los datos están almacenados localmente en base de datos.|
|**RNF-02**|ALTA|Las consultas analíticas sobre datos históricos (hasta 5 años) deben completarse en menos de 3 segundos.|
|**RNF-03**|ALTA|La sincronización en background no debe degradar el rendimiento de la UI. Debe ejecutarse en un proceso/worker separado.|
|**RNF-04**|MEDIA|El sistema debe implementar paginación en el historial de transacciones para manejar conjuntos de datos de más de 10.000 registros.|

## **3.2 Seguridad**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RNF-05**|ALTA|Las API Keys de Binance deben almacenarse cifradas en la base de datos. Nunca deben exponerse en texto plano en logs ni en las respuestas de la API interna.|
|**RNF-06**|ALTA|La aplicación web debe requerir autenticación para acceder a cualquier endpoint. Las sesiones deben tener timeout configurable.|
|**RNF-07**|ALTA|Todas las comunicaciones deben realizarse mediante HTTPS (TLS). Si el despliegue es en local, debe usarse un certificado auto-firmado o proxy inverso con Caddy/Nginx.|
|**RNF-08**|ALTA|Las API Keys de Binance configuradas en el sistema deben tener permisos de solo lectura. El sistema debe verificarlo y avisar si detecta permisos de escritura.|
|**RNF-09**|MEDIA|El sistema debe implementar protección básica contra CSRF en todos los endpoints que modifiquen datos.|

## **3.3 Fiabilidad y Mantenibilidad**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RNF-10**|ALTA|El sistema debe manejar gracefully los errores de la API de Binance (rate limits, outages) sin perder datos ya sincronizados.|
|**RNF-11**|ALTA|Debe incluir sistema de logging estructurado (nivel, timestamp, mensaje, contexto) persistido en archivo y consultable desde la UI de administración.|
|**RNF-12**|MEDIA|La base de datos debe contar con mecanismo de backup automático (al menos diario) hacia un directorio configurable.|
|**RNF-13**|MEDIA|El código debe seguir estructura modular con separación clara de capas (API layer, service layer, data layer) para facilitar el mantenimiento.|
|**RNF-14**|BAJA|El sistema debe incluir tests unitarios para los cálculos financieros críticos (P&L, VWAP, IRR) con cobertura mínima del 80%.|

## **3.4 Portabilidad y Despliegue**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**RNF-15**|ALTA|El sistema debe poder desplegarse mediante Docker Compose en cualquier máquina Linux, Mac o Windows con Docker instalado, con un solo comando.|
|**RNF-16**|ALTA|Toda la configuración sensible (API keys de la app, puerto, etc.) debe gestionarse mediante variables de entorno en un archivo .env, nunca hardcodeada.|
|**RNF-17**|MEDIA|El sistema debe incluir documentación de despliegue (README) que permita ponerlo en marcha en menos de 15 minutos.|


# **4. Casos de Uso**
## **4.1 Actores del Sistema**
- Usuario: propietario de la cuenta de Binance que accede a la aplicación web.
- Sistema de Sincronización: proceso background (scheduler) que ejecuta sincronizaciones periódicas.
- API Binance: servicio externo de datos.

## **4.2 Tabla de Casos de Uso**

|**ID**|**Nombre**|**Actor**|**Descripción**|
| :- | :- | :- | :- |
|**CU-01**|Configurar API Key de Binance|Usuario|El usuario accede a ajustes, introduce su API Key y Secret, el sistema los valida y guarda cifrados.|
|**CU-02**|Forzar sincronización manual|Usuario|El usuario pulsa 'Sincronizar ahora', el sistema descarga datos nuevos desde la API y actualiza la BD.|
|**CU-03**|Ver Overview del portafolio|Usuario|El usuario accede al dashboard principal y ve valor total, P&L, distribución y gráfico de 30 días.|
|**CU-04**|Analizar rendimiento temporal|Usuario|El usuario selecciona un rango de fechas y visualiza la curva de valor del portafolio con comparativa vs BTC.|
|**CU-05**|Ver análisis DCA de Bitcoin|Usuario|El usuario accede al dashboard DCA y ve precio promedio, sats acumuladas, calendario de compras y curva VWAP.|
|**CU-06**|Proyectar DCA futuro|Usuario|El usuario configura un plan DCA (cantidad + frecuencia) y el sistema simula el resultado bajo distintos escenarios de precio.|
|**CU-07**|Explorar historial de transacciones|Usuario|El usuario filtra transacciones por activo, tipo y fecha, y exporta el resultado a CSV.|
|**CU-08**|Ver métricas fiscales por año|Usuario|El usuario selecciona un año fiscal y el sistema le muestra ganancias/pérdidas realizadas para declaración.|
|**CU-09**|Configurar sincronización automática|Usuario|El usuario define el intervalo de auto-sync y el sistema programa las ejecuciones periódicas.|
|**CU-10**|Sincronización automática periódica|Sistema de Sync|El scheduler ejecuta la sincronización, descarga datos incrementales, los guarda en BD y actualiza métricas precalculadas.|
|**CU-11**|Ver estado del sistema|Usuario|El usuario accede a la sección de administración y ve logs de sync, estado de conexión a Binance y métricas de la BD.|
|**CU-12**|Cambiar divisa de referencia|Usuario|El usuario selecciona USD, EUR o BTC como divisa principal y todos los valores del dashboard se recalculan.|

## **4.3 Flujo Detallado: CU-10 Sincronización Automática**
### **Precondiciones**
- Las API Keys están configuradas y validadas en el sistema.
- La base de datos está operativa.
### **Flujo Principal**
1. El scheduler dispara el job de sincronización según el intervalo configurado.
1. El sistema consulta en la BD el último timestamp registrado para cada tipo de datos (trades, depósitos, retiros, balances).
1. El sistema llama a la API de Binance pidiendo solo los datos posteriores al último timestamp (sincronización incremental).
1. El sistema gestiona la paginación de la API de Binance hasta obtener todos los registros nuevos.
1. Los datos recibidos se normalizan, se enriquecen con precios históricos si aplica, y se persisten en las tablas correspondientes de la BD.
1. El sistema recalcula y cachea las métricas agregadas (valor total, P&L, VWAP DCA, etc.) en tablas de resumen.
1. Se registra en el log el resultado de la sincronización: timestamp, registros importados, duración y errores si los hubo.
1. El dashboard se refresca automáticamente si el usuario tiene la aplicación abierta (via WebSocket o polling).
### **Flujos Alternativos**
- 4a. Rate limit excedido: el sistema pausa, espera el tiempo indicado por Binance en el header Retry-After, y reintenta.
- 4b. Error de red: el sistema reintenta hasta 3 veces con backoff exponencial. Si falla, registra el error y planifica el siguiente intento normal.
- 4c. API Key inválida: el sistema marca la conexión como 'error de autenticación' y notifica al usuario en la UI.


# **5. Modelo de Datos**
## **5.1 Entidades Principales**
A continuación se describen las tablas principales de la base de datos. Se usará PostgreSQL como motor principal por su soporte de tipos de datos numéricos de alta precisión (NUMERIC/DECIMAL), funciones de ventana para análisis temporal, y extensión TimescaleDB opcional para series temporales.

### **Tabla: accounts**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**id**|—|UUID, PRIMARY KEY — identificador único de la cuenta.|
|**name**|—|VARCHAR(100) — nombre descriptivo de la cuenta (e.g. 'Cuenta Principal').|
|**api\_key\_encrypted**|—|TEXT — API Key de Binance cifrada con AES-256-GCM.|
|**api\_secret\_encrypted**|—|TEXT — API Secret de Binance cifrado.|
|**last\_sync\_at**|—|TIMESTAMPTZ — timestamp de la última sincronización exitosa.|
|**sync\_status**|—|ENUM('idle','syncing','error') — estado actual de la sincronización.|
|**created\_at**|—|TIMESTAMPTZ — fecha de creación del registro.|

### **Tabla: transactions**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**id**|—|UUID, PRIMARY KEY.|
|**account\_id**|—|UUID, FK → accounts.id.|
|**binance\_id**|—|VARCHAR(100) UNIQUE — ID original de Binance para evitar duplicados en re-sync.|
|**type**|—|ENUM('buy','sell','deposit','withdrawal','convert','earn\_interest','staking\_reward') — tipo de transacción.|
|**base\_asset**|—|VARCHAR(20) — activo base (e.g. 'BTC').|
|**quote\_asset**|—|VARCHAR(20) — activo cotizado (e.g. 'USDT').|
|**quantity**|—|NUMERIC(36,18) — cantidad del activo base.|
|**price**|—|NUMERIC(36,18) — precio por unidad en quote\_asset.|
|**total\_value\_usd**|—|NUMERIC(20,8) — valor total en USD al momento de la transacción (se almacena para análisis histórico).|
|**fee\_asset**|—|VARCHAR(20) — activo en el que se pagó la comisión.|
|**fee\_amount**|—|NUMERIC(36,18) — cantidad de comisión pagada.|
|**executed\_at**|—|TIMESTAMPTZ — timestamp de ejecución. Indexado.|
|**raw\_data**|—|JSONB — payload raw de la API de Binance para trazabilidad.|

### **Tabla: balances\_snapshot**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**id**|—|UUID, PRIMARY KEY.|
|**account\_id**|—|UUID, FK → accounts.id.|
|**asset**|—|VARCHAR(20) — símbolo del activo.|
|**free**|—|NUMERIC(36,18) — balance disponible.|
|**locked**|—|NUMERIC(36,18) — balance bloqueado (orders abiertas, staking).|
|**snapshot\_at**|—|TIMESTAMPTZ — timestamp del snapshot. Indexado.|
|**value\_usd**|—|NUMERIC(20,8) — valoración en USD en el momento del snapshot.|

### **Tabla: price\_history (OHLCV)**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**id**|—|UUID, PRIMARY KEY.|
|**symbol**|—|VARCHAR(20) — par de trading (e.g. 'BTCUSDT').|
|**interval**|—|ENUM('1d','1w','1M') — granularidad del dato.|
|**open\_at**|—|TIMESTAMPTZ — inicio del período. Índice compuesto (symbol, interval, open\_at).|
|**open**|—|NUMERIC(20,8) — precio de apertura.|
|**high**|—|NUMERIC(20,8) — precio máximo.|
|**low**|—|NUMERIC(20,8) — precio mínimo.|
|**close**|—|NUMERIC(20,8) — precio de cierre.|
|**volume**|—|NUMERIC(30,8) — volumen.|

### **Tabla: portfolio\_snapshots (caché calculado)**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**id**|—|UUID, PRIMARY KEY.|
|**account\_id**|—|UUID, FK → accounts.id.|
|**snapshot\_date**|—|DATE — fecha del snapshot diario. Índice único (account\_id, snapshot\_date).|
|**total\_value\_usd**|—|NUMERIC(20,8) — valor total del portafolio en USD.|
|**invested\_usd**|—|NUMERIC(20,8) — capital invertido acumulado hasta esa fecha.|
|**pnl\_unrealized\_usd**|—|NUMERIC(20,8) — P&L no realizado.|
|**pnl\_realized\_usd**|—|NUMERIC(20,8) — P&L realizado acumulado.|
|**btc\_amount**|—|NUMERIC(36,18) — cantidad total de BTC en portafolio esa fecha.|
|**btc\_avg\_buy\_price**|—|NUMERIC(20,8) — precio promedio de compra de BTC (VWAP) hasta esa fecha.|
|**composition\_json**|—|JSONB — composición detallada por activo en esa fecha.|


# **6. Arquitectura Técnica**
## **6.1 Stack Tecnológico Propuesto**

|**Capa**|**Tecnología**|**Justificación**|
| :- | :- | :- |
|**Frontend**|Next.js 14 (App Router) + TypeScript|SSR/SSG para carga rápida, ecosistema React maduro, TypeScript para tipo-seguridad.|
|**Gráficos**|Recharts + TradingView Lightweight Charts|Recharts para métricas generales, TradingView para gráficos de precio tipo candlestick.|
|**Estilos**|Tailwind CSS + shadcn/ui|Desarrollo rápido de UI consistente con componentes accesibles.|
|**Backend API**|FastAPI (Python) o Next.js API Routes|FastAPI si se prefiere Python para lógica financiera; API Routes si se quiere mono-repo JS.|
|**Sincronización**|APScheduler (Python) o node-cron|Scheduler en proceso independiente para no bloquear el servidor web.|
|**Base de Datos**|PostgreSQL 15+|Soporte NUMERIC de alta precisión, funciones de ventana, JSONB para datos raw.|
|**ORM / Query Builder**|SQLAlchemy (Python) o Drizzle ORM (TS)|Migrations versionadas, type-safety en queries.|
|**Caché en memoria**|Redis (opcional)|Caché de precios actuales y métricas calculadas frecuentemente para respuesta sub-100ms.|
|**Despliegue**|Docker Compose|Un solo docker-compose.yml levanta BD + backend + frontend + scheduler + Redis.|
|**Seguridad de secrets**|python-cryptography / Node crypto (AES-256-GCM)|Cifrado de API Keys en reposo.|

## **6.2 Diagrama de Arquitectura (descripción textual)**
El sistema sigue una arquitectura de tres capas desacopladas:

CAPA DE PRESENTACIÓN — Next.js frontend que consume la API interna mediante REST JSON. Se comunica con el backend exclusivamente a través del API Gateway interno. No tiene acceso directo a la base de datos.

CAPA DE NEGOCIO — Backend API (FastAPI o Next.js API Routes) que expone endpoints RESTful para: obtener dashboards (/api/v1/dashboard/\*), transacciones (/api/v1/transactions), configuración (/api/v1/settings), y forzar sync (/api/v1/sync). Contiene la lógica de cálculo financiero (P&L, VWAP, IRR, drawdown). El Scheduler Service corre en paralelo y ejecuta los jobs de sincronización periódicos.

CAPA DE DATOS — PostgreSQL como almacén principal. Redis como caché de métricas calculadas y precios en tiempo real. El Scheduler es el único componente que escribe datos provenientes de Binance; el backend API solo lee de la BD local (a excepción del endpoint de force-sync que delega al Scheduler).

## **6.3 Endpoints API Interna (referencia)**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**GET /api/v1/dashboard/overview**|—|Retorna métricas resumen: valor total, P&L, distribución top-10 activos, evolución 30d.|
|**GET /api/v1/dashboard/performance**|—|Query params: from, to, interval. Retorna serie temporal de valor del portafolio y benchmarks.|
|**GET /api/v1/dashboard/dca/:asset**|—|Retorna análisis DCA completo para el activo indicado (BTC por defecto).|
|**GET /api/v1/transactions**|—|Query params: page, limit, type, asset, from, to. Retorna historial paginado.|
|**GET /api/v1/transactions/export**|—|Query params iguales. Retorna CSV del historial filtrado.|
|**GET /api/v1/portfolio/assets**|—|Retorna lista de activos con balance, valor USD y métricas por activo.|
|**GET /api/v1/portfolio/history**|—|Retorna portfolio\_snapshots diarios en el rango indicado.|
|**GET /api/v1/settings**|—|Retorna configuración de la aplicación (excepto secrets).|
|**POST /api/v1/settings**|—|Guarda configuración (API Keys, intervalo de sync, divisa preferida).|
|**POST /api/v1/sync/trigger**|—|Fuerza una sincronización inmediata. Retorna job\_id para polling.|
|**GET /api/v1/sync/status**|—|Retorna estado del último sync: estado, registros importados, errores, timestamp.|
|**GET /api/v1/fiscal/:year**|—|Retorna ganancias/pérdidas realizadas agrupadas por año fiscal (método FIFO por defecto).|


# **7. Plan de Implementación por Fases**
## **Fase 1 — Fundación (MVP Core)**
Objetivo: sistema funcional con sincronización de datos y dashboard básico.

- Scaffolding del proyecto con Docker Compose (PostgreSQL + backend + frontend).
- Modelo de datos: migraciones para accounts, transactions, balances\_snapshot, price\_history, portfolio\_snapshots.
- Integración API Binance: módulo de cliente con gestión de rate limit y retry.
- Sincronización inicial completa: importar todo el historial de trades, depósitos y retiros.
- Sincronización incremental: job periódico que solo descarga datos nuevos.
- Autenticación de la app web (login básico con contraseña).
- Dashboard Overview: valor total, P&L básico, lista de activos.

## **Fase 2 — Analítica Avanzada**
Objetivo: métricas financieras completas y dashboard de performance.

- Cálculo de P&L realizado histórico (método FIFO).
- Cálculo de IRR y drawdown máximo.
- Generación de portfolio\_snapshots históricos diarios (backfill desde el inicio).
- Dashboard Performance con selector de rango temporal y comparativa vs BTC.
- Dashboard DCA Bitcoin: VWAP, calendario de compras, curva precio promedio vs mercado.
- Exportación CSV del historial de transacciones.

## **Fase 3 — Features Avanzados y Pulido**
Objetivo: dashboards especializados y mejoras de UX.

- Dashboard fiscal por año con método FIFO/LIFO configurable.
- Proyección de DCA futuro con simulación de escenarios.
- Heatmap de rendimiento diario.
- Modo oscuro, diseño responsive para móvil.
- Redis para caché de métricas calculadas.
- Tests unitarios de cálculos financieros críticos.
- Documentación de despliegue completa (README).


# **8. Restricciones y Consideraciones**
## **8.1 Restricciones de la API de Binance**
- La API de Binance tiene límites de rate que varían por endpoint (peso de petición). El módulo cliente debe respetar el header X-MBX-USED-WEIGHT y pausar si se acerca al límite.
- El historial de trades está limitado a 500 registros por petición y requiere iterar en ventanas temporales de máximo 24h en algunos endpoints. El sistema debe manejar esta paginación transparentemente.
- Los depósitos y retiros de cripto tienen endpoints separados a los depósitos/retiros de fiat. Se deben consultar por separado.
- Para acceder al historial de P2P y Binance Convert se requieren endpoints específicos con sus propias limitaciones de paginación.

## **8.2 Precisión Numérica**
- Todos los cálculos financieros deben realizarse con tipos de datos de alta precisión (DECIMAL/NUMERIC en BD, Decimal en Python o BigDecimal en JS). Nunca usar float nativo de JavaScript para cálculos monetarios.
- El almacenamiento de cantidades de criptomonedas requiere hasta 18 decimales de precisión (estándar ERC-20 / Satoshi).

## **8.3 Consideraciones de Privacidad**
- Este sistema es de uso personal y no está diseñado para múltiples usuarios públicos. No implementar registro de nuevos usuarios; solo configurar credenciales del propietario.
- No enviar ningún dato del portafolio a servicios externos no confiables. Los precios históricos sí pueden consultarse a APIs públicas (Binance público, CoinGecko) pero sin enviar identificadores de cuenta.

## **8.4 Limitaciones Conocidas**
- El historial de Binance disponible vía API puede estar limitado a los últimos 6-12 meses en algunos endpoints (e.g. historial de orders). Para datos más antiguos se puede necesitar exportar desde la web de Binance manualmente e importarlos como CSV.
- El sistema no soporta otros exchanges en Fase 1-2. La arquitectura debe diseñarse para permitir la adición futura de otros exchanges (abstracción de la capa de datos de exchange).

# **9. Criterios de Aceptación del MVP**

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**CA-01**|ALTA|El usuario puede introducir sus API Keys, el sistema las valida contra Binance y confirma que son de solo lectura.|
|**CA-02**|ALTA|Tras la primera sincronización, todos los trades históricos y depósitos aparecen en el historial de transacciones con los datos correctos (activo, cantidad, precio, fecha).|
|**CA-03**|ALTA|El valor total del portafolio en el dashboard coincide (±1%) con el valor mostrado en la aplicación oficial de Binance.|
|**CA-04**|ALTA|El precio promedio de compra de BTC calculado por el sistema coincide con el calculado manualmente a partir de las mismas transacciones.|
|**CA-05**|ALTA|La sincronización automática se ejecuta sin intervención del usuario y los nuevos datos aparecen en el dashboard sin necesidad de recargar manualmente.|
|**CA-06**|ALTA|Un error transitorio de la API de Binance (timeout, rate limit) no provoca pérdida de datos ya sincronizados ni corrompe el estado de la base de datos.|
|**CA-07**|ALTA|Las API Keys no son visibles en texto plano en ningún log, respuesta de API ni en la interfaz de usuario.|
|**CA-08**|ALTA|El sistema se puede levantar desde cero con docker compose up en menos de 5 minutos siguiendo el README.|


# **Apéndice A — Endpoints de Binance API Relevantes**
Lista de referencia de los endpoints de la API REST de Binance que el sistema debe integrar (API v3 en api.binance.com):

|**ID**|**Prioridad**|**Descripción**|
| :- | :- | :- |
|**GET /api/v3/account**|—|Balances actuales de todos los activos. Requiere autenticación HMAC.|
|**GET /api/v3/myTrades**|—|Historial de trades. Parámetros: symbol, startTime, endTime, limit (max 1000).|
|**GET /sapi/v1/capital/deposit/hisrec**|—|Historial de depósitos de cripto.|
|**GET /sapi/v1/capital/withdraw/history**|—|Historial de retiros de cripto.|
|**GET /sapi/v1/fiat/orders**|—|Historial de depósitos y retiros de fiat (transactionType: 0=depósito, 1=retiro).|
|**GET /sapi/v1/convert/tradeFlow**|—|Historial de conversiones Binance Convert.|
|**GET /sapi/v1/c2c/orderMatch/listUserOrderHistory**|—|Historial de operaciones P2P.|
|**GET /api/v3/klines**|—|Datos OHLCV históricos. Parámetros: symbol, interval, startTime, endTime, limit.|
|**GET /sapi/v1/asset/assetDividend**|—|Historial de distribuciones de earn (intereses de Flexible, rewards de staking).|
|**GET /api/v3/ticker/price**|—|Precio actual de un par. Uso para valoración en tiempo real.|
|**GET /api/v3/exchangeInfo**|—|Información de todos los pares disponibles. Útil para mapear activos a pares USD/USDT.|

# **Apéndice B — Fórmulas Financieras Clave**
### **Precio Promedio de Compra (VWAP DCA)**
Se calcula como la suma de (precio\_i × cantidad\_i) para todas las compras, dividida entre la cantidad total acumulada. Solo se incluyen transacciones de tipo 'buy' y 'deposit' de cripto. Las ventas parciales reducen la cantidad total pero no el coste medio (método FIFO ajusta el coste base de las unidades restantes).

### **P&L No Realizado**
P&L\_unrealized = (precio\_actual × cantidad\_actual) − coste\_base\_total. El coste\_base\_total es la suma del capital desembolsado para las unidades actualmente en posesión (calculado por FIFO si hubo ventas parciales).

### **ROI**
ROI = (valor\_actual − capital\_invertido\_total) / capital\_invertido\_total × 100. El capital\_invertido\_total es la suma de todos los depósitos de fiat netos de retiros de fiat, más el valor USD de los activos cripto depositados directamente.

### **Drawdown Máximo**
Se calcula sobre la serie temporal diaria del valor del portafolio: para cada día se computa el máximo valor histórico hasta ese día, luego la caída porcentual desde ese máximo. El drawdown máximo es la mayor caída porcentual registrada en toda la serie.

*— Fin del Documento —*

Binance Portfolio Dashboard SRS v1.0 · Febrero 2026
