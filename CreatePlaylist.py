# coding=utf-8
import requests
import csv
import os
import sys
import time
from time import strftime
import glob
import datetime
import sqlite3
import getTopAlbumsList
from getTopAlbumsList import getTopAlbums
import numpy as np
import random
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

def extract_time_sim(json):
    try:
        # Also convert to int since update_time will be string.  When comparing
        # strings, "10" is smaller than "2".
        return float(json['Similarity'])
    except KeyError:
        return 0

def getRecommendedArtists(SUBID):
    home = expanduser("~")
    with open('{}/Documents/edgesOUT.csv'.format(home), 'rb') as csvINfile:
        fieldNamesIN = ['SubsonicArtistIdA','SubsonicArtistIdB','Similarity']
        artistRead = csv.DictReader(csvINfile, fieldnames=fieldNamesIN)
        next(artistRead)
        RecomIDs = []
        for artist in artistRead:
            if artist['SubsonicArtistIdA']==SUBID:
                RecomIDs.append(artist)
        
        RecomIDs.sort(key=extract_time_sim, reverse=True)
        #print(RecomIDs)
    return RecomIDs

def getSGRecommendedArtists(SUBID):
    RecomIDs = []
    r = requests.get('http://localhost:9080/systemg/api/rest/graphs/RecoSonic/vertices/{}/outE'.format(SUBID))
    top = r.json()
    #print(top['edges'])
    #print(len(top['edges']))
    for edge in top['edges']:
        if edge['source']==SUBID:
            RecomIDs.append({'SubsonicArtistIdA': edge['source'],
                             'SubsonicArtistIdB': edge['target'],
                             'Similarity': format(edge['Similarity'])})
        else:
            RecomIDs.append({'SubsonicArtistIdA': edge['target'],
                             'SubsonicArtistIdB': edge['source'],
                             'Similarity': format(edge['Similarity'])})
    #print(RecomIDs)
    #print(len(RecomIDs))
    RecomIDs.sort(key=extract_time_sim, reverse=True)
    return RecomIDs

def getArtistName(SUBID):
    artist_name = ''
    home = expanduser("~")
    with open('{}/Documents/artists.csv'.format(home), 'rb') as csvINfile2:
        fieldNamesIN2 = ['SubsonicArtistId','ArtistName','musicBrainzId','MSDID']
        artistRead2 = csv.DictReader(csvINfile2, fieldnames=fieldNamesIN2)
        next(artistRead2)
        for artist in artistRead2:
            if artist['SubsonicArtistId']==SUBID:
                artist_name = artist['ArtistName']
                break
    return artist_name

def cleanIdsToArtistIds(cleanIds):
    cleanIdsList = []
    for Id in cleanIds:
        for artist in Id:
            cleanIdsList.append(artist['SubsonicArtistIdB'])
    return cleanIdsList

def cleanRecommendations(RecomIds, SeedComplete, RecArtistsTotal):
    SeedIds = []
    for seed in SeedComplete:
        SeedIds.append(seed['artist_id'])
    cleanIds = []
    for Id in RecomIds:
        if Id['SubsonicArtistIdB'] in SeedIds:
            pass
        elif Id['SubsonicArtistIdB'] in cleanIdsToArtistIds(RecArtistsTotal):
            pass
        else:
            cleanIds.append({'SubsonicArtistIdB': Id['SubsonicArtistIdB'],
                             'Similarity': Id['Similarity'],
                             'artist_name': getArtistName(Id['SubsonicArtistIdB'])})
    return cleanIds

def getTopSongs(artistName):
    TopSongs = []
    clist = getSubsonicCred()
    r = requests.get('http://{}:{}/rest/getTopSongs.view?u={}&p={}&f=json&v=1.14.0&c=myapp&artist='.format(clist[0],clist[1],clist[2],clist[3]) + artistName)
    top = r.json()
    try:
        songs = top['subsonic-response']['topSongs']['song']
        for song in songs:
            TopSongs.append(song)
    except KeyError:
        print('Could not find top songs for {}.'.format(artistName))
    return TopSongs

def getAlbums(SUBID):
    albums = []
    clist = getSubsonicCred()
    r = requests.get('http://{}:{}/rest/getArtist.view?u={}&p={}&f=json&v=1.14.0&c=myapp&id='.format(clist[0],clist[1],clist[2],clist[3]) + SUBID)
    top = r.json()
    try:
        albumsComplete = top['subsonic-response']['artist']['album']
        #print(albumsComplete)
        for album in albumsComplete:
            albums.append(album['id'])
    except KeyError:
        print('Could not find albums for {}.'.format(SUBID))
    return albums

def getSongs(AIDs):
    songs = []
    clist = getSubsonicCred()
    for album in AIDs:
        r = requests.get('http://{}:{}/rest/getAlbum.view?u={}&p={}&f=json&v=1.14.0&c=myapp&id='.format(clist[0],clist[1],clist[2],clist[3]) + album)
        top = r.json()
        #print(top)
        tracks = top['subsonic-response']['album']['song']
        for track in tracks:
            songs.append(track['id'])
    return songs

