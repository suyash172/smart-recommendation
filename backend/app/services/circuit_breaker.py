def is_retry_budget_exhausted(retry_count: int, max_retry_count: int) -> bool:
    """True when the transaction has used up its automated retries."""
    return retry_count >= max_retry_count