
from django.urls import path
from . import views

urlpatterns = [
    path('', views.spotify, name="spotify"),
    path('spotify/callback/', views.user_auth, name="user-auth"),
    path('search/', views.search, name="yt-search"),
    path('/success/', views.success, name="yt-success"),
]

