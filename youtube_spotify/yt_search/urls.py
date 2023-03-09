
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('spotify-auth', views.spotify, name="spotify"),
    path('spotify/callback', views.user_auth, name="user-auth"),
    path('search/', views.search, name="yt-search"),
    path('in-progress/', views.main, name="in-progress"),
  
]

