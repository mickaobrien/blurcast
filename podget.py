import requests
import os.path
import urllib2
import cPickle as pickle
import getpass
from pyquery import PyQuery as pq

BASE_URL = "https://www.newsblur.com"

USERNAME = "mickob"

FOLDER = "Listen Subscriptions"

PODCAST_DIR = "/home/michael/Music/podcasts"


def login():
    password = getpass.getpass("Enter password:")
    auth = {'username': USERNAME, 'password': password}
    r = requests.post("%s/api/login" % BASE_URL, data=auth)
    if r.json()['authenticated']:
        print "logged in!"
        cookies = r.cookies.get_dict()

        with open("cookies", "wb") as f:
            pickle.dump(cookies, f)
            f.close()
        return cookies
    else:
        print "no log in..."
        return 0


#def get_cookies(USERNAME, password):
    #auth = {'username': USERNAME, 'password': password}
    #r = requests.post("%s/api/login" % BASE_URL, data=auth)
    #if r.json()['authenticated']:
        #print "logged in!"
        #cookies = r.cookies.get_dict()

        #with open("cookies", "wb") as f:
            #pickle.dump(cookies, f)
            #f.close()
        #return cookies
    #else:
        #print "no log in..."
        #return 0

def valid_session(cookies):
    feeds = requests.get("%s/reader/feeds" % BASE_URL, cookies=cookies)
    if not feeds.json()['authenticated']:
        return False
    return True

def get_pod_ids(cookies):
    feeds = requests.get("%s/reader/feeds" % BASE_URL, cookies=cookies)

    # get dict where keys=folders, entries=feed_ids
    list_of_folders = [fldr for fldr in feeds.json()['folders']
                       if type(fldr) is dict]
    folders = {}
    for d in list_of_folders:
        folders.update(d)

    pod_ids = folders[FOLDER]
    return pod_ids


def get_links(pod_ids, cookies):
    links = []
    params = {'read_filter': 'unread'}
    for pid in pod_ids:
        f = requests.get("%s/reader/feed/%d" % (BASE_URL, pid),
                         params=params, cookies=cookies)

        if not f.json()['authenticated']:
            print "need to log in..."

        stories = f.json()['stories']

        for story in stories:
            dl_link = pq(story['story_content'])('source').attr.src
            story_id = story['id']
            links.append((pid, story_id, dl_link))

    return links


def download_link(link):
    #file_name = "%s/%s" % (PODCAST_DIR, link.split('/')[-1])
    file_name = link.split('/')[-1]
    u = urllib2.urlopen(link)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. /
                                       file_size)
        status = status + chr(8)*(len(status)+1)
        print status,

    f.close()


def pdcast():
    if os.path.isfile("cookies"):
        with open("cookies", "rb") as f:
            cookies = pickle.load(f)
            f.close()
        if not valid_session(cookies):
            print "Session expired! Need to log in again..."
            cookies = login()
    else:
        cookies = login()

    pod_ids = get_pod_ids(cookies)
    print "got ids!"
    links = get_links(pod_ids, cookies)
    print "got links!"

    if len(links):
        for (feed_id, pod_id, link) in links:
            if link is not None:
                download_link(link)
            else:
                print "Nothing to download at %s" % pod_id

            r = requests.post("%s/reader/mark_story_as_read" % BASE_URL,
                              params={'feed_id': feed_id, 'story_id': pod_id},
                              cookies=cookies)
            print "Marked read!      ?"
            print r.status_code
            print "---"
    else:
        print "Nothing to get...!"


if __name__ == "__main__":
    pdcast()
