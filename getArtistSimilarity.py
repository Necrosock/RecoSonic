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

def MSDIDtoSUBID(MSDID,Sublist):
    # Convert an MSD ID to the Subsonic ID
    SUBID = ''
    for artist in Sublist:
        if artist['MSDID']==MSDID:
#           print(artist['SubsonicArtistId'])
            SUBID = artist['SubsonicArtistId']
            break
    return SUBID

def SUBIDtoMSDID(SUBID,Sublist):
    # Convert a Subsonic ID to the MSD ID
    MSDID = ''
    for artist in Sublist:
        if artist['SubsonicArtistId']==SUBID:
#           print(artist['SubsonicArtistId'])
            MSDID = artist['MSDID']
            break
    return MSDID

def MSDIDandSUBIDlist():
    # Reads the artists.csv file created by GetArtists and returns a list
    # of dictionaries containing all the data
    home = expanduser("~")
    with open('{}/Documents/artists.csv'.format(home), 'rb') as csvINfile:
        fieldNamesIN = ['SubsonicArtistId','ArtistName','musicBrainzId','MSDID']
        artistRead = csv.DictReader(csvINfile, fieldnames=fieldNamesIN)
        
        next(artistRead)
        IDs = []
        for artist in artistRead:
            IDs.append({'ArtistName':artist['ArtistName'],
                        'SubsonicArtistId':artist['SubsonicArtistId'],
                        'musicBrainzId':artist['musicBrainzId'],
                        'MSDID':artist['MSDID']})
    return IDs

def listOfMSDID():
    home = expanduser("~")
    # returns list of SUBSONIC IDs of artists that have an MSDID!!
    with open('{}/Documents/artists.csv'.format(home), 'rb') as csvINfile2:
        fieldNamesIN2 = ['SubsonicArtistId','ArtistName','musicBrainzId','MSDID']
        artistRead2 = csv.DictReader(csvINfile2, fieldnames=fieldNamesIN2)
        
        next(artistRead2)
        MSDIDs = []
        for artist in artistRead2:
            if artist['MSDID']:
                MSDIDs.append(artist['SubsonicArtistId'])
    return MSDIDs

def listOfMSDIDtext(loMSDID):
    # Combines all MSD IDs to a text file for SQL query
    textOut = ''
    if loMSDID[0]['MSDID']:
        textOut = loMSDID[0]['MSDID']
    for MSDID in loMSDID:
        if MSDID['MSDID']:
            if textOut=='':
                textOut = '\'{}\''.format(MSDID['MSDID'])
            else:
                textOut = textOut + ',' + '\'{}\''.format(MSDID['MSDID'])
    return textOut

def strtimedelta(starttime,stoptime):
    return str(datetime.timedelta(seconds=stoptime-starttime))

def cleanUp(text):
    fixed = text.replace(',', ' ').replace('"', ' ')
    return fixed

def uniquePairs(list):
    # Only keep a single combination of items in an artist recommendation list
    # This saves us from calculating unnecessary duplicate similarities
    cleanList = []
    for pair in list:
        A = pair[0]
        B = pair[1]
        if [A,B] in cleanList or [B,A] in cleanList:
            pass
        else:
            cleanList.append(pair)
    return cleanList

def combineCleanPairs(list1, list2):
    # Combines the recommendations from MSD with Subsonic, excluding duplicates
    combinedCleanList = list1
    for pair in list2:
        A = pair[0]
        B = pair[1]
        if [A,B] in combinedCleanList or [B,A] in combinedCleanList:
            pass
        else:
            combinedCleanList.append(pair)
    return combinedCleanList

def calculateSimilarity(list1, list2):
    # Takes list of tags for each artist 
    # and calculates the similarity based on
    # number of shared tags
    shared = float(0)
    len1 = len(list1)
    #print(len1)
    len2 = len(list2)
    #print(len2)
    if len1 == 0 and len2 == 0:
        # Default similarity is 0.3 based on trial and error - 
        # bump this up if you want Subsonic's recommendation
        # to be more influential on overall recommendation
        similarity = 0.3
    else:
        for item1 in list1:
            for item2 in list2:
                if item1 == item2:
                    shared += 1
        try:
            similarity = shared/(len1+len2-shared)
        except ZeroDivisionError:
            similarity = 1
    return similarity

def main():

    clist = getSubsonicCred()
    home = expanduser("~")

    with open('{}/Documents/edgesOUT.csv'.format(home), 'wb') as edgesOUTfile:
        fieldNames = ['SubsonicArtistIdA','SubsonicArtistIdB','Similarity']
        similarityAdd = csv.DictWriter(edgesOUTfile, fieldnames=fieldNames)
        
        similarityAdd.writeheader()
        
        conn = sqlite3.connect(os.path.join(msd_subset_addf_path,
                                'artist_similarity.db'))
        
        
        edges = []
        similarityMSD = []
        similaritySUB = []
        t1 = time.time()
        artistRead = MSDIDandSUBIDlist()
        print('Number of artists read: {}'.format(len(artistRead)))
        queryInputText = listOfMSDIDtext(artistRead)
        for artist in artistRead:
