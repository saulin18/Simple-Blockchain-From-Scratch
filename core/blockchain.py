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

MAX_TRANSACTIONS_PER_BLOCK = 10


class Blockchain:
    def __init__(self):
        self.chain: list[Block] = []
        self.current_transactions: list[Transaction] = []
        self.nodes: set[str] = set()
        self.difficulty: int = 3
        self.address_to_balance = defaultdict(int)
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

    def reward_for(self, end: int) -> int:
        """
        Get the reward for a given chain and end
        :param end: <int> Height of the chain
        :return: <int> Reward
        """
        reward = 100

        for _ in range(end // 10):
            reward = reward * 85 // 100

        return max(reward, 1)

    def coinbase_amount(self, end: int, transactions: list[Transaction]) -> int:
        """Subsidy for this height plus the fees of the transactions in the block."""
        fees = sum(tx.fee for tx in transactions if not tx.is_coinbase)
        return self.reward_for(end) + fees

    def select_transactions(self, balance: defaultdict[str, int]) -> list[Transaction]:
        """
        Transactions this node will put in the next block.
        Higher fee first. The cap is local policy: a block that arrives
        with another selection is still valid.
        """
        dropped: set[Transaction] = set()
        pending: list[Transaction] = []
        ordered = sorted(
            (tx for tx in self.current_transactions if not tx.is_coinbase),
            key=lambda tx: (-tx.fee, tx.timestamp or 0),
        )

        for tx in ordered:
            cost = tx.amount + tx.fee
            if cost > balance[tx.sender_address]:
                dropped.add(tx)
                continue
            if len(pending) >= MAX_TRANSACTIONS_PER_BLOCK:
                break
            balance[tx.sender_address] -= cost
            balance[tx.recipient_address] += tx.amount
            pending.append(tx)

        self.current_transactions = [
            tx for tx in self.current_transactions if tx not in dropped
        ]
        return pending

    def prepare_block(
        self, miner_address: str, transactions: list[Transaction]
    ) -> Block:
        """
        Prepares a block for mining with the given miner address and transactions, it does not mine the block.
        :param miner_address: <str> Address of the miner
        :param transactions: <list[Transaction]> Transactions to put in the block
        :return: <Block> Prepared block
        """

        selected = (
            transactions
            if transactions is not None
            else self.select_transactions(balance=self.address_to_balance.copy())
        )
        # Mined a new coin
        coinbase = Transaction(
            sender_address="0",
            recipient_address=miner_address,
            amount=self.coinbase_amount(len(self.chain), selected),
            fee=0,
        )
        data = [coinbase, *selected]

        block = Block(
            index=len(self.chain) + 1,
            timestamp=int(time()),
            nonce=0,
            previous_hash=self.last_block.hash,
            data=data,
            difficulty=self.difficulty_for(chain=self.chain, end=len(self.chain)),
        )

        return block

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

            result = self.validate_block(
                external_block,
                self.last_block,
                address_to_balance=self.address_to_balance.copy(),
            )
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

        if external_block:
            block = external_block
        else:

            data = list(self.current_transactions)

            block = Block(
                index=index_of_current_block,
                timestamp=int(time()),
                nonce=proof or 0,
                previous_hash=previous_hash or self.last_block.hash,
                data=data,
                difficulty=self.difficulty_for(chain=self.chain, end=len(self.chain)),
            )

        if is_pending_for_mining:
            block.mine()

        self.commit_block(block)
        return block

    def commit_block(self, block: Block) -> None:
        """
        Commits a block to the blockchain
        :param block: <Block> Block to commit
        :return: None
        """

        tx_count = len(block.data)
        included = set(block.data)
        self.current_transactions = [
            tx for tx in self.current_transactions if tx not in included
        ]

        self.chain.append(block)

        for tx in block.data:
            self.address_to_balance[tx.sender_address] -= tx.amount + tx.fee
            self.address_to_balance[tx.recipient_address] += tx.amount

        logger.info(
            "Block forged index=%s nonce=%s txs=%s hash=%s",
            block.index,
            block.nonce,
            tx_count,
            block.hash,
        )

    def new_transaction(
        self,
        sender: str,
        recipient: str,
        amount: int,
        signature: str | None = None,
        timestamp: int | None = None,
        fee: int = 0,
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
            "New transaction requested sender=%s recipient=%s amount=%s fee=%s has_signature=%s",
            sender,
            recipient,
            amount,
            fee,
            bool(signature),
        )

        transaction = Transaction(
            sender,
            recipient,
            amount,
            timestamp=timestamp,
            signature=signature or "",
            fee=fee,
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
            cost = amount + transaction.fee
            if available < cost:
                logger.warning(
                    "Insufficient funds sender=%s balance=%s amount=%s fee=%s",
                    sender,
                    available,
                    amount,
                    transaction.fee,
                )
                raise InsufficientFundsError(
                    f"Sender does not have enough funds (balance={available}, amount={amount}, fee={transaction.fee})"
                )

        target_block = self.last_block.index + 1
        self.current_transactions.append(transaction)
        logger.info(
            "Transaction accepted sender=%s recipient=%s amount=%s fee=%s coinbase=%s pending_block=%s",
            sender,
            recipient,
            amount,
            transaction.fee,
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

    def get_transaction_depth(self, transaction_signature: str) -> int:
        """
        Get the depth of a transaction
        :param transaction_signature: <str> Signature of the transaction
        :return: <int> Depth of the transaction
        """
        for block in self.chain:
            for transaction in block.data:
                if transaction.signature == transaction_signature:
                    return len(self.chain) - block.index + 1
        return 0

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
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:8000'
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
        self,
        block: Block,
        last_block: Block,
        chain: list[Block] | None = None,
        address_to_balance: defaultdict[str, int] | None = None,
    ) -> bool | str:
        """
        Validate a block
        :param block: <Block> Block to validate
        :param last_block: <Block> Last block in the chain
        :param chain: <list[Block]> Chain to validate
        :param address_to_balance: <defaultdict[str, int]> Address to balance
        :return: <bool> True if valid, False if not
        """
        chain = self.chain if chain is None else chain

        pow_ok = block.hash[: block.difficulty] == "0" * block.difficulty
        links = block.previous_hash == last_block.hash
        if pow_ok and not links:
            return "fork"

        if not pow_ok or not links:
            return False

        seen_transactions = set()
        # Just one coinbase per block
        is_seen_coinbase = False
        expected_coinbase = self.coinbase_amount(len(chain), block.data)
        accumulated_balance: defaultdict[str, int] = (
            address_to_balance
            if address_to_balance is not None
            else self.address_to_balance.copy()
        )
        # for past in chain:
        #     for tx in past.data:
        #         accumulated_balance[tx.sender_address] -= tx.amount
        #         accumulated_balance[tx.recipient_address] += tx.amount

        for tx in block.data:
            if self.is_transaction_duplicated(tx, chain=chain):
                return False

            if tx in seen_transactions:
                return False

            seen_transactions.add(tx)

            if tx.is_coinbase and (
                tx.amount != expected_coinbase or tx.fee != 0 or is_seen_coinbase
            ):
                return False

            if tx.is_coinbase:
                is_seen_coinbase = True
                accumulated_balance[tx.recipient_address] += tx.amount
            else:
                accumulated_balance[tx.sender_address] -= tx.amount + tx.fee

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
        address_to_balance = defaultdict(int)

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
            if (
                self.validate_block(
                    block,
                    last_block,
                    chain=chain[:current_index],
                    address_to_balance=address_to_balance,
                )
                is not True
            ):
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

        if include_pending_transactions:
            balance = self.address_to_balance[address]
            for tx in self.current_transactions:
                if tx.sender_address == address:
                    balance -= tx.amount + tx.fee

                if tx.recipient_address == address:
                    balance += tx.amount
            return balance

        return self.address_to_balance[address]
