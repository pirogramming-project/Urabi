from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'accompany'

urlpatterns = [
    path('', views.AccompanyListView.as_view(), name='accompany_list'),
    path('detail/<int:pk>', views.AccompanyDetailView.as_view(), name='accompany_detail'),
    path('create', views.AccompanyCreateView.as_view(), name='accompany_create'),
    path('update/<int:pk>', views.AccompanyUpdateView.as_view(), name='accompany_update'),
    path('delete/<int:pk>', views.AccompanyDeleteView.as_view(), name='accompany_delete'),
    path('toggle-zzim/<int:travel_id>/', views.toggle_zzim, name='toggle_zzim'),
    path('add_participant/', views.add_participant, name='add_participant'),
    path('remove_participant/', views.remove_participant, name='remove_participant'),
    path('request/', views.apply_participant, name='request'),
    path('cancel/', views.cancel_participant, name='request_cancel'),
    path('load_plan_data/', views.load_plan_data, name='load_plan_data'),
]
