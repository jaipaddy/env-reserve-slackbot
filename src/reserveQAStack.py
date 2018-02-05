#!/usr/bin/env python

import json, os, logging, requests
from datetime import datetime
from slackclient import SlackClient
from time import sleep
from syslog import LOG_DEBUG

__app_name__ = 'QA environment reservation Slack Bot'
__author__ = 'Jaishankar Padmanabhan'
__credits__ = ["Jaishankar Padmanabhan"]
__maintainer__ = 'Jaishankar Padmanabhan'
__email__ = 'jai.padmanabhan@gmail.com'

TIMEOUT = int(os.environ.get("TIMEOUT", "7200"))
TOKEN = os.environ.get("TOKEN", None)
DATA_FILE= os.environ.get("DATA_FILE", None)
#Jenkins env variables
JENKINS=os.environ.get("JENKINS", "jenkins url")
JENKINS_URL= JENKINS+ "/buildByToken/buildWithParameters?job={0}&token={1}&Stack={2}"
JENKINS_TOKEN=os.environ.get("JENKINS_TOKEN", None)
JENKINS_RUBY_JOB=os.environ.get("JENKINS_RUBY_JOB", None)
JENKINS_JAVA_JOB=os.environ.get("JENKINS_JAVA_JOB", None)
JENKINS_FULL_JOB=os.environ.get("JENKINS_FULL_JOB", None)
JENKINS_DEPLOY_WHAT_U_WANT=os.environ.get("JENKINS_DEPLOY_WHAT_U_WANT", None)
JENKINS_RUN_DATAGEN_JOB=os.environ.get("JENKINS_RUN_DATAGEN_JOB", None)
JENKINS_RUN_BVT_JOB=os.environ.get("JENKINS_RUN_BVT_JOB", None)
JENKINS_RUN_PROD_SMOKE=os.environ.get("JENKINS_RUN_PROD_SMOKE", None)
JENKINS_RUBY_JOB_LINK=os.environ.get("JENKINS_RUBY_JOB_LINK", "jenkins url")
JENKINS_JAVA_JOB_LINK=os.environ.get("JENKINS_JAVA_JOB_LINK", "jenkins url")
JENKINS_FULL_JOB_LINK=os.environ.get("JENKINS_FULL_JOB_LINK", "jenkins url")
JENKINS_DEPLOY_WHAT_U_WANT_LINK=os.environ.get("JENKINS_DEPLOY_WHAT_U_WANT_LINK", "jenkins url")
JENKINS_RUN_DATAGEN_LINK=os.environ.get("JENKINS_RUN_DATAGEN_LINK", "jenkins url")
JENKINS_RUN_BVT_LINK=os.environ.get("JENKINS_RUN_BVT_LINK", "jenkins url")
JENKINS_RUN_PROD_SMOKE_LINK=os.environ.get("JENKINS_RUN_PROD_SMOKE_LINK", "jenkins url")
BUILDPARAMS_FILE=os.environ.get("BUILDPARAMS_FILE", None)

#Debug logging
LOG_DEBUG=os.environ.get("LOG_DEBUG", "true")
if LOG_DEBUG == "false":
    logging.basicConfig(format='[%(filename)s:%(lineno)s] %(message)s', level=logging.INFO)
else:
    logging.basicConfig(format='[%(filename)s:%(lineno)s] %(message)s', level=logging.DEBUG)    
    
log = logging.getLogger(__name__)
topics = {}

