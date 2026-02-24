"""
Proceso independiente del scheduler APScheduler.
Ejecuta jobs de sincronización periódica con Binance.
El scheduler es el ÚNICO proceso que escribe datos de Binance en la BD.
TODO: Implementar en Fase 1c.

Arrancar con: python -m sync.scheduler
"""

import logging

from core.config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info(
        "Scheduler starting — interval=%d min, env=%s",
        settings.SYNC_INTERVAL_MINUTES,
        settings.APP_ENV,
    )
    # TODO: configurar APScheduler con BlockingScheduler
    # TODO: añadir job sync_all_accounts() cada SYNC_INTERVAL_MINUTES
    logger.warning("Scheduler not yet implemented. Exiting.")


if __name__ == "__main__":
    main()
