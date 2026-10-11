from core.exceptions import InvalidAddressError
from nacl.signing import VerifyKey
from core.block import Block
from core.transaction import Transaction
from pydantic import BaseModel


class TransactionModel(BaseModel):
    from_address: str
    to_address: str
    amount: int
    signature: str
    timestamp: int

    @classmethod
    def from_transaction(cls, transaction: Transaction) -> "TransactionModel":
        return TransactionModel(
            from_address=transaction.sender_address,
            to_address=transaction.recipient_address,
            amount=transaction.amount,
            signature=transaction.signature,
            timestamp=transaction.timestamp,
        )

    @classmethod
    def to_transaction(cls, transaction: "TransactionModel") -> Transaction:
        return Transaction(
            transaction.from_address,
            transaction.to_address,
            transaction.amount,
            timestamp=transaction.timestamp,
            signature=transaction.signature,
        )


class BlockModel(BaseModel):
    index: int
    nonce: int
    previous_hash: str
    transactions: list[TransactionModel]
    timestamp: int
    hash: str
    difficulty: int

    @classmethod
    def from_block(cls, block: Block) -> "BlockModel":
        return BlockModel(
            index=block.index,
            nonce=block.nonce,
            previous_hash=block.previous_hash,
            transactions=[
                TransactionModel.from_transaction(transaction)
                for transaction in block.data
            ],
            timestamp=block.timestamp,
            hash=block.hash,
            difficulty=block.difficulty,
        )

    @classmethod
    def to_block(cls, block: "BlockModel") -> Block:
        return Block(
            index=block.index,
            nonce=block.nonce,
            previous_hash=block.previous_hash,
            timestamp=block.timestamp,
            data=[
                TransactionModel.to_transaction(transaction)
                for transaction in block.transactions
            ],
            difficulty=block.difficulty,
        )


class FullChain(BaseModel):
    chain: list[BlockModel]
    length: int


class MineResponse(BaseModel):
    message: str
    index: int
    previous_hash: str
    proof: int
    transactions: list[TransactionModel]
    timestamp: int
    hash: str

    @classmethod
    def from_block(cls, block: Block) -> "MineResponse":
        return MineResponse(
            message="New Block Forged",
            index=block.index,
            previous_hash=block.previous_hash,
            proof=block.nonce,
            transactions=[
                TransactionModel.from_transaction(transaction)
                for transaction in block.data
            ],
            timestamp=block.timestamp,
            hash=block.hash,
        )


class RegisterNodes(BaseModel):
    nodes: list[str]


class RegisterNodesResponse(BaseModel):
    message: str
    total_nodes: list[str]


class ResolveConflictsResponse(BaseModel):
    message: str
    chain: list[BlockModel]
    
class MineRequest(BaseModel):
    address: str
    
    def validate_address(self) -> None:
        try:
            VerifyKey(bytes.fromhex(self.address))
        except Exception as e:
            raise InvalidAddressError(f"Invalid address: {e}")
