import requests
from django.shortcuts import render
from django.conf import settings
from googleapiclient.discovery import build
import re

def search(request):

    if request.method == 'POST':
        link = request.POST.get('link')
        link = link.split('list=')[1]
        link = link.split( '&')[0]
        print(link)
        api_key = settings.YOUTUBE_DATA_API_KEY
        youtube = build('youtube', 'v3', developerKey=api_key)

        playlist_id = link
        playlist_response = youtube.playlists().list(part='snippet', id=playlist_id).execute()
        playlist = playlist_response['items'][0]
        playlist_title = playlist['snippet']['title']
        print(playlist_title, 'NASLOV PLEJLISTE')
        playlist_items = []
        next_page_token = None
        while True:
        # Retrieve a page of playlist items
            playlist_items_response = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            # Add the items to the playlist_items list
            playlist_items.extend(playlist_items_response['items'])

            # Check if there are more items to retrieve
            next_page_token = playlist_items_response.get('nextPageToken')
            if not next_page_token:
                break
        songs = []
        for playlist_item in playlist_items:
            video_title = playlist_item['snippet']['title']
            songs.append(video_title)
        songs = [song.lower() for song in songs if song.lower() != 'deleted video' and 'private']
        substrings = ['lyrics','official','live','with','video','tekst','music','lyric','mp3',\
                      'audio','uzivo','uživo','hd','-','(',')','[',']',',','.']
        pattern = r'\(\d{4}\)|\[official video \d{4}\)\]|\[official audio \d{4}\)\]|\(audio \d{4}\)|\(video \d{4}\)'
        for i in range(len(songs)):
            songs[i] = re.sub(pattern, '', songs[i])
            for word in substrings:
                songs[i] = songs[i].replace(word, '')
        songs = [song.strip() for song in songs if song!= 'private']
        print(songs)
        print(len(songs))

       
    return render(request, 'yt_search/search.html')
