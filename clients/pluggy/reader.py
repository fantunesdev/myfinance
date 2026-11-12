"""Read-only Pluggy transport shared by the probe and Django integration."""
import time
from collections import Counter
from uuid import UUID

import requests


class ProbeError(Exception):
    """A diagnostic safe to print without response bodies or credentials."""


class PluggyReader:
    BASE = "https://api.pluggy.ai"

    def __init__(self, client_id, client_secret, session=None, sleep=time.sleep):
        self.session = session or requests.Session()
        self.credentials = {"clientId": client_id, "clientSecret": client_secret}
        self.api_key = None
        self.sleep = sleep
        self.pages = Counter()

    def request(self, path, params=None):
        # Fixed host and allowlist: auth is the only POST; no financial writes.
        investment_history = path.startswith("/investments/") and path.endswith("/transactions") and self._is_uuid(path[len("/investments/"):-len("/transactions")])
        if not investment_history and path not in ("/auth", "/accounts", "/bills", "/v2/transactions", "/investments") and not (
            path.startswith("/items/") and self._is_uuid(path.removeprefix("/items/"))
        ):
            raise ProbeError("Endpoint fora do escopo de leitura.")
        auth = path == "/auth"
        for attempt in range(3):
            try:
                response = self.session.request(
                    "POST" if auth else "GET",
                    self.BASE + path,
                    params=params,
                    json=self.credentials if auth else None,
                    headers={} if auth else {"X-API-KEY": self.api_key},
                    timeout=(10, 45),
                    allow_redirects=False,
                )
            except requests.RequestException:
                if attempt < 2:
                    self.sleep(2**attempt)
                    continue
                raise ProbeError("Falha de rede/timeout; nenhuma exportação foi concluída.") from None
            if response.status_code == 401 and not auth:
                if attempt == 0:
                    self.authenticate()
                    continue
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt < 2:
                    try:
                        delay = min(30, max(1, int(response.headers.get("Retry-After", 2**attempt))))
                    except ValueError:
                        delay = 2**attempt
                    self.sleep(delay)
                    continue
            if response.status_code != 200:
                hints = {
                    401: "Credenciais inválidas ou autorização expirada.",
                    403: "Acesso não permitido para esta aplicação/conexão.",
                    429: "Limite de consultas atingido; aguarde antes de repetir.",
                }
                raise ProbeError(
                    f'HTTP {response.status_code} em {path.split("?")[0]}. '
                    + hints.get(response.status_code, "Consulta não concluída.")
                )
            try:
                data = response.json()
            except ValueError:
                raise ProbeError("A API retornou conteúdo que não é JSON.") from None
            if not isinstance(data, dict):
                raise ProbeError("Formato de resposta inesperado.")
            return data
        raise ProbeError("Consulta não concluída após tentativas limitadas.")

    @staticmethod
    def _is_uuid(value):
        try:
            UUID(value)
            return True
        except (ValueError, TypeError):
            return False

    def authenticate(self):
        self.api_key = self.request("/auth").get("apiKey")
        if not isinstance(self.api_key, str) or not self.api_key:
            raise ProbeError("Autenticação sem chave de API válida.")

    @staticmethod
    def append_rows(data, rows, seen):
        batch = data.get("results")
        if not isinstance(batch, list):
            raise ProbeError("Página sem lista results; exportação interrompida.")
        for row in batch:
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
                raise ProbeError("Registro sem identificador válido.")
            if row["id"] in seen:
                raise ProbeError("ID repetido entre páginas; repita a consulta após a sincronização.")
            seen.add(row["id"])
            rows.append(row)

    def numbered(self, path, params):
        rows, seen, expected = [], set(), None
        for page in range(1, 10001):
            data = self.request(path, {**params, "page": page})
            self.pages[path] += 1
            total, total_pages = data.get("total"), data.get("totalPages")
            if (
                type(total) is not int
                or total < 0
                or type(total_pages) is not int
                or total_pages < 0
                or data.get("page") != page
            ):
                raise ProbeError("Metadados de paginação inválidos.")
            if expected is None:
                expected = (total, total_pages)
            if expected != (total, total_pages):
                raise ProbeError("Paginação mudou durante a consulta; tente novamente depois.")
            self.append_rows(data, rows, seen)
            if page >= total_pages:
                if len(rows) != total:
                    raise ProbeError("Total recebido difere da paginação; exportação incompleta.")
                return rows
            if not data["results"]:
                raise ProbeError("Página vazia antes do fim da consulta.")
        raise ProbeError("Limite de páginas excedido.")

    def transactions(self, account_id):
        rows, seen, cursors = [], set(), set()
        params = {"accountId": account_id}
        for _ in range(10000):
            data = self.request("/v2/transactions", params)
            self.pages["/v2/transactions"] += 1
            self.append_rows(data, rows, seen)
            if any(row.get("accountId") != account_id for row in data["results"]):
                raise ProbeError("Transação retornada pertence a outra conta.")
            if "next" not in data:
                raise ProbeError("Resposta sem término explícito de paginação.")
            cursor = data["next"]
            if cursor is None:
                return rows
            if not isinstance(cursor, str) or not cursor.startswith("?") or cursor in cursors:
                raise ProbeError("Cursor inválido ou repetido; exportação interrompida.")
            cursors.add(cursor)
            # requests accepts a ready query string, preserving the provider cursor.
            params = cursor[1:]
        raise ProbeError("Limite de páginas excedido.")
