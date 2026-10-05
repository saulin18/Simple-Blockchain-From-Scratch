import hashlib
from time import time
from urllib import parse
import httpx
from .block import Block
from core.transaction import Transaction

class Blockchain():
    def __init__(self):
        self.chain: list[Block] = []
        self.current_transactions: list[Transaction] = []
        self.nodes: set[str] = set()

        # Initial block
        self.new_block(proof=100, previous_hash=1)

    def new_block(self, proof: int, previous_hash=None):
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = Block(
            index=len(self.chain) + 1,
            timestamp=int(time()),
            proof=proof,
            previous_hash=previous_hash or self.last_block.hash,
            data=self.current_transactions,
        )

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block
    
         
    def proof_of_work(self, last_proof: int) -> int:
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int) -> bool:
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def new_transaction(self, sender: str, recipient: str, amount: int) -> int:
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """
        transaction = Transaction(sender, recipient, amount)
        self.current_transactions.append(
            transaction
        )

        assert self.last_block is not None, "Last block is not set"
        return self.last_block.index + 1

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

        self.nodes.add(parse.urlparse(address).netloc)

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
                return False
            
            if not self.valid_proof(last_block.proof, block.proof):
                return False
            
            last_block = block
            current_index += 1

        return True
    
    async def resolve_conflicts(self) -> bool:
        """
        This is the Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)
        async with httpx.AsyncClient() as client:
            for node in neighbours:
                response = await client.get(f'http://{node}/chain')
                if response.status_code == 200:
                    length = response.json().get('length')
                    chain = response.json().get('chain')

                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        return False