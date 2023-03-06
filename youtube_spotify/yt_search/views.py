from .models import Playlists, Songs
from django.shortcuts import render, redirect
from django.conf import settings
from googleapiclient.discovery import build
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.contrib import messages
import json
from urllib.parse import urlencode, parse_qs
from ratelimit import limits


def create_auth_manager():
    auth_manager = SpotifyOAuth(client_id=settings.SPOTIPY_CLIENT_ID,
                                    client_secret=settings.SPOTIPY_CLIENT_SECRET,
                                    redirect_uri=settings.SPOTIPY_REDIRECT_URI,
                                    scope=settings.SPOTIPY_SCOPE)
    return auth_manager

def spotify(request):
    auth_manager = create_auth_manager()
    auth_url = auth_manager.get_authorize_url()
    return redirect(auth_url)


def user_auth(request):
    auth_manager = create_auth_manager()
    code = request.GET.get('code')
    token = auth_manager.get_access_token(code)
    token_json = json.dumps(token)
    # Encode JSON string as URL-safe string
    token_url = urlencode({'token': token_json})
    url = f'/search?token={token_url}'
    return redirect(url)

def search(request):
    encoded_url = request.GET.get('token', None)
    try:
        decoded_url = parse_qs(encoded_url)
        json_url = decoded_url['token'][0]
        token = json.loads(json_url)
    except:
        token = None
    print(token)
    print(type(token))
    print(token['expires_in'])
    auth_manager = create_auth_manager()
    if token is None or auth_manager.is_token_expired(token):
        return redirect('')
    headers = {
    'Authorization': 'Bearer ' + token['access_token'],
    'Content-Type': 'application/json'
    }
    try:
        sp = spotipy.Spotify(auth = headers) 
        user_id = sp.current_user()['id']
    except:
        messages.warning(request, 'Something went wrong. Please try again.')

    if request.method == 'POST':
        link = request.POST.get('link')
        link = link.split('list=')
        if len(link) <2:
            link = None
        else:
            link = link[1]
            link = link.split( '&')[0]
        
       
        api_key = settings.YOUTUBE_DATA_API_KEY
        youtube = build('youtube', 'v3', developerKey=api_key)

        playlist_id = link
        if playlist_id is not None:
            messages.success(request, 'We are making your playlist. You will be redirected to Spotify as soon as it is done.')
            try:
                #extracting the name of the playlist
                playlist_response = youtube.playlists().list(part='snippet', id=playlist_id).execute()
                playlist = playlist_response['items'][0]
                playlist_title = playlist['snippet']['title']
                playlist = Playlists.objects.create(user_id = user_id, playlist_title = playlist_title)
                print(playlist_title, 'NASLOV PLEJLISTE')
                
                # retrieving the songs from the playlist
                playlist_items = []
                next_page_token = None
                while True:
                    playlist_items_response = youtube.playlistItems().list(
                        part='snippet',
                        playlistId=playlist_id,
                        maxResults=50,
                        pageToken=next_page_token
                    ).execute()

                    playlist_items.extend(playlist_items_response['items'])

                    # Check if there are more items to retrieve
                    next_page_token = playlist_items_response.get('nextPageToken')
                    if not next_page_token:
                        break

                # extracting the titles of the songs
                songs = []
                for playlist_item in playlist_items:
                    video_title = playlist_item['snippet']['title']
                    songs.append(video_title)
                    

                # editing the title format to optimize the spotify search
                songs = [song.lower() for song in songs if song.lower() != 'deleted video' and 'private']
                substrings = ['lyrics','official','live','video','tekst','music','lyric','mp3','hq','spot','arena','bg','zagreb','studio'\
                            'audio','uzivo','uživo','hd','explicit','verzija', '*', '-','(',')','[',']',',','.']
                pattern = r'\(\d{4}\)|\(official video \d{4}\)\)|\[official audio \d{4}\)\]|\(audio \d{4}\)|\(video \d{4}\)|\(album version\)|\
                \(studio version\)|\(new version\)|\(old version\)|\(original version\)'
                for i in range(len(songs)):
                    songs[i] = songs[i].lower()
                    songs[i] = re.sub(pattern, '', songs[i])
                    for word in substrings:
                        songs[i] = songs[i].replace(word, '')
                    songs[i]= songs[i].strip()
                    Songs.objects.create(playlist = playlist, song_title = songs[i])
                playlist_link = make_playlist(sp)
                return redirect(playlist_link)
            except:
                messages.warning(request, 'Something went wrong. Please try again.')
        else:
            messages.error(request, "Your playlist link has an invalid format.")
    return render(request, 'yt_search/search.html')

def make_playlist(sp):
    user_id = sp.current_user()['id']
    playlist = Playlists.objects.filter(user_id = user_id).last()
    songs = Songs.objects.filter(playlist = playlist)
    print(songs)
    tracks = []
    for title in songs: 
        song = search_spotify(title, sp)
        if song not in tracks:
            tracks.append(song)
    playlist = sp.user_playlist_create(user_id, playlist.playlist_title, public=False)
    for i in range(0, len(tracks), 100):
        sp.playlist_add_items(playlist_id=playlist['id'], items=tracks[i:i+100])
    playlist_id = playlist['id']
    playlist_link = f"https://open.spotify.com/playlist/{playlist_id}"
    return playlist_link


@limits(calls=80, period=30)
def search_spotify(title, sp):
    results = sp.search(q=title.song_title, type='track', limit = 1)
    song = results['tracks']['items'][0]['uri']
    print(song, ' PJESMA ')
    return song
    
        
    
