"""Límites compartidos de paginación — Fase 2/M3 (docs/22-planificacion-fase2.md).

Un solo lugar para el tamaño de página por defecto y el máximo permitido,
en vez de repetir los mismos números en cada router que pagina (Auditoría,
Usuarios — Equipos ya paginaba desde antes de esta fase con los mismos
valores, mantenido tal cual, sin tocar su router en este cambio)."""

TAMANO_PAGINA_POR_DEFECTO = 20
# Evita que un cliente pida una página de miles de filas de un tirón — el
# mismo valor que ya usaba el módulo Equipos antes de esta fase.
TAMANO_PAGINA_MAXIMO = 100
