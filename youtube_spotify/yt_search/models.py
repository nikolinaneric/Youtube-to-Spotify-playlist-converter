from django.db import models

class Playlists(models.Model):
    user_id = models.CharField(max_length = 255)
    playlist_title = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'playlists'

class Songs(models.Model):
    playlist = models.ForeignKey(Playlists, on_delete = models.CASCADE)
    song_title = models.CharField(max_length=255)

    class Meta:
        db_table = 'songs'