def removeTopSongs(AllSongsIdList, TopSongsIdList):
    cleanSongIdList = []
    for allsong in AllSongsIdList:
        if allsong in TopSongsIdList:
            pass
        else:
            cleanSongIdList.append(allsong)
    return cleanSongIdList

def makePlaylistName():
    return 'RecoSonic-{}'.format(strftime('%d-%b-%Y_%H-%M-%S',time.localtime()))

def songlistToText(songlist):
    text = '&songId='.join(songlist)
    return text

def makePlaylist(songlist):
    clist = getSubsonicCred()
    r = requests.get('http://{}:{}/rest/createPlaylist.view?u={}&p={}&f=json&v=1.14.0&c=myapp&name={}&songId={}'.format(clist[0],clist[1],clist[2],clist[3],makePlaylistName(), songlistToText(songlist)))
    return

def main():

    PlaylistSize = 100

    SeedIn = getTopAlbumsList.getTopAlbums()
    
    totalPlays = 0
    
    for artist in SeedIn:
        totalPlays+=artist['playCount']
    
    print('Total number of artist plays = {}'.format(totalPlays))
    
    SeedSubset = []
    SeedNum = 0
    SeedSize = 0
    while SeedNum < 0.8*totalPlays:
        SeedNum+=SeedIn[SeedSize]['playCount']
        SeedSubset.append(SeedIn[SeedSize])
        SeedSize+=1
    
    print('Total number of artists spanning 80% of total plays = {}'.format(SeedSize))
    
    TotalSubsetPlays = 0
    for artist in SeedSubset:
        TotalSubsetPlays+=artist['playCount']
    
    SeedComplete = []
    for artist in SeedSubset:
        SeedComplete.append({'artist_id': artist['artist_id'], 
                             'playCount': artist['playCount'], 
                             'artist_name': artist['artist_name'],
                             'playlistPortion': (artist['playCount']*PlaylistSize)/TotalSubsetPlays})
        
    RecArtistsTotal = []
    Playlist = []
    leftOverSongNum = 0
    
    for i in range(1):
        for seed in SeedComplete:
            # get all recommended artist per target, sorted by similarity
            print('original playlistPortion for this artist: {}'.format(seed['playlistPortion']))
            seed = {'artist_id': seed['artist_id'], 
                             'playCount': seed['playCount'], 
                             'artist_name': seed['artist_name'],
                             'playlistPortion': (seed['playlistPortion']+leftOverSongNum)}
            print('new playlistPortion for this artist: {}'.format(seed['playlistPortion']))
            RecArtists = getSGRecommendedArtists(seed['artist_id'])
            # get rid of any artists if they are already in SeedComplete or RecArtistsTotal
            RecArtists = cleanRecommendations(RecArtists, SeedComplete, RecArtistsTotal)
            RecArtistsTotal.append(RecArtists)
            # keep top 3 recommended artists
            RecArtists = RecArtists[0:3] 
            # for each recommended artist
            print('Artist: {}, Number of Songs Needed: {}'.format(seed['artist_name'],seed['playlistPortion']))
            for recArtist in RecArtists:
                
                # retrieve top songs and count them
                top = getTopSongs(recArtist['artist_name'])
                topNum = len(top)
                print('    Number of top songs for {} (similarity={}): {}'.format(recArtist['artist_name'],recArtist['Similarity'],topNum))
                # if there are as many songs as playlistPortion, append that many into Playlist
                recPortion = int(round(seed['playlistPortion']/3))
                if topNum > recPortion:
                    GrabbedSongs = random.sample(top, recPortion)
                    for song in GrabbedSongs:
                        print('adding song ID: {}'.format(song['id']))
                        Playlist.append(song['id'])
                # else, append all top songs into playlist AND
                else:
                    print('not enough top songs for this artist')
                    for song in top:
                        Playlist.append(song['id'])
                    # count total number of songs by recommended artist
                    allSongs = getSongs(getAlbums(recArtist['SubsonicArtistIdB']))
                    randSongToGrabFromNum = len(allSongs)-topNum
                    allSongs = removeTopSongs(allSongs, Playlist)
                    # if there are enough total songs:
                    if len(allSongs) > recPortion:
                        # remove the songs already in Playlist
                        print('there are enough total songs to grab from here.')
                        # grab enough random songs by recommended artist to make up playlistPortion
                        RandSongs = random.sample(allSongs, randSongToGrabFromNum)
                        for randSong in RandSongs:
                            Playlist.append(randSong)
                    # else, grab all songs by recommended artist AND
                    else:
                        whateverNum = len(allSongs)
                        for allsong in allSongs:
                            Playlist.append(allsong)
                        # give next artist the leftover song number
                        leftOverSongNum = recPortion - topNum - whateverNum
        
        if len(Playlist)>=PlaylistSize:
            Playlist = random.sample(Playlist, PlaylistSize)
            break
        else:
            i+=1
        
    print(Playlist)
    print('size of playlist: {}'.format(len(Playlist)))
    makePlaylist(Playlist)

if __name__=="__main__": main()