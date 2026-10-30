import logging
import os
from pathlib import Path
import grpc
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from .api.client import Certs, Client

logger = logging.getLogger(__name__)
ICONS = ["?", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]


def roll(address):
    certs = Certs.load(Path(os.environ.get("CERTS_DIR", str(settings.BASE_DIR / "certs"))))
    return Client(address, certs).roll_die()


def index(request):
    values = [0, 0]
    error = ""
    if request.method == "POST":
        try:
            values = [roll("127.0.0.1:8443"), roll("127.0.0.1:9448")]
        except (grpc.RpcError, OSError, ValueError):
            logger.exception("Dice service request failed")
            error = "Сервис временно недоступен. Проверьте сервер, nginx и сертификаты."
    sign = "=" if values[0] == values[1] else "<" if values[0] < values[1] else ">"
    return render(request, "index.html", {"icon_a": ICONS[values[0]], "icon_b": ICONS[values[1]], "value_a": values[0], "value_b": values[1], "sign": sign, "error": error})


def rpc_response(address, label):
    try:
        value = roll(address)
        return HttpResponse(f"{label} | Value: {value} {ICONS[value]}\n", content_type="text/plain; charset=utf-8")
    except (grpc.RpcError, OSError, ValueError):
        logger.exception("Dice service request failed")
        return HttpResponse("Dice service unavailable\n", status=503, content_type="text/plain")


def direct(request):
    return rpc_response("127.0.0.1:8443", "Direct gRPC + mTLS")


def proxied(request):
    return rpc_response("127.0.0.1:9448", "nginx + mTLS -> gRPC h2c")
