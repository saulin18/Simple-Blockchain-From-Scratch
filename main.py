
from fastapi import Depends
from core.exceptions import BlockchainError
from typing import Any, cast
from core.consensus import Consensues
from models import BlockModel
import uvicorn
from fastapi import FastAPI, Request
from logging_config import LOGGING_CONFIG
from typing import TypedDict

from core.blockchain import Blockchain

from fastapi.middleware.cors import CORSMiddleware

from models import (
    TransactionModel,
    FullChain,
    MineResponse,
    RegisterNodes,
    RegisterNodesResponse,
    ResolveConflictsResponse,
    MineRequest,
)
from logging import getLogger
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from middlewares import blockchain_error_handler, RequestContextLogMiddleware 

logger = getLogger(__name__)


class LifespanState(TypedDict):
    blockchain: Blockchain


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[LifespanState, Any]:
    lifespan_state = LifespanState(blockchain=Blockchain())
    yield lifespan_state
    # close clients, release any open resources

def get_blockchain(http: Request) -> Blockchain:
    state = cast(LifespanState, http.state)
    return state["blockchain"]

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextLogMiddleware)
app.add_exception_handler(BlockchainError, blockchain_error_handler)

@app.get("/")
def main():
    logger.info("Hello World")
    return {"message": "Hello World"}


@app.get("/mine")
def mine(request: MineRequest, blockchain: Blockchain = Depends(get_blockchain)) -> MineResponse:
    # The sender is "0" to signify that this node has mined a new coin.
    request.validate_address()
    blockchain.new_transaction(
        sender="0",
        recipient=request.address,
        amount=1,
    )
    last_block_hash = blockchain.last_block.hash

    block = blockchain.new_block(is_pending_for_mining=True)
    logger.info("Mine completed index=%s hash=%s", block.index, block.hash)

    return MineResponse(
        message="New Block Forged",
        index=block.index,
        previous_hash=last_block_hash,
        proof=block.nonce,
        transactions=[
            TransactionModel.from_transaction(transaction)
            for transaction in blockchain.last_block.data
        ],
        timestamp=blockchain.last_block.timestamp,
        hash=blockchain.last_block.hash,
    )


@app.post("/transactions/new")
def new_transaction(transaction: TransactionModel, blockchain: Blockchain = Depends(get_blockchain)):
    logger.info(
        "POST /transactions/new from=%s to=%s amount=%s",
        transaction.from_address,
        transaction.to_address,
        transaction.amount,
    )
    index = blockchain.new_transaction(
        transaction.from_address,
        transaction.to_address,
        transaction.amount,
        transaction.signature,
        transaction.timestamp,
    )
    return {"message": f"Transaction will be added to Block {index}"}


@app.get("/balance/{address}")
def get_balance(
    address: str, blockchain: Blockchain = Depends(get_blockchain), include_pending: bool = False
):
    balance = blockchain.get_balance(
        address, include_pending_transactions=include_pending
    )
    return {"address": address, "balance": balance}


@app.get("/chain")
def full_chain(blockchain: Blockchain = Depends(get_blockchain)) -> FullChain:
    logger.debug("GET /chain length=%s", len(blockchain.chain))
    return FullChain(
        chain=[BlockModel.from_block(block) for block in blockchain.chain],
        length=len(blockchain.chain),
    )


@app.post("/nodes/register")
def register_nodes(
    nodes: RegisterNodes, blockchain: Blockchain = Depends(get_blockchain)
) -> RegisterNodesResponse:
    logger.info("POST /nodes/register count=%s", len(nodes.nodes))
    for node in nodes.nodes:
        blockchain.register_node(node)
    return RegisterNodesResponse(
        message="New nodes have been added", total_nodes=list(blockchain.nodes)
    )


@app.get("/nodes/resolve")
async def consensus(
    blockchain: Blockchain = Depends(get_blockchain),
) -> ResolveConflictsResponse:
    logger.info("GET /nodes/resolve")
    validator = Consensues(blockchain.nodes, blockchain)
    replaced = await validator.resolve_conflicts()
    if replaced:
        return ResolveConflictsResponse(
            message="Our chain was replaced",
            chain=[BlockModel.from_block(block) for block in blockchain.chain],
        )

    return ResolveConflictsResponse(
        message="Our chain is authoritative",
        chain=[BlockModel.from_block(block) for block in blockchain.chain],
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info",
        log_config=LOGGING_CONFIG,
    )
