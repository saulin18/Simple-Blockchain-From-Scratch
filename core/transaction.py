
class Transaction:
    def __init__(self, sender: str, recipient: str, amount: int):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount

    def to_dict(self) -> dict[str, str | int]:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
        }
        
    def __repr__(self) -> str:
        return f"Transaction(sender={self.sender}, recipient={self.recipient}, amount={self.amount})"
    