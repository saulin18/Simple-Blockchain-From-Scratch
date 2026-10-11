class BlockchainError(Exception):
    """Base error for blockchain business rules."""


class InvalidTransactionError(BlockchainError):
    """Transaction violates protocol rules."""


class InvalidSignatureError(InvalidTransactionError):
    """Signature missing or does not match sender public key."""


class InvalidAddressError(InvalidTransactionError):
    """Address is not a valid public key encoding."""


class InsufficientFundsError(InvalidTransactionError):
    """Sender balance is lower than the transfer amount."""


class InvalidAmountError(InvalidTransactionError):
    """Amount is not allowed (e.g. negative or zero)."""


class SelfTransferError(InvalidTransactionError):
    """Sender and recipient must be different."""
