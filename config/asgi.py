import os
from django.core.asgi import get_asgi_application

# 1. Django settings 모듈 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2. Django ASGI application 초기화 (이 시점에 Django 앱이 로드됨)
django_asgi_app = get_asgi_application()

# 3. 다른 모듈들은 Django 초기화 후에 import
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chat.routing import websocket_urlpatterns

# 4. ASGI 애플리케이션 설정
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})