class QASlackBot:
  buildparams = {}
  client = None
  my_user_name = ''
  userdict = {}
  reservedict = {}
  overridedict={}
  channel = None
  message = None
  buildparamsList = []
  

  def userlist(self):
    api_call = self.client.api_call("users.list")
    if api_call.get('ok'):
      # retrieve all users
      users = api_call.get('members')
      for user in users:
         self.userdict[user['id']] = user['name']
    #log.debug(self.userdict)    

  def connect(self, token):
    self.client = SlackClient(token)
    self.client.rtm_connect()
    self.my_user_name = self.client.server.username
    log.debug("Connected to Slack as "+ self.my_user_name)

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
        for key in topics.keys():
            if key in self.reservedict:
                elapsed = datetime.now() - self.reservedict[key][1]
                if elapsed.total_seconds() > TIMEOUT:
                    msg = "@{0} 8 hrs up! Released stack `{1}`".format(self.reservedict[key][0], key)
                    log.debug( msg)
                    self.post(self.reservedict[key][2], msg)
                    del self.reservedict[key]
                            
      except Exception as e:
        pass
        #log.error("Exception: ", e.message)


  def process_message(self, message):
    self.channel = message['channel']  
    self.message = message['text']
    
    if self.message.lower().find(" help") == 12:
        self.help()
    elif self.message.lower().find(" status") == 12:
        self.status()
        
    for key in topics.keys():
      if self.message.lower().startswith("using " + key) or self.message.lower().startswith("on " + key) or self.message.lower().startswith("reserve " + key) or self.message.lower().startswith(key+" reserve"):
        id = message['user']
        # Hold state of who is using the stack
        if  key not in self.reservedict :
            response = self.newreservation(key, id)
        else:
            response = self.existingReservation(key, id)
      elif key in self.reservedict and (self.message.lower().startswith("release " + key) or self.message.lower().startswith(key+" release")):
          response = self.releaseStack(key)
          
          # ************* Jenkins Deploy ******************
          # deploy full  
      elif  self.message.lower().startswith(key) and " deploy" in self.message.lower() and self.message.lower().endswith(" full") :
          self.fulldeploy(message, key)  
          # deploy full | ApiVersion=master,WebVersion=SAV-3000
      elif self.message.lower().startswith(key) and (self.message.lower().find(" deploy") <  self.message.lower().find(" full")) and not self.message.lower().endswith("full") and "|" in self.message:
           self.fulldeployParams(message, key)  
           # deploy java
      elif self.message.lower().startswith(key) and " deploy" in self.message.lower() and self.message.lower().endswith(" java") :
          self.deployjava(message, key)  
          # deploy java | Manifest=20170909
      elif self.message.lower().startswith(key) and (self.message.lower().find(" deploy") <  self.message.lower().find(" java")) and not self.message.lower().endswith("java") and "|" in self.message and "Manifest" in self.message:
           self.deployjavaParams(message, key)  
           #deploy ruby 
      elif self.message.lower().startswith(key) and " deploy" in self.message.lower() and self.message.lower().endswith(" ruby") :
          self.deployruby(message, key)  
          # deploy ruby | ApiVersion=SAV-3000,WebVersion=master
      elif self.message.lower().startswith(key) and (self.message.lower().find(" deploy") <  self.message.lower().find(" ruby")) and not self.message.lower().endswith("java") and "|" in self.message and "Manifest" not in self.message:
           self.deployrubyParams(message, key)  
             # deploy what you want
      elif self.message.lower().startswith(key) and (self.message.lower().find(" deploy") <  self.message.lower().find(" only")) and not self.message.lower().endswith("only") and "|" in self.message and ";" not in self.message:
          self.deploywhatyouwant(message, key)
           
           # run datagen only
      elif self.message.lower().startswith(key) and (self.message.lower().find(" run") <  self.message.lower().find(" datagen")) and self.message.lower().endswith("datagen") :
          self.rundatagen(message, key)     
           # run BVT
      elif self.message.lower().startswith(key) and (self.message.lower().find(" run") <  self.message.lower().find(" bvt")) and  self.message.lower().endswith("bvt"):
          self.runbvt(message, key)       
         # run Prod smoke
      elif self.message.lower().startswith(key) and (self.message.lower().find(" run") <  self.message.lower().find(" smoke")) and  self.message.lower().endswith("smoke"):
          self.runprodsmoke(message, key)   
          
          #respond to user's secondary msg
    if self.message.lower() == 'y' :
        self.overrideReservation(message, key)
         
            
  def post(self, channel, message):
    chan = self.client.server.channels.find(channel)
    if not chan:
      raise Exception("Channel %s not found." % channel)

    return chan.send_message(message)

  def launchJenkins(self, url):
      log.debug(url)
      r = requests.get(url)
      if r.status_code != 201:
         self.post(self.channel, "`Could not launch Jenkins job !`s")
      else:
         log.info("Launched Jenkins job "+url)  
    
  def parseBuild(self, url):
       flag=True
       for k in self.buildparams.keys():
               if k in self.buildparamsList:
                   url = url + "&" + k+ "=" +self.buildparams[k]
               else:
                   flag=False
                   self.post(self.channel, "`Check the parameters passed! Try @qabot help`")
       if flag:         
          self.launchJenkins(url)
          link =""
          if "ruby" in url.lower():
              link = JENKINS_RUBY_JOB_LINK
          elif  "java" in url.lower():
              link = JENKINS_JAVA_JOB_LINK
          elif "full" in url.lower():
              link = JENKINS_FULL_JOB_LINK 
          elif "what_you_want" in url.lower():
              link = JENKINS_DEPLOY_WHAT_U_WANT_LINK       
          elif "datagen" in url.lower():
              link = JENKINS_RUN_DATAGEN_LINK    
          elif "build-verification" in url.lower():
              link = JENKINS_RUN_BVT_LINK   
          elif "prod-smoke" in url.lower():
              link = JENKINS_RUN_PROD_SMOKE_LINK 
                     
          self.post(self.channel, "Jenkins job successfully launched at "+ link)      
          
       self.buildparams = {}   

  def help(self):
      self.post(self.channel, "```Welcome to the QA environment reservation system! \nPlease type 'reserve <stack>' or '<stack> reserve' to reserve one of the following\n \
qa1\n qa2\n qa3\n qa4\n stage2\n sandbox1\n prod\nWhen you are done, type 'release <stack>' OR '<stack> release'\nTo check current \
reservations, type @qabot status\nTo deploy to the reserved stack:\n<stack> deploy full OR\n<stack> deploy full | ApiVersion=SAV-3001-api,WebVersion=SAV-3000-web,\
RabbitConsumersVersion=master,AdminVersion=master,CsrVersion=master,Manifest=20170909\nDeploy Ruby only with <stack> deploy ruby \
OR <stack> deploy ruby | ApiVersion=master,WebVersion=SAV-3000-web\nDeploy Java only with <stack> deploy java OR <stack> deploy java | Manifest=20170909\n\
*Deploy specific versions only with <stack> deploy only | ApiVersion=master,Manifest=20170909\nRun datagen to refresh data with <stack> run datagen\n\
Run BVT with <stack> run bvt\nRun Production smoke with <stack> run smoke\n\nNOTE - There is a usage limit of 8 hours```")

  def status(self):
      if not self.reservedict.keys():
          self.post(self.channel, "All stacks available!")
      for key in self.reservedict.keys():
          response = topics[key].format(self.reservedict[key][0], key)
          self.post(self.channel, response)
          log.info(response)
      
  def newreservation(self, key, id):
      log.info("not there")
      self.reservedict[key] = [self.userdict[id], datetime.now(), self.channel]
      response = topics[key].format(self.userdict[id], key)
      log.info("Posting to {0}: {1}".format(self.channel, response))
      self.post(self.channel, response)

  def existingReservation(self, key, id):
      log.info("Stack already taken")
      self.overridedict[key] = self.userdict[id]
      response = topics[key].format(self.reservedict[key][0], key) + " . Are you sure you want to reserve it instead? Type `y` or `n`"
      log.info("Posting to {0}: {1}".format(self.channel, response))
      self.post(self.channel, response)

  def releaseStack(self, key):
      log.info("release by user")
      response = self.reservedict[key][0] + " has released stack " + key
      self.post(self.reservedict[key][2], response)
      del self.reservedict[key]

  def fulldeploy(self, message, key):
      url = JENKINS_URL.format(JENKINS_FULL_JOB, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")

  def fulldeployParams(self, message, key):
      log.debug("Parsing build params")
      s = self.message.split("|")[1].strip()
      self.buildparams = dict(item.split("=") for item in s.split(","))
      log.debug(self.buildparams)
      url = JENKINS_URL.format(JENKINS_FULL_JOB, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")

  def deployjava(self, message, key):
      url = JENKINS_URL.format(JENKINS_JAVA_JOB, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")

  def deployjavaParams(self, message, key):
      log.debug("Parsing build params")
      s = self.message.split("|")[1].strip()
      self.buildparams = dict(item.split("=") for item in s.split(","))
      log.info(self.buildparams)
      url = JENKINS_URL.format(JENKINS_JAVA_JOB, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")

  def deployruby(self, message, key):
      url = JENKINS_URL.format(JENKINS_RUBY_JOB, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")

  def deployrubyParams(self, message, key):
      log.debug("Parsing build params")
      s = self.message.split("|")[1].strip()
      self.buildparams = dict(item.split("=") for item in s.split(","))
      url = JENKINS_URL.format(JENKINS_RUBY_JOB, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")

  def deploywhatyouwant(self, message, key):
      log.debug("Parsing build params")
      s = self.message.split("|")[1].strip()
      self.buildparams = dict(item.split("=") for item in s.split(","))
      url = JENKINS_URL.format(JENKINS_DEPLOY_WHAT_U_WANT, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")
          
  def overrideReservation(self, message, key):
      id = message['user']
      for key in self.overridedict.keys():
          if self.overridedict[key] == self.userdict[id]:
              log.info("take over")
              response = topics[key].format(self.overridedict[key], key)
              self.reservedict[key] = [self.overridedict[key], datetime.now(), self.channel]
              log.info("Posting to {0}: {1}".format(self.channel, response))
              self.post(self.channel, response)
      
      self.overridedict = {}

  def rundatagen(self, message, key):
      url = JENKINS_URL.format(JENKINS_RUN_DATAGEN_JOB, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")
          
  def runbvt(self, message, key):
      url = JENKINS_URL.format(JENKINS_RUN_BVT_JOB, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")
          
  def runprodsmoke(self, message, key):
      url = JENKINS_URL.format(JENKINS_RUN_PROD_SMOKE, JENKINS_TOKEN, key)
      if self.reservedict and self.userdict[message['user']] in self.reservedict[key]:
          self.parseBuild(url)
      else:
          self.post(self.channel, "`Please reserve the stack before Jenkins deploy`")          
          
              
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
    topics = json.load(data_file)
 
 # Read Jenkins parameters into list
  with open(BUILDPARAMS_FILE) as data_file:
    bot.buildparamsList = data_file.read().splitlines()
    
  # While loop to listen for messages on Slack
  bot.listen()
