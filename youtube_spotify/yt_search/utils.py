from django.conf import settings
from .models import Playlists, Songs
from ratelimit import limits, sleep_and_retry
from googleapiclient.discovery import build
import time



def retrieving_songs(link, user_id, user_uuid):
    """
    The extraction of the playlist name and the song's title is done with Google api client and Youtube API.
    The playlist object is created in database with the playlist name attached to the spotify user id. 

    Parameters:
    link (str): extracted playlist ID from url upon which will youtube search be done
    user_id (str): spotify user id obtained via Spotify object 

    Returns:
    playlist(database object), songs(list).
    """
    playlist_id = link
    api_key = settings.YOUTUBE_DATA_API_KEY
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    if playlist_id is not None:
        try:
            #extracting the name of the playlist
            playlist_response = youtube.playlists().list(part='snippet', id=playlist_id).execute()
            playlist = playlist_response['items'][0]
            playlist_title = playlist['snippet']['title']
            playlist = Playlists.objects.create(uuid = user_uuid, user_id = user_id, playlist_title = playlist_title)
          
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
            return playlist, songs
        except:
            pass

@sleep_and_retry
@limits(calls=10, period=1)
def search_spotify(title, sp):
    """
    This function searches the Spotify API for a track with a given title and returns the track's Spotify URI.
    The @limits decorator from the ratelimit library, which limits the number of API calls that can be made to
    Spotify to 10 calls per second.

    Parameters:
    title (str): The title of the song to search for.
    sp (Spotify object): The Spotify object that represents the user's authorization to interact with the Spotify API.

    Returns:
    str: The Spotify URI of the track that matches the search query.
    """
    results = sp.search(q=title.song_title, type='track', limit = 1)
    song = None
    if results['tracks']['items']:
        song = results['tracks']['items'][0]['uri']
    return song if song else None



        
def make_playlist(sp):
    """
    This function creates a new Spotify playlist and adds songs to it based on the most recently playlist from the database created
    for the current user.

    Parameters:
    sp (Spotify object): The Spotify object that represents the user's authorization to interact with the Spotify API.

    """
    user_id = sp.current_user()['id']
    playlist = Playlists.objects.filter(user_id = user_id).last()
    songs = Songs.objects.filter(playlist = playlist)
    tracks = []
    for title in songs:
        song = search_spotify(title, sp)
        if song not in tracks and song is not None:
            tracks.append(song)
    spotify_playlist = sp.user_playlist_create(user_id, playlist.playlist_title, public=False)
    for i in range(0, len(tracks), 100):
        sp.playlist_add_items(playlist_id=spotify_playlist['id'], items=tracks[i:i+100])
    spotify_playlist_id = spotify_playlist['id']
    spotify_playlist_link = f"https://open.spotify.com/playlist/{spotify_playlist_id}"
    playlist.playlist_link = spotify_playlist_link
    playlist.status = "done"
    playlist.save()
