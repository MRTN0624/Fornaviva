"""Límite de cuerpo antes de decodificar JSON, incluso sin Content-Length."""
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 128 * 1024


class RequestSizeLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        buffer = bytearray()
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            size += len(body)
            if size > MAX_BODY_BYTES:
                response = JSONResponse({"detail": "El cuerpo supera 128 KiB."}, status_code=413)
                return await response(scope, receive, send)
            buffer.extend(body)
            if not message.get("more_body", False):
                break
        delivered = False

        async def limited_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(buffer), "more_body": False}
            return await receive()

        await self.app(scope, limited_receive, send)
