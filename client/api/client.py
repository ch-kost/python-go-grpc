from dataclasses import dataclass
from pathlib import Path
import grpc
from . import api_pb2, api_pb2_grpc


@dataclass(frozen=True)
class Certs:
    root: bytes
    cert: bytes
    key: bytes

    @classmethod
    def load(cls, directory: Path):
        return cls((directory / "ca.pem").read_bytes(), (directory / "client.pem").read_bytes(), (directory / "client-key.pem").read_bytes())


class Client:
    def __init__(self, address: str, certs: Certs):
        self.address = address
        self.credentials = grpc.ssl_channel_credentials(certs.root, certs.key, certs.cert)

    def roll_die(self) -> int:
        with grpc.secure_channel(self.address, self.credentials) as channel:
            value = api_pb2_grpc.DiceServiceStub(channel).RollDie(api_pb2.RollDieRequest(), timeout=5).value
        if not 1 <= value <= 6:
            raise ValueError(f"DiceService returned invalid value {value}")
        return value
