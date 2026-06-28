# components/redis_component.py
import redis
import json
from typing import Optional, List, Dict
import logging

from core.string_constants import QUEUE_NAMES
from core.config import Config

logger = logging.getLogger(__name__)

class RedisQueue:
    """
    Dedicated Redis component for queue management.
    Handles all interactions with Redis.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password,
            db=config.redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        self.task_queue = QUEUE_NAMES['task_queue']
        self.result_queue = QUEUE_NAMES['result_queue']
        self.failure_queue = QUEUE_NAMES['failure_queue']
    
    def push_task(self, task: Dict) -> bool:
        """Push a task to the queue."""
        try:
            self.client.rpush(self.task_queue, json.dumps(task))
            return True
        except Exception as e:
            logger.error(f"Failed to push task: {e}")
            return False
    
    def push_tasks(self, tasks: List[Dict]) -> int:
        """Push multiple tasks to the queue."""
        count = 0
        for task in tasks:
            if self.push_task(task):
                count += 1
        return count
    
    def pop_task(self, timeout: int = 5) -> Optional[Dict]:
        """Pop a task from the queue (blocking)."""
        try:
            result = self.client.blpop(self.task_queue, timeout=timeout)
            if result:
                return json.loads(result[1])
            return None
        except Exception as e:
            logger.error(f"Failed to pop task: {e}")
            return None
    
    def push_result(self, result: Dict) -> bool:
        """Push a result to the results queue."""
        try:
            self.client.rpush(self.result_queue, json.dumps(result))
            return True
        except Exception as e:
            logger.error(f"Failed to push result: {e}")
            return False
    
    def pop_result(self) -> Optional[Dict]:
        """Pop a result from the results queue."""
        try:
            result = self.client.lpop(self.result_queue)
            if result:
                return json.loads(result)
            return None
        except Exception as e:
            logger.error(f"Failed to pop result: {e}")
            return None
    
    def pop_all_results(self) -> List[Dict]:
        """Pop all available results."""
        results = []
        while True:
            result = self.pop_result()
            if result is None:
                break
            results.append(result)
        return results
    
    def push_failure(self, failure: Dict) -> bool:
        """Push a failure to the failure queue."""
        try:
            self.client.rpush(self.failure_queue, json.dumps(failure))
            return True
        except Exception as e:
            logger.error(f"Failed to push failure: {e}")
            return False
    
    def get_queue_size(self) -> Dict[str, int]:
        """Get sizes of all queues."""
        return {
            'tasks': self.client.llen(self.task_queue),
            'results': self.client.llen(self.result_queue),
            'failures': self.client.llen(self.failure_queue)
        }
    
    def clear_queues(self) -> None:
        """Clear all queues."""
        self.client.delete(self.task_queue)
        self.client.delete(self.result_queue)
        self.client.delete(self.failure_queue)
    
    def health_check(self) -> bool:
        """Check if Redis is healthy."""
        try:
            return self.client.ping()
        except Exception:
            return False
    
    def close(self) -> None:
        """Close Redis connection."""
        self.client.close()