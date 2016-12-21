import requests
import json
from os.path import expanduser

def getSubsonicCred():
    try:
        home = expanduser("~")
        # Need to have a text file named "subsonic_credentials.txt" in the Documents folder,
        # having each line list the Subsonic server's address, port, username, and password
        with open('{}/Documents/subsonic_credentials.txt'.format(home), 'r') as cfile:
            creds = cfile.read()
            clist = creds.split()
    except IOError:
        clist = []
        print('IOError, could not find ~/Documents/subsonic_credentials.txt')
    return clist

def combineArtists(albumsIn):
    # Take list of most frequently played albums, and combine all
    # common artists together, adding their albums' playCount
    combinedArtists = []
    for album in albumsIn:
        if combinedArtists:
            if album['artist'] not in iterAlbums(combinedArtists):
                combinedArtists.append(album)
            else:
                for artist in combinedArtists:
                    if artist['artist']==album['artist']:
                        #print('artist playcount: {}'.format(artist['playCount'])+ ', album playcount: {}'.format(album['playCount']))
                        artist['playCount']+=album['playCount']
                        #print('new artist playcount: {}'.format(artist['playCount']))
        else:
            combinedArtists.append(album)
    return combinedArtists

def iterAlbums(dictIn):
    # Create iterable list of artist names from album dictionary
    albums=[]
    for album in dictIn:
        albums.append(album['artist'])
    return albums
    
def extract_time(json):
    # Sorts combined artist list by playCount - which may get jumbled up
    # after adding up all the plays during combining artists from albums
    try:
        return int(json['playCount'])
    except KeyError:
        return 0

def getTopAlbums():
    clist = getSubsonicCred()
    # Get most frequently played albums - maximum of 500 albums
    r = requests.get('http://{}:{}/rest/getAlbumList2.view?u={}&p={}&f=json&v=1.14.0&c=myapp&type=frequent&size=500'.format(clist[0],clist[1],clist[2],clist[3]))

    topArtists = []
    top = r.json()
    albums = top['subsonic-response']['albumList2']['album']

    combined = combineArtists(albums)

    # Sort "combined" based on playCount
    combined.sort(key=extract_time, reverse=True)
    # Print out the top artists
    for album in combined:
        print(album['artist'] + ' (count = {})'.format(album['playCount']))
        topArtists.append({'artist_name':'{}'.format(album['artist'].encode('utf-8')),
                           'playCount': album['playCount'],'artist_id':'{}'.format(album['artistId'])})
    #print topArtists
    return topArtists
if __name__=='__main__': getTopAlbums()