from collections import defaultdict
import logging
from time import time
from urllib import parse
from .block import Block
from core.transaction import Transaction
from core.exceptions import (
    InsufficientFundsError,
    DuplicatedTransactionError,
    DuplicatedBlockError,
    InvalidBlockError,
)

logger = logging.getLogger(__name__)


class Blockchain:
    def __init__(self):
        self.chain: list[Block] = []
        self.current_transactions: list[Transaction] = []
        self.nodes: set[str] = set()
        self.difficulty: int = 3
        # Initial block
        self.new_block(proof=100, previous_hash="1")
        logger.info("Blockchain initialized with genesis block")

    def difficulty_for(self, chain: list[Block], end: int) -> int:
        """
        Get the difficulty for a given chain and end
        :param chain: <list[Block]> Chain to get the difficulty
        :param end: <int> Height of the chain
        :return: <int> Difficulty
        """
        logger.debug("Calculating difficulty for end=%s", end)
        if end < 10:
            return self.difficulty
        if end % 10 != 0:
            return chain[end - 1].difficulty

        actual = chain[end - 1].timestamp - chain[end - 10].timestamp
        expected = 10 * 10
        difficulty = chain[end - 1].difficulty
        if actual < expected / 2:
            return min(difficulty + 1, 8)
        if actual > expected * 2:
            return max(difficulty - 1, 1)
        return difficulty

    def new_block(
        self,
        proof: int | None = None,
        previous_hash: str | None = None,
        is_pending_for_mining: bool = False,
        external_block: Block | None = None,  # For external blocks
    ) -> Block:
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :param is_pending_for_mining: <bool> True if the block is pending for mining, False otherwise
        :param external_block: <Block> External block to add to the chain
        :return: <Block> New Block
        """

        index_of_current_block = len(self.chain) + 1

        if external_block:
            for block in self.chain:
                if block.hash == external_block.hash:
                    raise DuplicatedBlockError(
                        f"Block {external_block.index} is duplicated"
                    )

            result = self.validate_block(external_block, self.last_block)
            if result == "fork":
                raise InvalidBlockError("fork")
            if result is not True:
                raise InvalidBlockError(f"Block {external_block.index} is invalid")

            if external_block.index != index_of_current_block:
                raise InvalidBlockError(
                    f"Block {external_block.index} is not the current block"
                )

            if external_block.difficulty != self.difficulty_for(
                chain=self.chain, end=len(self.chain)
            ):
                raise InvalidBlockError(
                    f"Block {external_block.index} has invalid difficulty"
                )

        block = external_block or Block(
            index=index_of_current_block,
            timestamp=int(time()),
            # Pending block has no proof
            nonce=proof or 0,
            previous_hash=previous_hash or self.last_block.hash,
            data=list(self.current_transactions),
            difficulty=self.difficulty_for(chain=self.chain, end=len(self.chain)),
        )

        if is_pending_for_mining:
            block.mine()

        tx_count = len(self.current_transactions)
        # Reset the current list of transactions
        transactions_of_external_block = (
            set(external_block.data)
            if external_block
            else set(self.current_transactions)
        )
        self.current_transactions = [
            tx
            for tx in self.current_transactions
            if tx not in transactions_of_external_block
        ]

        self.chain.append(block)
        logger.info(
            "Block forged index=%s nonce=%s txs=%s hash=%s",
            block.index,
            block.nonce,
            tx_count,
            block.hash,
        )
        return block

    def new_transaction(
        self,
        sender: str,
        recipient: str,
        amount: int,
        signature: str | None = None,
        timestamp: int | None = None,
    ) -> Transaction:
        """
        Creates a new transaction to go into the next mined Block.
        Transaction-level rules live in Transaction.validate();
        chain-level rules (balance) live here.

        :param sender: <str> Address of the sender
        :param recipient: <str> Address of the recipient
        :param amount: <int> Amount of the transaction
        :param signature: <str> Signature of the transaction
        :param timestamp: <int> Timestamp of the transaction
        :return: <Transaction> Created transaction
        """
        logger.debug(
            "New transaction requested sender=%s recipient=%s amount=%s has_signature=%s",
            sender,
            recipient,
            amount,
            bool(signature),
        )

        transaction = Transaction(
            sender,
            recipient,
            amount,
            timestamp=timestamp,
            signature=signature or "",
        )
        transaction.validate()

        if self.is_transaction_duplicated(transaction):
            raise DuplicatedTransactionError(
                f"Transaction {transaction.sender_address} -> {transaction.recipient_address} is duplicated"
            )

        if self.is_transaction_in_mempool(transaction):
            raise DuplicatedTransactionError(
                f"Transaction {transaction.sender_address} -> {transaction.recipient_address} is already in the mempool"
            )

        if not transaction.is_coinbase:
            available = self.get_balance(sender, include_pending_transactions=True)
            if available < amount:
                logger.warning(
                    "Insufficient funds sender=%s balance=%s amount=%s",
                    sender,
                    available,
                    amount,
                )
                raise InsufficientFundsError(
                    f"Sender does not have enough funds (balance={available}, amount={amount})"
                )

        target_block = self.last_block.index + 1
        self.current_transactions.append(transaction)
        logger.info(
            "Transaction accepted sender=%s recipient=%s amount=%s coinbase=%s pending_block=%s",
            sender,
            recipient,
            amount,
            transaction.is_coinbase,
            target_block,
        )
        return transaction

    def is_transaction_duplicated(
        self, transaction: Transaction, chain: list[Block] | None = None
    ) -> bool:
        """
        Check if a transaction is duplicated
        :param transaction: <Transaction> Transaction to check
        :param chain: <list[Block]> Chain to check
        :return: <bool> True if duplicated, False otherwise
        """
        chain = self.chain if chain is None else chain
        return any(tx == transaction for block in chain for tx in block.data)

    def is_transaction_in_mempool(self, transaction: Transaction) -> bool:
        """
        Check if a transaction is in the mempool
        :param transaction: <Transaction> Transaction to check
        :return: <bool> True if in the mempool, False otherwise
        """
        return any(tx == transaction for tx in self.current_transactions)

    @property
    def last_block(self) -> Block:
        """Returns the last Block in the chain
        :return: <Block> Last Block
        """
        assert self.chain is not None, "Chain is not set"
        return self.chain[-1]

    def register_node(self, address: str) -> None:
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """

        netloc = parse.urlparse(address).netloc
        self.nodes.add(netloc)
        logger.info(
            "Node registered address=%s netloc=%s total_nodes=%s",
            address,
            netloc,
            len(self.nodes),
        )

    def validate_block(
        self, block: Block, last_block: Block, chain: list[Block] | None = None
    ) -> bool | str:
        """
        Validate a block
        :param block: <Block> Block to validate
        :param last_block: <Block> Last block in the chain
        :return: <bool> True if valid, False if not
        """
        chain = self.chain if chain is None else chain

        pow_ok = (
            block.hash[: block.difficulty] == "0" * block.difficulty
        )
        links = block.previous_hash == last_block.hash
        if pow_ok and not links:
            return "fork"

        if not pow_ok or not links:
            return False

        seen_transactions = set()
        # Just one coinbase per block
        is_seen_coinbase = False
        accumulated_balance: defaultdict[str, int] = defaultdict(int)
        for past in chain:
            for tx in past.data:
                accumulated_balance[tx.sender_address] -= tx.amount
                accumulated_balance[tx.recipient_address] += tx.amount

        for tx in block.data:
            if self.is_transaction_duplicated(tx, chain=chain):
                return False

            if tx in seen_transactions:
                return False

            seen_transactions.add(tx)

            if tx.is_coinbase and (tx.amount != 1 or is_seen_coinbase):
                return False

            if tx.is_coinbase:
                is_seen_coinbase = True
                accumulated_balance[tx.recipient_address] += tx.amount
            else:
                accumulated_balance[tx.sender_address] -= tx.amount

                if accumulated_balance[tx.sender_address] < 0:
                    return False
                accumulated_balance[tx.recipient_address] += tx.amount

            try:
                tx.validate()
            except Exception as e:
                logger.warning(
                    "Transaction invalid at index=%s: error=%s",
                    block.index,
                    str(e),
                )
                return False

        if not is_seen_coinbase:
            return False

        return True

    def valid_chain(self, chain: list[Block]) -> bool:
        """
        Check if a given blockchain is valid
        :param chain: <list[Block]> Chain to check
        :return: <bool> True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if block.previous_hash != last_block.hash:
                logger.warning(
                    "Chain invalid at index=%s: previous_hash mismatch",
                    current_index,
                )
                return False

            if block.difficulty != self.difficulty_for(chain=chain, end=current_index):
                logger.warning(
                    "Chain invalid at index=%s: difficulty mismatch",
                    current_index,
                )
                return False

            logger.debug("Block hash=%s difficulty=%s", block.hash, block.difficulty)
            # Validate the proof of work like we mined the block
            if self.validate_block(block, last_block, chain=chain[:current_index]) is not True:
                logger.warning(
                    "Chain invalid at index=%s: invalid proof",
                    current_index,
                )
                return False

            last_block = block
            current_index += 1

        logger.debug("Chain valid length=%s", len(chain))
        return True

    def get_balance(
        self, address: str, include_pending_transactions: bool = False
    ) -> int:
        """
        Get the balance of an address
        :param address: <str> Address to get the balance of
        :param include_pending_transactions: <bool> Whether to include pending transactions in the balance
        :return: <int> Balance of the address
        """

        balance = 0
        for block in self.chain:
            for transaction in block.data:
                if transaction.sender_address == address:
                    balance -= transaction.amount
                if transaction.recipient_address == address:
                    balance += transaction.amount

        if include_pending_transactions:
            for transaction in self.current_transactions:
                if transaction.sender_address == address:
                    balance -= transaction.amount
                if transaction.recipient_address == address:
                    balance += transaction.amount
        return balance
