import requests
import os.path
import urllib2
import cPickle as pickle
import getpass
from pyquery import PyQuery as pq

#TODO learn how to program...
#TODO Add classes for session and link

#folder names, username etc.
#TODO add better config file e.g. ConfigParser
from settings import *

BASE_URL = "https://www.newsblur.com"

class blurcast:

    def __init__(self):
        if not os.path.isfile("settings.py"):
            self.create_settings()
        
        self.set_cookies()
        #self.get_new_podcasts()

    def get_new_podcasts(self):
        if not hasattr(self, 'pod_ids'):
            self.set_pod_ids()

        self.set_links()
        self.download_all_unread()

    def create_settings(self):
        """ Create a settings.py file based on user input.
        """
        username = raw_input("Username: ")
        folder = raw_input("NewsBlur folder containing podcasts: ")
        save_dir = raw_input("Directory to save podcasts: ")
        with open("settings.py", "w+") as f:
            f.write('USERNAME = "%s"\n' % username)
            f.write('FOLDER = "%s"\n' % folder)
            f.write('PODCAST_DIR = "%s"' % save_dir)
            f.close()
        return

    def login(self,password):
        """ Login to NewsBlur account with username from settings.py
            and password typed in.
        """
        #TODO Fix this mess here.
        auth = {'username': USERNAME, 'password': password}
        r = requests.post("%s/api/login" % BASE_URL, data=auth)
        print r.json()
        if not r.json()['authenticated']:
            print "There was an error logging in, try reentering your password."
            while not r.json()['authenticated']:
                password = getpass.getpass("Password: ")
                auth = {'username': USERNAME, 'password': password}
                r = requests.post("%s/api/login" % BASE_URL, data=auth)

        print "logged in!"
        cookies = r.cookies.get_dict()
        return cookies
        #else:
            #print "no log in..."
            #return 0

    def get_session_id(self):
        """ Get session_id cookie used to validate.
        """
        password = getpass.getpass("Enter your password: ")
        cookies = self.login(password)
        return cookies

    def save_cookies(self):
        """ Save session_id cookie for later use.
        """
        with open("cookies.cfg", "wb") as f:
            pickle.dump(self.cookies, f)
            f.close()

    def cookies_exist(self):
        """ Check if cookies file exists.
        """
        if os.path.isfile("cookies.cfg"):
            return True
        return False

    def valid_session(self):
        """ Check if session_id in current cookie is valid.
        """
        feeds = requests.get("%s/reader/feeds" % BASE_URL, cookies=self.cookies)
        if not feeds.json()['authenticated']:
            return False
        return True

    def set_cookies(self):
        """ Set valid cookies either from cookies.cfg or by requesting
            a new one.
        """
        if self.cookies_exist():
            with open("cookies.cfg", "rb") as f:
                cookies = pickle.load(f)
                f.close()
                self.cookies = cookies
            if self.valid_session():
                return
        
        cookies = self.get_session_id()
        self.cookies = cookies
        self.save_cookies()



    def set_pod_ids(self):
        feeds = requests.get("%s/reader/feeds" % BASE_URL,
                             cookies=self.cookies)

        # get dict where keys=folders, entries=feed_ids
        list_of_folders = [fldr for fldr in feeds.json()['folders']
                           if type(fldr) is dict]
        folders = {}
        for d in list_of_folders:
            folders.update(d)

        pod_ids = folders[FOLDER]
        self.pod_ids = pod_ids


    def set_links(self):
        """ Sets links to be a list of tuples of feed_id, story_id and
            podcast link for each unread podcast item.
        """
        links = []
        params = {'read_filter': 'unread'}
        for pid in self.pod_ids:
            f = requests.get("%s/reader/feed/%d" % (BASE_URL, pid),
                             params=params, 
                             cookies=self.cookies)

            if not f.json()['authenticated']:
                print "need to log in..."

            stories = f.json()['stories']

            for story in stories:
                dl_link = pq(story['story_content'])('source').attr.src
                story_id = story['id']
                links.append((pid, story_id, dl_link))

        self.links = links
        #return links


    def download_link(self,link):
        file_name = "%s/%s" % (PODCAST_DIR, link.split('/')[-1])
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
            status = r"[%3.2f%%]" % (file_size_dl * 100./file_size)
            status = status + chr(8)*(len(status)+1)
            print status,

        f.close()

    def mark_story_read(self, feed_id, story_id):
        r = requests.post("%s/reader/mark_story_as_read" % BASE_URL,
                          params={'feed_id': feed_id, 'story_id': story_id},
                          cookies=self.cookies)
        print "%s marked read...\n\n" % story_id


    def download_all_unread(self):
        if len(self.links)>0:
            for data in self.links:
                feed_id = data[0]
                story_id = data[1]
                link = data[2]
                self.download_link(link)
                self.mark_story_read(feed_id, story_id)
            self.links = []

        else:
            print "Nothing new to download."

if __name__ == "__main__":
    podcatcher = blurcast()
    podcatcher.get_new_podcasts()
