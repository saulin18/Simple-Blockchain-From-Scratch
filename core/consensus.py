from core.blockchain import Blockchain
from logging import getLogger
import httpx
from models import BlockModel

logger = getLogger(__name__)


class Consensues:
    def __init__(self, nodes: set[str], blockchain: Blockchain):
        self.nodes = nodes
        self.blockchain = blockchain

    async def resolve_conflicts(self) -> bool:
        """
        This is the Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.blockchain.chain)
        logger.info(
            "Resolving conflicts local_length=%s neighbours=%s",
            max_length,
            len(neighbours),
        )
        async with httpx.AsyncClient() as client:
            for node in neighbours:
                url = f"http://{node}/chain"
                try:
                    response = await client.get(url)
                except httpx.HTTPError as exc:
                    logger.warning("Peer unreachable node=%s error=%s", node, exc)
                    continue
                if response.status_code != 200:
                    logger.warning(
                        "Peer bad status node=%s status=%s",
                        node,
                        response.status_code,
                    )
                    continue
                length = response.json().get("length")
                chain = response.json().get("chain")
                blocks = [
                    BlockModel.to_block(BlockModel.model_validate(raw)) for raw in chain
                ]
                logger.debug(
                    "Peer chain node=%s length=%s",
                    node,
                    length,
                )

                all_valid_transactions = True
                for block in blocks:
                    for transaction in block.data:
                        try:
                            transaction.validate()
                        except Exception as e:
                            logger.error(
                                "Invalid transaction in block %s: %s", block.index, e
                            )
                            all_valid_transactions = False
                            break

                if not all_valid_transactions:
                    continue

                if (
                    length > max_length
                    and self.blockchain.valid_chain(blocks)
                    and all_valid_transactions
                ):
                    logger.debug(
                        "Longer valid chain found node=%s length=%s",
                        node,
                        length,
                    )
                    max_length = length
                    new_chain = blocks
        if new_chain:
            old_length = len(self.blockchain.chain)
            self.blockchain.current_transactions = []
            self.blockchain.chain = new_chain
            logger.info(
                "Local chain replaced old_length=%s new_length=%s",
                old_length,
                len(self.blockchain.chain),
            )
            return True
        logger.info(
            "Local chain remains authoritative length=%s", len(self.blockchain.chain)
        )
        return False