#                print(artist_MSDID)
            # we build the SQL query
            q = 'SELECT target, similar FROM similarity WHERE similarity.target = "{}\" AND similarity.similar IN ({})'.format(artist['MSDID'],queryInputText)
#                print(q)
            # we query the database 
            res = conn.execute(q)
            artist_sim = res.fetchall()
#                print(artist_sim)
            for target in artist_sim:
#                print('{} --> {}'.format(target[0],target[1]))
                edges.append([target[0],target[1]])
                
        t2 = time.time()
        print 'Got list of all MSD similarities in:',strtimedelta(t1,t2)
        print('Number of edges found by MSD: {}'.format(len(edges)))
        edges = uniquePairs(edges)
        t3 = time.time()
        print 'Cleaned and got only unique pairs in:',strtimedelta(t2,t3)
        print('Number of unique edges found by MSD: {}'.format(len(edges)))
        i = 0
        for edge in edges:
            artistA = MSDIDtoSUBID(edge[0],artistRead)
            artistB = MSDIDtoSUBID(edge[1],artistRead)
            if artistA != '' and artistB != '':
                similarityMSD.append([artistA, artistB])
            i+=1
        t4 = time.time()
        print 'Converted the MSDIDs to SUBIDs:',strtimedelta(t3,t4)
        
        artistRead2 = MSDIDandSUBIDlist()
        for artist in artistRead2:
            targetArtist = artist['SubsonicArtistId']
            arReq = requests.get('http://{}:{}/rest/getArtistInfo2.view?u={}&p={}&f=json&v=1.14.0&c=myapp&id={}'.format(clist[0],clist[1],clist[2],clist[3],targetArtist))
            arData = arReq.json()
            try:
                recommended = arData['subsonic-response']['artistInfo2']['similarArtist']
                if recommended:
                    for recArtist in recommended:
                        similaritySUB.append([targetArtist,recArtist['id']])
            except KeyError:
                pass
        t5 = time.time()
        print('Number of Subsonic recommendations found: {}'.format(len(similaritySUB)))
        print 'Grabbed Subsonic recommendations in:',strtimedelta(t4,t5)
        similaritySUB = uniquePairs(similaritySUB)
        t6 = time.time()
        print('Number of unique Subsonic recommendations found: {}'.format(len(similaritySUB)))
        print 'Got all unique Subsonic recommendations in:',strtimedelta(t5,t6)
        similarity = combineCleanPairs(similarityMSD, similaritySUB)
        t7 = time.time()
        print('Number of similarities found by MSD and Subsonic: {}'.format(len(similarity)))
        print 'Combined all unique recommendations in:',strtimedelta(t6,t7)
        
        connTerms = sqlite3.connect(os.path.join(msd_subset_addf_path,
                                'artist_term.db'))
        artistRead3 = MSDIDandSUBIDlist()
        
        for tuple1 in similarity:
            artist1 = tuple1[0]
            artist2 = tuple1[1]
            sim = 0.3
            loIDs = listOfMSDID()
            # look for MSDID for each artist
            if artist1 in loIDs and artist2 in loIDs:
                # convert SUBIDs to MSDIDs
                artist1m = SUBIDtoMSDID(artist1, artistRead3) 
                artist2m = SUBIDtoMSDID(artist2, artistRead3)
                artist1t = []
                artist2t = []
                # query DB for terms
                q1 = 'SELECT term FROM artist_term WHERE artist_term.artist_id = "{0}\" UNION SELECT mbtag FROM artist_mbtag WHERE artist_mbtag.artist_id = "{0}\"'.format(artist1m)
                resTerms1 = connTerms.execute(q1)
                artistTerms1 = resTerms1.fetchall()
                #print('artist 1 terms:',artistTerms1)
                q2 = 'SELECT term FROM artist_term WHERE artist_term.artist_id = "{0}\" UNION SELECT mbtag FROM artist_mbtag WHERE artist_mbtag.artist_id = "{0}\"'.format(artist2m)
                resTerms2 = connTerms.execute(q2)
                artistTerms2 = resTerms2.fetchall()
                #print('artist 2 terms:',artistTerms2)
                sim = calculateSimilarity(artistTerms1, artistTerms2)
                #print('similarity: {}'.format(sim))
            else:
                # if not found for both, pass
                pass

            write = {'SubsonicArtistIdA': '{}'.format(artist1),
                     'SubsonicArtistIdB': '{}'.format(artist2),
                     'Similarity': '{}'.format(sim)}
            similarityAdd.writerow(write)
        t8 = time.time()
        print 'all similarity found in:',strtimedelta(t1,t8)
        # we close the connection to the database
        conn.close()
    
if __name__=='__main__': main()