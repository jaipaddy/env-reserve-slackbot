#!/usr/bin/env python

import argparse, ConfigParser, sys, json, os, pprint
from datetime import datetime
from slackclient import SlackClient
from time import sleep
from _ast import If

__app_name__ = 'QA environment reservation Slack Bot'
__author__ = 'Jaishankar Padmanabhan'
__credits__ = ["Jaishankar Padmanabhan"]
__maintainer__ = 'Jaishankar Padmanabhan'
__email__ = 'jai.padmanabhan@gmail.com'
TIMEOUT = 30

class Converser:
  topics = {}
  client = None
  debug = False
  my_user_name = ''
  userdict = {}
  reservedict = {}
  overridedict={}
  channel = None

  def userlist(self):
    api_call = self.client.api_call("users.list")
    if api_call.get('ok'):
      # retrieve all users
      users = api_call.get('members')
      for user in users:
         self.userdict[user['id']] = user['name']   
         # pprint.pprint(self.userdict)


  def connect(self, token):
    self.client = SlackClient(token)
    self.client.rtm_connect()
    self.my_user_name = self.client.server.username
    print(self.my_user_name)
    print("Connected to Slack.")

  def listen(self):
    while True:
      try:
        input = self.client.rtm_read()
        if input:
          for action in input:
            if self.debug:
              print(action)
            if 'type' in action and action['type'] == "message":
              # Uncomment to only respond to messages addressed to us.
              # if 'text' in action
              #   and action['text'].lower().startswith(self.my_user_name):
              self.process_message(action)
        else:
          sleep(1)
          
        for key in self.topics.keys():
            if key in self.reservedict:
                elapsed = datetime.now() - self.reservedict[key][1]
                if elapsed.total_seconds() > TIMEOUT:
                    msg = "@{0} 8 hrs up! Released stack `{1}`".format(self.reservedict[key][0], key)
                    print msg
                    del self.reservedict[key]
                    self.post(self.channel, msg)
                            
      except Exception as e:
        print("Exception: ", e.message)

  def process_message(self, message):
    self.channel = message['channel']
    if message['text'].lower().find(" help") == 12:
        self.post(message['channel'], "```Welcome to the QA environment reservation system! \nPlease type one of the following <stack> to reserve it.\n \
qa1\n qa2\n qa3\n qa4\n stage2\n sandbox1\nWhen you are done, type release <stack> OR <stack> release\nTo check current \
reservations, type @qabot status\nNOTE - There is a usage limit of 8 hours```")
    elif message['text'].lower().find(" status") == 12:
        if not self.reservedict.keys():
          self.post(message['channel'], "All stacks available!") 
        for key in self.reservedict.keys():
            response = self.topics[key].format(self.reservedict[key][0], key)
            self.post(message['channel'], response)
            print(response)
        
    for key in self.topics.keys():
      if message['text'].lower().startswith(key) and message['text'].lower().endswith(key) or message['text'].lower().startswith("using " + key) or message['text'].lower().startswith("on " + key):
        id = message['user']
        # Hold state of who is using the stack
        if  key not in self.reservedict :
            print "not there"
            self.reservedict[key] = [self.userdict[id],  datetime.now()]
            response = self.topics[key].format(self.userdict[id], key)
            print("Posting to {0}: {1}".format(message['channel'], response))
            self.post(message['channel'], response)
        else:
            print "Stack already taken"
            self.overridedict[key] = self.userdict[id]
            response = self.topics[key].format(self.reservedict[key][0], key) + " . Are you sure you want to reserve it instead? Type `y` or `n`"
            print("Posting to {0}: {1}".format(message['channel'], response))
            self.post(message['channel'], response)
      elif key in self.reservedict and (message['text'].lower().startswith("release " + key) or message['text'].lower().startswith(key+" release")):
          print "release by user"
          response = self.reservedict[key][0] + " has released stack " + key
          del self.reservedict[key]
          self.post(message['channel'], response)
                
          #respond to user's secondary msg
    if message['text'].lower() == 'y' or message['text'].lower() == 'yes':
        id = message['user']
        for key in self.overridedict.keys():
            if self.overridedict[key] == self.userdict[id]:
                print 'take over'
                response = self.topics[key].format(self.overridedict[key], key)
                self.reservedict[key] = [self.overridedict[key],  datetime.now()]
                print("Posting to {0}: {1}".format(message['channel'], response))
                self.post(message['channel'], response)
        
        self.overridedict ={}
         
            
  def post(self, channel, message):
    chan = self.client.server.channels.find(channel)
    if not chan:
      raise Exception("Channel %s not found." % channel)

    return chan.send_message(message)

# Main

if __name__ == "__main__":

  parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='''
This script posts responses to trigger phrases.
Run with:
converse.py topics.json
''',
    epilog='''''')
  parser.add_argument('-d', action='store_true', help="Print debug output.")
  parser.add_argument('topics_file', type=str, nargs=1,
                   help='JSON of phrases/responses to read.')
  args = parser.parse_args()

  # Create a new Converser
  conv = Converser()

  if args.d:
    conv.debug = True

  # Read our token and connect with it
  config = ConfigParser.RawConfigParser()
  config.read('creds.cfg')
  token = config.get("Slack", "token")

  conv.connect(token)
  conv.userlist()

  # Add our topics to the converser
  with open(args.topics_file[0]) as data_file:
    conv.topics = json.load(data_file)

  # Run our conversation loop.
  conv.listen()
