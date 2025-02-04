import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from chat.routing import websocket_urlpatterns  # 채팅앱의 웹소켓 URL 패턴

# 1. Django 설정 파일 경로 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2. Django 초기화 (이렇게 해야 앱이 로드됨)
django.setup()

# 3. Django가 초기화된 후에 ASGI 애플리케이션을 가져옵니다.
application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # HTTP 요청 처리
    "websocket": AuthMiddlewareStack(  # 웹소켓 요청 처리
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
