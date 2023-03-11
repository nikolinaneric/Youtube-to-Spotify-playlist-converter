from django.db import models
import json

class UserToken(models.Model):
    uuid = models.CharField(max_length = 255, unique=True, default = None)
    token = models.TextField()

    def set_token(self, token_dict):
        self.token = json.dumps(token_dict)

    def get_token(self):
        return json.loads(self.token)
    
    class Meta:
        db_table = 'user_tokens'
        
class Playlists(models.Model):
    user_id = models.CharField(max_length = 255)
    playlist_title = models.CharField(max_length=255)
    uuid = models.CharField(max_length = 255, default = None)
    playlist_link = models.CharField(max_length=255, default = "")
    status = models.CharField(max_length=255, default = "in progress")
    class Meta:
        db_table = 'playlists'

class Songs(models.Model):
    playlist = models.ForeignKey(Playlists, on_delete = models.CASCADE)
    song_title = models.CharField(max_length=255)

    class Meta:
        db_table = 'songs'