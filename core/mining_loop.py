from core.user import User
from logging import getLogger
from core.blockchain import Blockchain
import httpx
import asyncio

logger = getLogger(__name__)


class MiningLoop:
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain
        self.miner = User(name="Miner", id="miner")
        logger.info(
            f"Mining loop initialized for miner: {self.miner.name} and address: {self.miner.address}"
        )

    async def run(self) -> None:
        """
        Run the mining loop for the miner.
        :return: <None>
        """

        async with httpx.AsyncClient(timeout=None) as client:
            while True:
                if not len(self.blockchain.current_transactions) > 0:
                    await asyncio.sleep(10)
                    continue
                try:
                    response = await client.get(
                        f"http://localhost:8000/mine",
                        params={"address": self.miner.address},
                    )
                except Exception as e:
                    logger.error(f"Failed to mine a new block: {e}")
                    await asyncio.sleep(1)
                    continue

                if response.status_code == 200:
                    logger.info(f"Mined a new block: {response.json()}")
                else:
                    logger.error(f"Failed to mine a new block: {response.status_code}")
                    await asyncio.sleep(1)
                    continue
