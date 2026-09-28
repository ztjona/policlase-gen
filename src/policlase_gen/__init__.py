"""Cadena de herramientas de autoría de preguntas de policlase.

Paquete autónomo: sin autenticación, sin base de datos, sin servidor. La plataforma lo
importa como dependencia para que servidor y CLI no puedan discrepar sobre qué es un ítem
válido, ni sobre cómo se califica una respuesta.

Ver `docs/schema.md` para la referencia normativa del formato.
"""

from .errors import Diagnostic, Report, Severity
from .validate import SCHEMA_VERSIONS, validate_document, validate_file

__version__ = "0.1.0"

__all__ = [
    "Diagnostic", "Report", "Severity",
    "SCHEMA_VERSIONS", "validate_file", "validate_document",
    "__version__",
]
