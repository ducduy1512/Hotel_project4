
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


API_BASE_URL = "http://127.0.0.1:8000"


class APIError(Exception):
    """Lỗi phát sinh khi giao tiếp với FastAPI."""
    pass


class APIClient:
    def __init__(self, base_url=API_BASE_URL, timeout=15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method, endpoint, data=None, params=None):
        url = self.base_url + "/" + endpoint.lstrip("/")

        if params:
            query_string = urlencode({
                key: value
                for key, value in params.items()
                if value is not None
            })

            if query_string:
                url += "?" + query_string

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        body = None

        if data is not None:
            body = json.dumps(
                data,
                ensure_ascii=False
            ).encode("utf-8")

        req = Request(
            url=url,
            data=body,
            headers=headers,
            method=method.upper()
        )

        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")

                if not raw:
                    return {}

                return json.loads(raw)

        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")

            try:
                result = json.loads(raw)
                detail = result.get("detail", raw)
            except (json.JSONDecodeError, AttributeError):
                detail = raw

            raise APIError(
                f"API trả về lỗi HTTP {error.code}: {detail}"
            ) from error

        except URLError as error:
            raise APIError(
                "Không thể kết nối FastAPI tại "
                f"{self.base_url}.\n"
                "Hãy khởi động API trước khi sử dụng giao diện.\n"
                f"Chi tiết: {error.reason}"
            ) from error

        except json.JSONDecodeError as error:
            raise APIError(
                "FastAPI trả về dữ liệu JSON không hợp lệ."
            ) from error

        except TimeoutError as error:
            raise APIError(
                "Kết nối FastAPI quá thời gian chờ."
            ) from error

    def get(self, endpoint, params=None):
        return self.request(
            "GET",
            endpoint,
            params=params
        )

    def post(self, endpoint, data):
        return self.request(
            "POST",
            endpoint,
            data=data
        )

    def put(self, endpoint, data):
        return self.request(
            "PUT",
            endpoint,
            data=data
        )

    def delete(self, endpoint):
        return self.request(
            "DELETE",
            endpoint
        )


# Sử dụng chung trong toàn bộ giao diện Tkinter
api_client = APIClient()
