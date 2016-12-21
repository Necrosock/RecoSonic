# coding=utf-8
import requests
import csv
import os
import sys
import time
import glob
import datetime
import sqlite3
import numpy as np
from os.path import expanduser
from pprint import pprint

home = expanduser("~")
msd_subset_path='{}/Downloads/MillionSongSubset'.format(home)
msd_subset_data_path=os.path.join(msd_subset_path,'data')
msd_subset_addf_path=os.path.join(msd_subset_path,'AdditionalFiles')
assert os.path.isdir(msd_subset_path),'wrong path' # sanity check
# path to the Million Song Dataset code
# CHANGE IT TO YOUR LOCAL CONFIGURATION
msd_code_path='{}/Downloads/MSongsDB-master'.format(home)
assert os.path.isdir(msd_code_path),'wrong path' # sanity check
# we add some paths to python so we can import MSD code
# Ubuntu: you can change the environment variable PYTHONPATH
# in your .bashrc file so you do not have to type these lines
sys.path.append( os.path.join(msd_code_path,'PythonSrc') )

# the following function simply gives us a nice string for
# a time lag in seconds
def strtimedelta(starttime,stoptime):
    return str(datetime.timedelta(seconds=stoptime-starttime))

def cleanCommas(text):
    fixed = text.replace('\,', ' ')
    fixed = fixed.replace('"', ' ')
    fixed = fixed.replace('\'', ' ')
    fixed = fixed.replace('{', ' ')
    fixed = fixed.replace('}', ' ')
    return fixed

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

def main():
    #utf-8 encoding test:
    #print('Fichier non trouvé')
    
    clist = getSubsonicCred()
    home = expanduser("~")
    
    # Create the artists.csv file containing all artists found in Subsonic
    with open('{}/Documents/artists.csv'.format(home), 'wb') as csvfile:
        fieldNamesIN = ['SubsonicArtistId','ArtistName','musicBrainzId','MSDID']
        artistAdd = csv.DictWriter(csvfile, fieldnames=fieldNamesIN)
        artistAdd.writeheader()
        
        # Connect into MSD's SQLite database file
        conn = sqlite3.connect(os.path.join(msd_subset_addf_path,
                                    'track_metadata.db'))
        
        # Get list of all artists
        r = requests.get('http://{}:{}/rest/getArtists.view?u={}&p={}&f=json&v=1.14.0&c=myapp'.format(clist[0],clist[1],clist[2],clist[3]))
        
        artistRes = r.json()
        
        ind = artistRes['subsonic-response']['artists']['index']
        
        t1 = time.time()
        # Artist count set to 0
        c=0
        err=0
        artists = []
        indLength = len(ind)
        # Loop through each letter in the index
        for let in ind:
            bands = let['artist']
            #print(bands)
            bandLength = len(bands)
            print('Number of bands in letter {}: {}'.format(let['name'],bandLength))
            for ar in bands:
                # getArtistInfo
                brainzId = ''
                artist_name = ''
                artist_name = cleanCommas(ar['name'].encode('utf-8')).strip()
                artist_sub_id = ar['id']
                arReq = requests.get('http://{}:{}/rest/getArtistInfo2.view?u={}&p={}&f=json&v=1.14.0&c=myapp&id='.format(clist[0],clist[1],clist[2],clist[3]) + artist_sub_id)
                arData = arReq.json()

                try:
                    artist_mb_id = arData['subsonic-response']['artistInfo2']['musicBrainzId']
                    #print('MB ID: {}'.format(artist_mb_id))
                except KeyError:
                    artist_mb_id = ''
                
                if artist_name != '':
                    #print('Clean name: {}'.format(artist_name))
                    q = 'SELECT DISTINCT artist_id FROM songs WHERE songs.artist_name = "{}\"'.format(artist_name)
                    #print(q)
                    # we query the MSD database to find the MSD ID
                    try:
                        res = conn.execute(q)
                        artist_msdid_sqlite = res.fetchall()
                        #print(artist_msdid_sqlite)
                        if artist_msdid_sqlite:
                            artist_msdid_sqlite = '{}'.format(artist_msdid_sqlite[0])[3:-3]
                        else:
                            artist_msdid_sqlite = ''
                        print(artist_msdid_sqlite)
                    except ValueError:
                        err+=1
                
                write = {'ArtistName': '{}'.format(artist_name), 
                             'SubsonicArtistId': '{}'.format(artist_sub_id),
                              'musicBrainzId': '{}'.format(artist_mb_id),
                               'MSDID': '{}'.format(artist_msdid_sqlite)}
                artists.append(write)
            print('Progress: {}%'.format(c*100/indLength))
            c+=1
        print('number of value errors: {}'.format(err))
        for art in artists:
            artistAdd.writerow(art)
        print('The total number of bands found is: {}'.format(len(artists)))
        t2 = time.time()
        print('The total time to find artist info is: {}'.format(strtimedelta(t1,t2)))

if __name__=='__main__': main()