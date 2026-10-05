from core.block import Block
from core.transaction import Transaction
from pydantic import BaseModel

class NewTransaction(BaseModel):
    sender: str
    recipient: str
    amount: int

class FullChain(BaseModel):
    chain: list[Block]
    length: int
    
class MineResponse(BaseModel):
    message: str
    index: int
    previous_hash: str
    proof: int
    transactions: list[Transaction]
    
class RegisterNodes(BaseModel):
    nodes: list[str]
    
class RegisterNodesResponse(BaseModel):
    message: str
    total_nodes: list[str]
    
class ResolveConflictsResponse(BaseModel):
    message: str
    chain: list[Block]