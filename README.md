# Simple, minimal blockchain built from scratch in Python

FastAPI serves the HTTP layer and Pydantic validates the payloads. Each process is one node: it keeps an account-balance chain, checks Ed25519 signatures, and mines with proof of work.

Transactions choose a fee of 1, 2, or 5. A block takes the ten highest fees that the sender can pay. The coinbase pays the miner the block reward plus those fees. While the mempool has transactions, a background loop mines on this node and pushes the block to registered peers. A block that does not link to the local tip triggers a pull of the longest valid chain.

## Next steps

- Add tests.
- Run a demo with a few nodes, using Docker or Kubernetes.

## Quick Start

- You need to have [uv](https://docs.astral.sh/uv/) for running the project so if you don't have it installed, please install it with pip:

```bash
pip install uv
```

- Install dependencies:

```bash
uv sync
```

### Start the development server

```bash
uv run fastapi dev
```

Visit http://localhost:8000

The miner address is printed in the log when the process starts. The coinbase of this node pays that address.

## Project Structure

- `main.py` - FastAPI application with endpoints
- `pyproject.toml` - Project dependencies
- `models.py` - Pydantic schemas
- `core/` - chain, blocks, transactions, consensus, and the mining loop
