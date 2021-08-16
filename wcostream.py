#!/usr/bin/env python3

"""
wcostream.py
Downloads playlists from wcostream.com
Written by Quinn Neufeld
Feb. 20th 2021
Mar. 17th 2021 - Now attempts to start xvfb
"""

import sys
import os
import multiprocessing as mp

import dryscrape
import bs4
import requests

class VideoDetails:
    """Class to store details about a video"""
    def __init__(self, page_url: str, s_path: str):
        self.page_url = page_url
        self.s_path = s_path

def print_help():
    """Prints help message"""
    print("Usage: wcostream.py <dir> <playlist url>")
    print("Example: wcostream.py AnimeName https://wcostream.com/playlist-cat/<id>")

def rip_video(details: VideoDetails, lock: mp.Lock):
    """Rips a video from a page"""
    #Pull the location of the video file from the webpage
    lock.acquire()
    print("Downloading video from " + details.page_url)
    sess = dryscrape.Session()
    sess.visit(details.page_url)
    try:
        vidsrc = sess.at_xpath('//video')["src"]
        sess.reset()
    except:
        print("Could not find video url in page " + details.page_url)
        return

    lock.release()

    #Download .mp4
    print("Downloading video " + details.s_path + " from " + vidsrc)
    resp = requests.get(vidsrc)
    if not resp.ok:
        print("Could not download video " + details.s_path + " at url " + url)
        return
    print("Downloaded video " + details.s_path)

    #Save .mp4 to file
    with open(details.s_path, "wb") as fi:
        fi.write(resp.content)
    print("Saved video to " + details.s_path)
    del resp

def rip_playlist(url: str, s_dir: str):
    """Rips a playlist"""
    #Pull video details from webpage
    sess = dryscrape.Session()
    sess.visit(url)
    soup = bs4.BeautifulSoup(sess.body(), features="lxml")
    sess.reset()

    vids = []
    for a in soup.find_all("a"):
        if not a.has_attr("class"):
            continue
        if "sonra" in a["class"]:
            vids.append(VideoDetails(a["href"], os.path.join(s_dir, a.text + ".mp4")))
    
    if len(vids) == 0:
        print("Got no videos. Is that a real link or has the site's structure changed?")
        exit(3)
    
    #Spawn threads
    processes = []
    lock = mp.Lock()
    for vid in vids:
        processes.append(mp.Process(target=rip_video, args=(vid, lock)))
        processes[-1].start()
    print("Spawned dl threads.")

    for p in processes:
        p.join()
    print("Joined dl threads.")

#Check args
if len(sys.argv) < 3 or "-h" in sys.argv or "--help" in sys.argv:
    print_help()
    exit(1)

#Make sure the save dir exists
s_dir = sys.argv[1]
if not os.path.exists(s_dir):
    os.mkdir(s_dir)

if not os.path.isdir(s_dir):
    print(s_dir + " is not a directory.")
    exit(2)

if "linux" in sys.platform:
    #Start xvfb in case no X is running.
    try:
        dryscrape.start_xvfb()
    except:
        print("Could not start xvfb server.")
        exit(3)

url = sys.argv[2]
rip_playlist(url, s_dir)
