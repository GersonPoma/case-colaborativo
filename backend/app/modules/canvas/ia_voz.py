from groq import Groq
from groq import APIConnectionError, APIStatusError

from app.config.settings import settings
from app.core.exceptions import AppException


def transcribir_audio(contenido: bytes, nombre_archivo: str) -> str:
    if not settings.GROQ_API_KEY_VOZ:
        raise AppException("No hay una API key de Groq configurada en el servidor.")

    cliente = Groq(api_key=settings.GROQ_API_KEY_VOZ)
    try:
        respuesta = cliente.audio.transcriptions.create(
            file=(nombre_archivo, contenido),
            model=settings.GROQ_MODEL_VOZ,
            language="es",
        )
    except APIStatusError as exc:
        if exc.status_code >= 500 or exc.status_code == 429:
            raise AppException(
                "El servicio de transcripción está saturado en este momento. Probá de nuevo en unos minutos."
            ) from exc
        raise AppException(f"No se pudo transcribir el audio: {exc.message}") from exc
    except APIConnectionError as exc:
        raise AppException("No se pudo conectar con el servicio de transcripción.") from exc

    texto = respuesta.text.strip()
    if not texto:
        raise AppException("No se pudo reconocer ningún texto en el audio.")
    return texto
