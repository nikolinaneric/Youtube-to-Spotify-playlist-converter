
from django.urls import path
from . import views

urlpatterns = [
    path('', views.search, name="yt-search"),
    path('sp', views.spotify, name="spotify"),
    path('spotify/callback/', views.make_playlist, name="success")
]
