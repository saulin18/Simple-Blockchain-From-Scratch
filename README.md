# Simple, minimal blockchain built from scratch in Python

I'm using FastAPI for the HTTP layer, Pydantic for validating data. 

Next steps:

- Implement P2P, signatures, a better PoW, Docker, variable difficulty to mine.
- Maybe a mining loop
- Maybe a demo with some nodes using Docker with replicas mechanism or Kubernetes

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

## Project Structure

- `main.py` - FastAPI application with endpoints
- `pyproject.toml` - Project dependencies
- `models.py` - Pydantic schemas

In `core` we have the logic for the blockchain. It's simple at this moment, I plan to develop more in the meantime, stay tuned! 
