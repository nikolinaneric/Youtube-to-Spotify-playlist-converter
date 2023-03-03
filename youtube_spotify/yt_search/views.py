from .models import Songs
from django.shortcuts import render, redirect
from django.conf import settings
from googleapiclient.discovery import build
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.core.cache import cache
from django.contrib import messages


def search(request):

    if request.method == 'POST':
        link = request.POST.get('link')
        link = link.split('list=')[1]
        link = link.split( '&')[0]
       
        api_key = settings.YOUTUBE_DATA_API_KEY
        youtube = build('youtube', 'v3', developerKey=api_key)

        playlist_id = link
        try:
            #extracting the name of the playlist
            playlist_response = youtube.playlists().list(part='snippet', id=playlist_id).execute()
            playlist = playlist_response['items'][0]
            playlist_title = playlist['snippet']['title']
            print(playlist_title, 'NASLOV PLEJLISTE')
            
            # retrieving the songs from the playlist
            playlist_items = []
            next_page_token = None
            while True:
                playlist_items_response = youtube.playlistItems().list(
                    part='snippet, contentDetails', 
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
                video_title = playlist_item['snippet']['title'],
                video_id = playlist_item['snippet']['resourceId']['videoId']
                thumbnail_url = playlist_item['snippet']['thumbnails'].get('high').get('url') if playlist_item['snippet']['thumbnails'] else None
            
                songs.append(video_title[0])
                #songs.append({'id':video_id,'title': video_title,'thumbnail_url':thumbnail_url,'duration': duration})

            # editing the title format to make spotify search more successfull
            songs = [song.lower() for song in songs if song.lower() != 'deleted video' and 'private']
            substrings = ['lyrics','official','live','with','video','tekst','music','lyric','mp3',\
                        'audio','uzivo','uživo','hd','-','(',')','[',']',',','.']
            pattern = r'\(\d{4}\)|\(official video \d{4}\)\)|\[official audio \d{4}\)\]|\(audio \d{4}\)|\(video \d{4}\)'
            for i in range(len(songs)):
                songs[i] = songs[i].lower()
                songs[i] = re.sub(pattern, '', songs[i])
                for word in substrings:
                    songs[i] = songs[i].replace(word, '')
                songs[i]= songs[i].strip()
                Songs.objects.create(title = songs[i])
            print(songs)
            messages.success(request, 'Your playlist will be made as soon you aprove the access to your spotify account.')
            return redirect('/sp')
        except:
            messages.error(request, 'Something went wrong. Maybe the link you\'ve provided isn\'t in the right format. Please try again.')

    
    return render(request, 'yt_search/search.html')

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

def make_playlist(request):
    auth_manager = create_auth_manager()
    code = request.GET.get('code')
    access_token = auth_manager.get_access_token(code)
    if auth_manager.is_token_expired(access_token):
        access_token = auth_manager.refresh_access_token(access_token['refresh_token'])
    
    headers = {
    'Authorization': 'Bearer ' + access_token['access_token'],
    'Content-Type': 'application/json'
}
    sp = spotipy.Spotify(auth = headers)
    songs = [song.title for song in Songs.objects.all()]
    print(songs)
    tracks = []
    for title in songs: 
        results = sp.search(q=title, type='track', limit = 1)
        song = results['tracks']['items'][0]['uri']
        print(song, ' PJESMA ')
        tracks.append(song)
    user_id = sp.current_user()['id']
    playlist = sp.user_playlist_create(user_id, 'Teodora', public=False)
    sp.playlist_add_items(playlist_id=playlist['id'], items=tracks)
    return render(request, 'yt_search/success.html')
    