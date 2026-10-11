from datetime import timezone
from datetime import datetime
from nacl.signing import SigningKey
from .transaction import Transaction
from .exceptions import InvalidAddressError


class User:
    def __init__(self, name, id: str):
        self.name = name
        self.id = id
        self.signing_key = SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.created_at = datetime.now(tz=timezone.utc)
        self.updated_at = datetime.now(tz=timezone.utc)

    def __str__(self):
        return f"User(name={self.name}, id={self.id}, public_key={self.verify_key.encode().hex()})"

    def __repr__(self):
        return self.__str__()

    def sign(self, transaction: Transaction) -> str:
        if transaction.sender_address != self.address:
            raise InvalidAddressError(
                "Sender address does not match the user's address"
            )

        return transaction.sign(self.signing_key)

    def verify(self, transaction: Transaction) -> bool:
        return transaction.verify(self.verify_key)

    @property
    def address(self) -> str:
        return self.verify_key.encode().hex()
