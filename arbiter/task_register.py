from typing import Callable
from arbiter.task.tasks import (
    ArbiterAsyncTask,
    ArbiterHttpTask,
    ArbiterPeriodicTask,
    ArbiterSubscribeTask
)

class TaskRegister:
    
    def regist_task(self, task: ArbiterAsyncTask):
        raise NotImplementedError("handle_task method must be implemented")
    
    def async_task(
        self,
        queue: str = None,
        num_of_tasks: int = 1,
        timeout: float = 10,
        retries: int = 3,
        retry_delay: float = 1,
        strict_mode: bool = True,
        log_level: str | None = None,
        log_format: str | None = None        
    ):
        # 데코레이터 함수 정의
        task = ArbiterAsyncTask(
            queue=queue,
            num_of_tasks=num_of_tasks,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            strict_mode=strict_mode,
            log_level=log_level,
            log_format=log_format
        )
        def decorator(func: Callable) -> Callable:
            self.regist_task(task)
            return task(func)
        return decorator

    def periodic_task(
        self,
        interval: float,
        queue: str = None,
        num_of_tasks: int = 1,
        timeout: float = 10,
        retries: int = 3,
        retry_delay: float = 1,
        strict_mode: bool = True,
        log_level: str | None = None,
        log_format: str | None = None
    ):
        task = ArbiterPeriodicTask(
            interval=interval,
            queue=queue,
            num_of_tasks=num_of_tasks,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            strict_mode=strict_mode,
            log_level=log_level,
            log_format=log_format
        )
        # 데코레이터 함수 정의
        def decorator(func: Callable) -> Callable:
            self.regist_task(task)
            return task(func)
        return decorator

    def subscribe_task(
        self,
        queue: str = None,
        num_of_tasks: int = 1,
        timeout: float = 10,
        retries: int = 3,
        retry_delay: float = 1,
        strict_mode: bool = True,
        log_level: str | None = None,
        log_format: str | None = None   
    ):
        # 데코레이터 함수 정의
        task = ArbiterSubscribeTask(
            queue=queue,
            num_of_tasks=num_of_tasks,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            strict_mode=strict_mode,
            log_level=log_level,
            log_format=log_format
        )
        def decorator(func: Callable) -> Callable:
            self.regist_task(task)
            return task(func)
        return decorator