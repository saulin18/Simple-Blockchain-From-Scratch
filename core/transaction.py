from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from nacl.signing import SigningKey
import json
import time
import logging

from core.exceptions import (
    InvalidAddressError,
    InvalidAmountError,
    InvalidSignatureError,
    SelfTransferError,
)

logger = logging.getLogger(__name__)

COINBASE_SENDER = "0"


class Transaction:
    def __init__(
        self,
        sender_address: str,
        recipient_address: str,
        amount: int,
        timestamp: int | None = None,
        signature: str = "",
    ):
        self.sender_address = sender_address
        self.recipient_address = recipient_address
        self.amount = amount
        self.timestamp = timestamp if timestamp is not None else int(time.time())
        self.signature = signature

    def to_dict(self) -> dict[str, str | int]:
        return {
            "sender": self.sender_address,
            "recipient": self.recipient_address,
            "amount": self.amount,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return (
            f"Transaction(sender={self.sender_address}, "
            f"recipient={self.recipient_address}, amount={self.amount})"
        )

    @property
    def is_coinbase(self) -> bool:
        return self.sender_address == COINBASE_SENDER

    def update_signature(self, signature: str) -> None:
        self.signature = signature

    def sign(self, private_key: SigningKey) -> str:
        message = json.dumps(self.to_dict(), sort_keys=True).encode()
        signature = private_key.sign(message).signature
        self.update_signature(signature.hex())
        return self.signature

    def verify(self, public_key: VerifyKey) -> bool:
        message = json.dumps(self.to_dict(), sort_keys=True).encode()

        try:
            public_key.verify(message, bytes.fromhex(self.signature))
            return True
        except (BadSignatureError, ValueError):
            return False

    def validate(self) -> None:
        if self.amount <= 0:
            logger.warning(
                "Invalid amount sender=%s amount=%s",
                self.sender_address,
                self.amount,
            )
            raise InvalidAmountError("Amount must be greater than zero")

        if self.sender_address == self.recipient_address:
            logger.warning(
                "Sender and recipient are the same address=%s",
                self.sender_address,
            )
            raise SelfTransferError("Sender and recipient cannot be the same")

        if self.is_coinbase:
            return

        if not self.signature or self.timestamp is None:
            raise InvalidSignatureError("Signature and timestamp are required")

        try:
            public_key = VerifyKey(bytes.fromhex(self.sender_address))
        except (ValueError, TypeError) as exc:
            logger.warning(
                "Invalid sender address sender=%s error=%s",
                self.sender_address,
                exc,
            )
            raise InvalidAddressError("Invalid sender address") from exc

        if not self.verify(public_key):
            logger.warning(
                "Invalid signature sender=%s recipient=%s amount=%s",
                self.sender_address,
                self.recipient_address,
                self.amount,
            )
            raise InvalidSignatureError("Signature is not valid")
