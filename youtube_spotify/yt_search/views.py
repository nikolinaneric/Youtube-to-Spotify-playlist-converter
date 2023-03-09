from .models import Playlists, Songs, UserToken
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from googleapiclient.discovery import build
import re
import spotipy
from django.contrib import messages
from urllib.parse import urlencode
from ratelimit import limits, sleep_and_retry
import requests
import time
import uuid


def home(request):
    return render(request, 'yt_search/home.html')

def spotify(request):
    """
    Redirects the user to the Spotify authorization page to grant access to
    their Spotify account.
    """
    client_id = settings.SPOTIPY_CLIENT_ID
    redirect_uri = settings.SPOTIPY_REDIRECT_URI
    scope = settings.SPOTIPY_SCOPE

    params = {
    'client_id': client_id,
    'response_type': 'code',
    'redirect_uri': redirect_uri,
    'scope': scope,
}
    auth_url = 'https://accounts.spotify.com/authorize?' + urlencode(params)
    return redirect(auth_url)


def user_auth(request):
    """
    Handles the callback from the Spotify authorization page and retrieves
    an access token. The access token is then encoded as a URL-safe string
    and passed as a parameter in the redirect to the search page.
    """
    code = request.GET.get('code')
    params = {
    'client_id': settings.SPOTIPY_CLIENT_ID,
    'client_secret': settings.SPOTIPY_CLIENT_SECRET,
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': settings.SPOTIPY_REDIRECT_URI
    }
    token_url = 'https://accounts.spotify.com/api/token'
    response = requests.post(token_url, data=params)
    token = response.json()
    expires_at = int(time.time()) + int(token['expires_in'])
    token['expires_at'] = expires_at

    # setting the unique user identifier into session value
    # and storing it into the database together with the user's token
    user_uuid = str(uuid.uuid4())
    request.session['user_uuid'] = user_uuid
    user = UserToken.objects.create(uuid = user_uuid)
    user.set_token(token)
    user.save()
    return redirect(search)

def search(request):
    """
    Ensures that the user provides a valid YouTube playlist link,
    and if that is the case envokes the JavaScript function that
    will redirect to the main view and open the loading screen until 
    the redirect page is ready.
    
    """
    warning = None
    r_url = None
    if request.method == 'POST':
        link = request.POST.get('link')
        link = link.split('list=')
        if len(link)<2:
            link = None
            warning = "Your playlist link has an invalid format."
        elif 'radio' in link[1] :
            link = None
            warning = "The playlist is a Youtube generated mix."
        else:
            link = link[1]
            link = link.split( '&')[0]
            r_url =  '/in-progress?link={}'.format(link)
    context = {'warning': warning, 'r_url': r_url}
    return render(request, 'yt_search/search.html', context)

def retrieving_songs(link, user_id):
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
        start_time = time.time()
        print('pravim plejlistu')
        try:
            #extracting the name of the playlist
            playlist_response = youtube.playlists().list(part='snippet', id=playlist_id).execute()
            playlist = playlist_response['items'][0]
            playlist_title = playlist['snippet']['title']
            playlist = Playlists.objects.create(user_id = user_id, playlist_title = playlist_title)
            print(playlist_title, 'NASLOV PLEJLISTE')
            print(time.time() - start_time,'napravljena plejlista')
            print('izvlacim pjesme')
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
            print(time.time() - start_time,'zavrseno izvlacenje pjesama')
            print(songs)
            return playlist, songs
        except:
            pass

def formating_and_storing_songs(playlist, songs, sp):
    """
    This function edits the titles format to optimize the spotify search and then writes in the database those
    formated songs attached to the playlist object made earlier. After storing the playlist in the database, another function
    "make_playlist" is evoked that will return the link of the created Spotify playlist based on stored songs. 
    Parameters:
    playlist (database object): specific for spotify user id, containing the title of the playlist and belonging songs.
    sp (Spotify object): The Spotify object that represents the user's authorization to interact with the Spotify API.

    Returns:
    redirect link: The Spotify page with the newly created playlist.
    """
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
    playlist_link = make_playlist(sp)
    print(time.time() - start_time,'zavrseno pravljene plejliste spotify')
    return playlist_link

@sleep_and_retry
@limits(calls=10, period=1)
def search_spotify(title, sp):
    """
    This function searches the Spotify API for a track with a given title and returns the track's Spotify URI.
    The @limits decorator from the ratelimit library, which limits the number of API calls that can be made to
    Spotify to 80 calls per 30 seconds.

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
        print(song, ' PJESMA ')
    return song if song else None

def make_playlist(sp):
    """
    This function creates a new Spotify playlist and adds songs to it based on the most recently playlist from the database created
    for the current user.

    Parameters:
    sp (Spotify object): The Spotify object that represents the user's authorization to interact with the Spotify API.

    Returns:
    str: The link to the newly created Spotify playlist.
    """
    user_id = sp.current_user()['id']
    playlist = Playlists.objects.filter(user_id = user_id).last()
    songs = Songs.objects.filter(playlist = playlist)
    print(songs)
    tracks = []
    for title in songs:
        song = search_spotify(title, sp)
        if song not in tracks and song is not None:
            tracks.append(song)
    playlist = sp.user_playlist_create(user_id, playlist.playlist_title, public=False)
    for i in range(0, len(tracks), 100):
        sp.playlist_add_items(playlist_id=playlist['id'], items=tracks[i:i+100])
    playlist_id = playlist['id']
    playlist_link = f"https://open.spotify.com/playlist/{playlist_id}"
    return playlist_link


def main(request):
    """
    Handles the main functionality of the app, which is to create a new
    playlist in database based on a YouTube playlist provided by the user,
    which will later be transfered to Spotify playlist.
    The user must first grant access to their Spotify account before they can
    use this feature. After the user provides a valid YouTube playlist link,
    the app extracts the song titles from the playlist and uses the Spotify
    API to search for each song and add it to a new Spotify playlist. If the
    process is successful, the user is redirected to the new Spotify playlist.
    """
    user_uuid = request.session.get('user_uuid')
    user = get_object_or_404(UserToken, uuid=user_uuid)
    if user:
        token = user.get_token()
    else:
        token is None
    if token is None or time.time() > token['expires_at']:
        messages.warning(request, 'Please log in to your Spotify account')
        return redirect('spotify')
    headers = {
    'Authorization': 'Bearer ' + token['access_token'],
    'Content-Type': 'application/json'
    }
    try:
        sp = spotipy.Spotify(auth = headers)
    except:
        messages.warning(request, 'Something went wrong. Please try again.')
        return redirect('spotify')
    
    link = request.GET.get('link')
    user_id = sp.current_user()['id']

    try:
        playlist, songs = retrieving_songs(link, user_id)
        playlist_link = formating_and_storing_songs(playlist, songs, sp)
        return redirect(playlist_link)
    except:
        warning = 'Something went wrong. Please try again.'
        return redirect(request, 'yt_search/search.html', {'warning': warning})

