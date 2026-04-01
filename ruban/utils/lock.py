import redis
import time
import uuid

from ruban.config import REDIS_URL

redis_client = redis.from_url(f"{REDIS_URL}/2", decode_responses=True)


class RedisDistributedLock:
    def __init__(self, client: redis.Redis, lock_key: str, expire: int = 5):
        self.redis = client
        self.lock_key = lock_key
        self.expire = expire  # 锁过期时间（秒），防止死锁
        self.lock_value = str(uuid.uuid4())  # 唯一ID，防止误删别人的锁

    def acquire(self, blocking: bool = True, timeout: int = 10):
        """获取锁"""
        end = time.time() + timeout
        while True:
            # SET key value NX PX ：只有不存在才设置，原子操作
            if self.redis.set(
                self.lock_key,
                self.lock_value,
                nx=True,
                ex=self.expire
            ):
                return True

            if not blocking or time.time() > end:
                return False
            time.sleep(0.05)

    def release(self):
        """释放锁（Lua脚本保证原子性，只删自己的锁）"""
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        self.redis.eval(lua_script, 1, self.lock_key, self.lock_value)

    def __enter__(self):
        """支持 with 语法"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出自动释放"""
        self.release()


# 封装成你原来的 api_lock 格式
class RedisLock:
    def get_lock(self, key=-1):
        return RedisDistributedLock(redis_client, f"lock:{key}", expire=5)


redis_lock = RedisLock()
