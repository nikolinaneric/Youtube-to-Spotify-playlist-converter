from .models import Playlists, Songs, UserToken
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.conf import settings
import spotipy
from django.contrib import messages
from urllib.parse import urlencode
import requests
import time
import uuid
from youtube_spotify.celery import formating_and_storing_songs
from .utils import retrieving_songs

def home(request):
    # setting the unique user identifier into cookies
    response = render(request, 'yt_search/home.html')
    if 'user_uuid' in request.COOKIES:
        print(request.COOKIES.get('user_uuid'),'user_uuid')
    else:
        user_uuid = str(uuid.uuid4())
        response.set_cookie('user_uuid', user_uuid, max_age=164000)
        return redirect(request.get_full_path())
    return response


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
    user_uuid = request.COOKIES.get('user_uuid')
    if user_uuid is not None:
        user = UserToken.objects.filter(uuid = user_uuid).first()
        if not user:
            user = UserToken.objects.create(uuid = user_uuid)
        user.set_token(token)
        user.save()
    else:
        messages.warning(request, 'Something went wrong. Please try again.')
        return redirect(home)
    return redirect(search)

def search(request):
    """
    Ensures that the user provides a valid YouTube playlist link,
    and if that is the case envokes the JavaScript function that
    will redirect to the main view and open the loading screen until 
    the redirect page is ready.
    
    """
    user_uuid = request.COOKIES.get('user_uuid')
    playlists = Playlists.objects.filter(uuid = user_uuid).order_by('-id')
    in_progress = playlists.filter(status = 'in progress')
    warning = None
    r_url = None
    status = request.GET.get('status')
    if status == '500':
        warning = 'Something went wrong. Please try again.'
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
            r_url = reverse('in-progress') + '?link={}'.format(link)
            return redirect(r_url)
    context = {'warning': warning, 'r_url': r_url, 'playlists': playlists, 'in_progress': in_progress}
    return render(request, 'yt_search/search.html', context)


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
    user_uuid = request.COOKIES.get('user_uuid')
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

    playlist, songs = retrieving_songs(link, user_id, user_uuid)
    try:
        playlist_id = playlist.id
        formating_and_storing_songs.delay(playlist_id, songs, headers)
        return redirect('yt-search')
    except Exception as e:
        playlist.status = "failed"
        playlist.save()
        print(playlist.status)
        print(playlist.playlist_title)
        print(e)
        r_url = reverse('yt-search') + '?status=500'
        return redirect(r_url)
    
        
