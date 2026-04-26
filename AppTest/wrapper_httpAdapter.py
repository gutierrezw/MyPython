import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIClient:
    def __init__(self, base_url=None, retries=3, backoff_factor=0.5, status_forcelist=None):
        """
        Inicializa el cliente API con una sesión configurada para reintentos.

        :param base_url: (Opcional) URL base para las solicitudes.
        :param retries: Número total de reintentos.
        :param backoff_factor: Factor de tiempo de espera entre reintentos.
        :param status_forcelist: Lista de códigos HTTP que deben provocar reintentos.
        """
        self.base_url = base_url or ""
        self.session = requests.Session()
        # Si no se especifica, usamos algunos códigos de error comunes para reintentos.
        status_forcelist = status_forcelist or [502, 503, 504]
        retry_strategy = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=["GET", "POST", "PUT", "DELETE"]  # Para versiones antiguas, usa method_whitelist
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get(self, url, **kwargs):
        """Realiza una solicitud GET controlada por reintentos."""
        full_url = self._build_url(url)
        response = self.session.get(full_url, **kwargs)
        response.raise_for_status()
        return response

    def post(self, url, data=None, json=None, **kwargs):
        """Realiza una solicitud POST controlada por reintentos."""
        full_url = self._build_url(url)
        response = self.session.post(full_url, data=data, json=json, **kwargs)
        response.raise_for_status()
        return response

    def _build_url(self, url):
        """Construye la URL completa si se ha definido una URL base."""
        if self.base_url:
            return self.base_url.rstrip("/") + "/" + url.lstrip("/")
        return url


# Ejemplo de uso:
if __name__ == "__main__":
    # Creamos un cliente API con reintentos configurados
    client = APIClient(retries=5, backoff_factor=1)
    try:
        response = client.get(
            "https://api.binance.com/api/v3/openOrders?timestamp=1740241030019&signature=TU_SIGNATURE_AQUI", timeout=10)
        data = response.json()
        print("Datos obtenidos:", data)
    except Exception as e:
        print("Error en la solicitud:", e)
