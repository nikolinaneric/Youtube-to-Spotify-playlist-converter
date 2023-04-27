import os
import django
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtube_spotify.settings')

app = Celery('youtube_spotipy', broker="redis://localhost:6379/0")

app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


import spotipy
import time
from django.conf import settings
django.setup()
from yt_search.models import Playlists, Songs
from yt_search.utils import make_playlist, search_spotify
import re



@app.task
def formating_and_storing_songs(playlist_id, songs, headers):
    """
    This function edits the titles format to optimize the spotify search and then writes in the database those
    formated songs attached to the playlist object made earlier. After storing the playlist in the database, another function
    "make_playlist" is evoked that will return the link of the created Spotify playlist based on stored songs. 
    Parameters:
    playlist (database object): specific for spotify user id, containing the title of the playlist and belonging songs.
    sp (Spotify object): The Spotify object that represents the user's authorization to interact with the Spotify API.


    """
   
    sp = spotipy.Spotify(auth = headers)
    playlist = Playlists.objects.filter(id=playlist_id).first()
    start_time = time.time()
    # editing the title format to optimize the spotify search
    songs = [song.lower() for song in songs if song.lower() != 'deleted video' and 'private']
    substrings = ['lyrics','official','live','video','tekst','music','lyric','mp3','hq','spot','arena','bg','zagreb','studio'
                'audio','uzivo','uživo','hd','explicit','ep','album','verzija', 'version','full','album','stream' '*', '-','(',')','[',']',',','.']
    pattern = r'\(\d{4}\)|\(official video \d{4}\)\)|\[official video \d{4}\)\]|\(official audio \d{4}\)\)|\[official audio \d{4}\)\)]|\(official audio\)|\(official video\)|\(audio \d{4}\)|\(video \d{4}\)|\(album version\)|\
    \(studio version\)|\(new version\)|\(old version\)|\(original version\)'
    for i in range(len(songs)):
        songs[i] = songs[i].lower()
        songs[i] = re.sub(pattern, '', songs[i])
        for word in substrings:
            songs[i] = songs[i].replace(word, '')
        songs[i]= songs[i].strip()
        Songs.objects.create(playlist = playlist, song_title = songs[i])
    print(time.time() - start_time, 'zavrseno upisivanje u bazu')
    make_playlist(sp)
    print(time.time() - start_time,'zavrseno pravljene plejliste spotify')
    

    
