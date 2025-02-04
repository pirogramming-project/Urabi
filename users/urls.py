from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static
from .views import get_csrf_token
from .views import get_token_for_logged_in_user

app_name = 'users'

urlpatterns = [
    path('users/', views.login_view, name='main'),  
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('login/kakao/', views.kakao_login, name='kakao-login'),
    path('login/kakao/callback/', views.kakao_login_callback, name='kakao-callback'),
    path('login/naver/', views.naver_login, name='naver-login'),
    path('login/naver/callback/', views.naver_login_callback, name='naver-callback'),
    path('logout/', views.user_logout, name='logout'),

    path('mypage/', views.my_page, name='my_page'),
    path('mypage/edit', views.edit_profile, name='edit_profile'),
    path("csrf/", views.get_csrf_token, name="get_csrf_token"),
    path('api/get_token/', views.get_token_for_logged_in_user, name='get_token'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)