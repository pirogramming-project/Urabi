from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

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
    path('mypage/edit/', views.edit_profile, name='edit_profile'),
    path('mypage/trip/', views.my_trip, name='my_trip'),
    path('mypage/trip/update/<int:pk>', views.update_trip, name='update_trip'),
    path('mypage/trip/delete/<int:pk>/', views.delete_trip, name='delete_trip'),
    path('mypage/detail/<int:pk>/', views.user_detail, name='user_detail'),
    path('mypage/plan/<int:pk>/', views.plan_detail, name='plan_detail'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)