#!/usr/bin/env python

from sys import argv
import os
import json
import re
import multiprocessing as mp

import requests

def retry_request(url: str, times=0):
    """
    Tries to send a GET request to a URL until a response with a status code of 200 is returned or a given number of times.
    If times is 0, retries until successful.
    If not successful returns None.
    """
    while True:
        try:
            resp = requests.get(url)
        except:
            times -= 1
            continue
        if resp.ok:
            return resp
        times -= 1
        if times == 0:
            print("Ran out of attempts when trying to retrieve URL '" + url + "'. Got status code: " + str(resp.status_code))
            return None

def download_chapter(chapter_id: int, title: str):
    """
    Downloads a single chapter
    """
    #resp = requests.get("https://api.mangadex.org/v2/chapter/" + str(chapter_id))
    resp = retry_request("https://api.mangadex.org/v2/chapter/" + str(chapter_id), times=10)
    if resp == None:
        print("Failed to get API information on chapter " + str(chapter_id))
        return
    
    chapter = json.loads(resp.text)["data"]

    chapter_path = os.path.join(title, chapter["chapter"])
    if os.path.exists(chapter_path) and not os.path.isdir(chapter_path):
        print(chapter_path + " is already occupied.")
    elif not os.path.exists(chapter_path):
        os.mkdir(chapter_path)
    
    fallback_server = False

    for page in chapter["pages"]:
        if not fallback_server:
            link = chapter["server"] + chapter["hash"] + "/" + page
            #resp = requests.get(link)
            resp = retry_request(link, times=10)
            if resp == None:
                fallback_server = True

        if fallback_server:
            link = chapter["serverFallback"] + chapter["hash"] + "/" + page
            #resp = requests.get(link)
            resp = retry_request(link, times=10)
            if resp == None:
                print("Could not get page from server or fallback server.")
                return

        with open(os.path.join(chapter_path, page), "wb") as fi:
            fi.write(resp.content)
    
    print("Saved chapter " + str(chapter["chapter"]))

def download_chapters(chapter_ids: list, title: str):
    """Downloads chapters from a list"""
    threads = []
    print("Starting threads...")
    for chapter in chapter_ids:
        threads.append(mp.Process(target=download_chapter, args=(chapter, title)))
        threads[-1].start()
    print("Started threads.")
    
    for thread in threads:
        thread.join()

def has_chapter(chapters: list, chapter: dict):
    """
    Returns the index if a chapter is already in a list of chapters.
    Returns -1 if the chapter is not in a list of chapters.
    """
    for i in range(len(chapters)):
        c = chapters[i]
        if c["chapter"] == chapter["chapter"]:
            return i
    return -1

def remove_duplicate_chapters(chapters: list):
    """Removes duplicate chapters from a list. Defaults to most viewed chapter."""
    out_chapters = []
    for chapter in chapters:
        c_idx = has_chapter(out_chapters, chapter)
        if c_idx == -1:
            out_chapters.append(chapter)
        else:
            if chapter["views"] > out_chapters[c_idx]["views"]:
                out_chapters[c_idx] = chapter
    return out_chapters

def get_chapters_from_manga(m_id: int, langs: list):
    """
    Returns chapter ids from a manga
    """
    #resp = requests.get("https://api.mangadex.org/v2/manga/" + str(m_id) + "/chapters")
    resp = retry_request("https://api.mangadex.org/v2/manga/" + str(m_id) + "/chapters", times=10)
    if resp == None:
        print("Got non-ok response from request for chapters of manga " + str(m_id))
        exit()
    
    chapters = json.loads(resp.text)["data"]["chapters"]
    i = 0
    while i < len(chapters):
        if not chapters[i]["language"] in langs:
            del chapters[i]
            continue
        i += 1
    
    chapters = remove_duplicate_chapters(chapters)
    return chapters

def get_manga_title(m_id: int):
    """
    Returns title for a manga
    """
    #resp = requests.get("https://api.mangadex.org/v2/manga/" + str(m_id))
    resp = retry_request("https://api.mangadex.org/v2/manga/" + str(m_id), times=10)
    if resp == None:
        print("Got non-ok response from request for manga " + str(m_id))
        return "Unknown Title"
    
    manga = json.loads(resp.text)
    return manga["data"]["title"]


if len(argv) < 2 or "-h" in argv or "--help" in argv:
    print(
        """Usage: mangadex.py <manga id> / -c <chapter ids>
        Downloads all chapters from a manga of a given id.
        or downloads a single chapter specified by -c.
        -l / --lang <language> - specifies language id for manga downloads. Defaults to 'gb' (for english)."""
    )
    exit(1)

#Download chapters
if "-c" in argv:
    chapters = []
    for arg in argv[1:]:
        try:
            chapters.append(int(arg))
        except:
            continue
    
    download_chapters(chapters, "Manual Chapters")
    exit()

languages = []

if "-l" in argv:
    i = argv.index("-l")
    languages.append(argv[i + 1])
    del argv[i + 1]
    del argv[i]
if "--lang" in argv:
    i = argv.index("--lang")
    languages.append(argv[i + 1])
    del argv[i + 1]
    del argv[i]

if len(languages) == 0:
    languages = ["gb"]

for arg in argv[1:]:
    title = get_manga_title(int(arg))
    print("Got manga title: '" + title + "'")

    chapters = get_chapters_from_manga(int(arg), languages)
    chapter_ids = []
    for c in chapters:
        chapter_ids.append(c["id"])
    if os.path.exists(title) and not os.path.isdir(title):
        print("Title is a non-directory")
        exit(2)
    if not os.path.exists(title):
        os.mkdir(title)
    download_chapters(chapter_ids, title)
