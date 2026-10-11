import hashlib
import json
from core.transaction import Transaction


class Block:
    def __init__(
        self,
        index: int,
        nonce: int,
        previous_hash: str,
        timestamp: int,
        data: list[Transaction],
        difficulty: int,
    ):
        self.index = index
        self.nonce = nonce
        self.difficulty = difficulty
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data

    def __repr__(self):
        return (
            f"Block(index={self.index}, previous_hash={self.previous_hash}, "
            f"timestamp={self.timestamp}, data={self.data}, nonce={self.nonce})"
        )

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": [
                {**transaction.to_dict(), "signature": transaction.signature}
                for transaction in self.data
            ],
            "hash": self.hash,
        }

    @property
    def hash(self) -> str:
        block_data = {
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": [transaction.to_dict() for transaction in self.data],
            "nonce": self.nonce,
            "difficulty": self.difficulty,
        }
        block_string = json.dumps(block_data, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def mine(self) -> "Block":
        while self.hash[: self.difficulty] != "0" * self.difficulty:
            self.nonce += 1
        return self
