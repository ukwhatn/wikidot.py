class Client:
    def __init__(
            self,
            api: bool = False,
            async_limit: int = 40,
            semaphore_limit: int = 30,
            async_interval: float = 0,
            retry_limit_on_error: int = 6,
            retry_interval_on_error: float = 5,
            request_timeout: float = 40
    ):
        
