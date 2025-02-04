# chat/redis_layer.py

from channels_redis.core import RedisChannelLayer
import asyncio

class CustomRedisChannelLayer(RedisChannelLayer):
    async def receive_single(self, channel, timeout=None):
        """
        이 함수는 BRPOP 명령어를 사용하여 대기 중인 메시지를 가져옵니다.
        `index=0`을 사용하여 첫 번째 Redis 서버 인스턴스를 사용합니다.
        """
        
        connection = await self.connection(index=0)  # index=0을 명시적으로 전달
        result = await connection.brpop(channel, timeout=timeout)
        return result
