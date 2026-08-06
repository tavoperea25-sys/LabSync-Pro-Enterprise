#!/bin/sh
set -e

echo "Aplicando migraciones..."
alembic upgrade head

echo "Sembrando roles y permisos de sistema..."
python -m app.seeds.seed_roles_permisos

if [ "$ENTORNO" != "produccion" ]; then
  echo "Sembrando laboratorio de desarrollo..."
  python -m app.seeds.seed_dev_tenant || true
fi

if [ "$ENTORNO" = "produccion" ]; then
  # Fase 2/M7 (docs/22-planificacion-fase2.md). `--reload` reinicia todo el
  # proceso ante cualquier cambio de archivo (útil en desarrollo, con el
  # código montado como volumen) y solo soporta 1 worker — en producción no
  # hay archivos cambiando en caliente y sí interesa aprovechar varios
  # núcleos, así que se usa `--workers` en su lugar. Parametrizable (no un
  # valor fijo) porque el número correcto depende de los núcleos de la
  # máquina real, que este repo no conoce de antemano — WORKERS_UVICORN
  # queda como variable de entorno para que quien despliegue lo fije según
  # el hardware. El default (4) es un punto de partida conservador, no una
  # medición: ajustar cuando exista un entorno de producción real desplegado
  # (ver docs/13-arquitectura.md sección 11, "Arquitectura futura" — el
  # `docker-compose.prod.yml` que usaría esta rama todavía no existe).
  echo "Iniciando API (producción, ${WORKERS_UVICORN:-4} workers, sin --reload)..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WORKERS_UVICORN:-4}"
else
  echo "Iniciando API (desarrollo, --reload activo)..."
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
