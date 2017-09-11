#!/usr/bin/env python

import argparse, json, os, logging
from datetime import datetime
from slackclient import SlackClient
from time import sleep

__app_name__ = 'QA environment reservation Slack Bot'
__author__ = 'Jaishankar Padmanabhan'
__credits__ = ["Jaishankar Padmanabhan"]
__maintainer__ = 'Jaishankar Padmanabhan'
__email__ = 'jai.padmanabhan@gmail.com'

TIMEOUT = int(os.environ.get("TIMEOUT", "7200"))
TOKEN = os.environ.get("TOKEN", None)
DATA_FILE= os.environ.get("DATA_FILE", None)
logging.basicConfig(format='localhost - - [%(asctime)s] %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)
  
class QASlackBot:
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
    log.debug(self.userdict)    


  def connect(self, token):
    self.client = SlackClient(token)
    self.client.rtm_connect()
    self.my_user_name = self.client.server.username
    log.info("Connected to Slack as "+ self.my_user_name)

  def listen(self):
    while True:
      try:
        input = self.client.rtm_read()
        if input:
          for action in input:
            log.debug(action)
            if 'type' in action and action['type'] == "message":
              self.process_message(action)
        else:
          sleep(1)
          
          # Check for time reserved and release when time is up
        for key in self.topics.keys():
            if key in self.reservedict:
                elapsed = datetime.now() - self.reservedict[key][1]
                if elapsed.total_seconds() > TIMEOUT:
                    msg = "@{0} 8 hrs up! Released stack `{1}`".format(self.reservedict[key][0], key)
                    log.debug(msg)
                    del self.reservedict[key]
                    self.post(self.channel, msg)
                            
      except Exception as e:
        log.fatal("Exception: ", e.message)

  def process_message(self, message):
    self.channel = message['channel']
    if message['text'].lower().find(" help") == 12:
        welcome = "```Welcome to the QA environment reservation system! \nPlease type one of the following <stack> to reserve it.\n \
qa1\n qa2\n qa3\n qa4\n stage2\n sandbox1\nWhen you are done, type release <stack> OR <stack> release\nTo check current \
reservations, type @qabot status\nNOTE - There is a usage limit of 8 hours```"
        self.post(message['channel'], welcome)
        log.debug("Posting to {0}: {1}".format(message['channel'], welcome))
    elif message['text'].lower().find(" status") == 12:
        if not self.reservedict.keys():
          self.post(message['channel'], "All stacks available!") 
          log.debug("Posting to {0}: {1}".format(message['channel'], "All stacks available!"))
        for key in self.reservedict.keys():
            response = self.topics[key].format(self.reservedict[key][0], key)
            self.post(message['channel'], response)
            log.info("Posting to {0}: {1}".format(message['channel'], response))
             
    for key in self.topics.keys():
      if message['text'].lower().startswith(key) and message['text'].lower().endswith(key) or message['text'].lower().startswith("using " + key) or message['text'].lower().startswith("on " + key):
        id = message['user']
        # Hold state of who is using the stack
        if  key not in self.reservedict :
            log.info("Not present")
            self.reservedict[key] = [self.userdict[id],  datetime.now()]
            response = self.topics[key].format(self.userdict[id], key)
            log.info("Posting to {0}: {1}".format(message['channel'], response))
            self.post(message['channel'], response)
        else:
            log.info("Stack already taken")
            self.overridedict[key] = self.userdict[id]
            response = self.topics[key].format(self.reservedict[key][0], key) + " . Are you sure you want to reserve it instead? Type `y` or `n`"
            log.info("Posting to {0}: {1}".format(message['channel'], response))
            self.post(message['channel'], response)
      elif key in self.reservedict and (message['text'].lower().startswith("release " + key) or message['text'].lower().startswith(key+" release")):
          log.info("Release by user")
          response = self.reservedict[key][0] + " has released stack " + key
          del self.reservedict[key]
          self.post(message['channel'], response)
                
       
    if message['text'].lower() == 'y' or message['text'].lower() == 'yes':
        id = message['user']
        for key in self.overridedict.keys():
            if self.overridedict[key] == self.userdict[id]:
                log.info("Take over")
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

# Main gateway
if __name__ == "__main__":

  if TOKEN is None:
        log.error("Slack Token is not set. Exiting.")
        exit()
  elif DATA_FILE is None:
        log.error("DATA_FILE is not set. Exiting.")
        exit()
        
  bot = QASlackBot()
  bot.connect(TOKEN)
  bot.userlist() # Build user id to name dictionary

  # Add our topics to the bot
  with open(DATA_FILE) as data_file:
    bot.topics = json.load(data_file)

  # While loop to listen for messages on Slack
  bot.listen()
