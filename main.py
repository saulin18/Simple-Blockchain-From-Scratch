from fastapi.responses import JSONResponse
from core.exceptions import (
    DuplicatedTransactionError,
    InvalidBlockError,
    DuplicatedBlockError,
    BlockchainError,
)
from fastapi import Depends, BackgroundTasks
from typing import Any, cast
from core.consensus import Consensues
from models import BlockModel
import uvicorn
from fastapi import FastAPI, Request
from logging_config import LOGGING_CONFIG
from typing import TypedDict

from core.blockchain import Blockchain
from core.transaction import Transaction
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


def get_consensues(blockchain: Blockchain = Depends(get_blockchain)) -> Consensues:
    return Consensues(blockchain.nodes, blockchain)


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
async def mine(
    background_tasks: BackgroundTasks,
    request: MineRequest,
    blockchain: Blockchain = Depends(get_blockchain),
    validator: Consensues = Depends(get_consensues),
) -> MineResponse:
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

    background_tasks.add_task(
        validator.push_block_to_neighbours, BlockModel.from_block(block)
    )

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


@app.post("/blocks/new")
async def new_block(
    background_tasks: BackgroundTasks,
    block: BlockModel,
    blockchain: Blockchain = Depends(get_blockchain),
    validator: Consensues = Depends(get_consensues),
):
    """
    Receive a new block from a neighbour and add it to the blockchain. Push a block to the blockchain.
    """
    logger.info("POST /blocks/new index=%s hash=%s", block.index, block.hash)
    external_block = BlockModel.to_block(block)

    try:
        blockchain.new_block(external_block=external_block)
    except (DuplicatedBlockError, InvalidBlockError) as e:
        if isinstance(e, InvalidBlockError) and e.reason == "fork":
            background_tasks.add_task(validator.resolve_conflicts)
        return JSONResponse(content={"message": str(e)}, status_code=400)
    background_tasks.add_task(validator.push_block_to_neighbours, block)
    return JSONResponse(content={"message": "Block accepted"}, status_code=200)


@app.post("/transactions/new")
async def new_transaction(
    background_tasks: BackgroundTasks,
    transaction: TransactionModel,
    blockchain: Blockchain = Depends(get_blockchain),
    validator: Consensues = Depends(get_consensues),
):
    logger.info(
        "POST /transactions/new from=%s to=%s amount=%s",
        transaction.from_address,
        transaction.to_address,
        transaction.amount,
    )
    is_coinbase = transaction.from_address == "0"
    if is_coinbase:
        return JSONResponse(
            content={"message": "Coinbase transaction is not allowed"}, status_code=400
        )

    try:
        created_transaction: Transaction = blockchain.new_transaction(
            transaction.from_address,
            transaction.to_address,
            transaction.amount,
            transaction.signature,
            transaction.timestamp,
        )
    except DuplicatedTransactionError as e:
        return JSONResponse(content={"message": str(e)}, status_code=400)

    background_tasks.add_task(
        validator.push_transaction_to_neighbours,
        TransactionModel.from_transaction(created_transaction),
    )

    return {
        "message": f"Transaction will be added to Block {blockchain.last_block.index + 1}"
    }


@app.get("/balance/{address}")
def get_balance(
    address: str,
    blockchain: Blockchain = Depends(get_blockchain),
    include_pending: bool = False,
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
