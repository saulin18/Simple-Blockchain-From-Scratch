from models import FullChain
import uvicorn
from fastapi import FastAPI

app = FastAPI()
from uuid import uuid4
from core.blockchain import Blockchain
from models import (
    NewTransaction,
    FullChain,
    MineResponse,
    RegisterNodes,
    RegisterNodesResponse,
    ResolveConflictsResponse,
)


@app.get("/")
def main():
    return {"message": "Hello World"}


node_identifier = str(uuid4()).replace("-", "")
blockchain = Blockchain()


@app.get("/mine")
def mine() -> MineResponse:
    last_block = blockchain.last_block
    last_proof = last_block.proof
    proof = blockchain.proof_of_work(last_proof)

    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )
    return MineResponse(
        message="New Block Forged",
        index=blockchain.new_block(proof, previous_hash=last_block.hash).index,
        previous_hash=last_block.hash,
        proof=proof,
        transactions=blockchain.last_block.data,
    )


@app.post("/transactions/new")
def new_transaction(transaction: NewTransaction):
    return blockchain.new_transaction(
        transaction.sender, transaction.recipient, transaction.amount
    )


@app.get("/chain")
def full_chain() -> FullChain:
    return FullChain(chain=blockchain.chain, length=len(blockchain.chain))


@app.post("/nodes/register")
def register_nodes(nodes: RegisterNodes) -> RegisterNodesResponse:
    for node in nodes.nodes:
        blockchain.register_node(node)
    return RegisterNodesResponse(
        message="New nodes have been added", total_nodes=list(blockchain.nodes)
    )


@app.get("/nodes/resolve")
async def consensus() -> ResolveConflictsResponse:
    replaced = await blockchain.resolve_conflicts()
    if replaced:
        return ResolveConflictsResponse(
            message="Our chain was replaced", chain=blockchain.chain
        )

    return ResolveConflictsResponse(
        message="Our chain is authoritative", chain=blockchain.chain
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
