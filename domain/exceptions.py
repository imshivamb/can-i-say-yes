class DomainError(Exception):
    """Base error for deterministic domain logic."""


class InvalidTransitionError(DomainError):
    """A commitment or decision moved to a status that is not allowed."""


class UnknownEntityError(DomainError):
    """A referenced world id does not exist."""
