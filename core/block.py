import hashlib
import json
from core.transaction import Transaction


class Block():
    def __init__(
        self,
        index: int,
        previous_hash: str,
        timestamp: int,
        data: list[Transaction],
        proof: int,
    ):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.proof = proof
        self._hash = self.hash

    def __repr__(self):
        return f"Block(index={self.index}, previous_hash={self.previous_hash}, \
    timestamp={self.timestamp}, data={self.data}, proof={self.proof})"

    def to_dict(self) -> dict[str, int | str | list[Transaction]]:
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data,
            "proof": self.proof,
        }

    @property
    def hash(self) -> str:
        """
        Creates a SHA-256 hash of a Block
        :return: <str>
        """
        block_string = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
