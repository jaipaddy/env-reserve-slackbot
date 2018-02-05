# env-reserve-slackbot
Reserve/release test environments from Slack

Use Slack chat bot to help streamline test environment reservation and deployment. Users can reserve a test environment for deployment (via Jenkins) without worrying about stepping on others with the added ability to release it when their work is done. The environment is also released after a configurable number of hours. This is a Python app that uses the Slack real time messaging (RTM) API and packaged as a Docker container.

# How to run
1. Create a bot using the Slack Web UI using your team account under Configure Apps - Custom Integrations
2. Add new Bot configuration and save the API token
3. Copy QASlackBot.env.sample to QASlackBot.env and replace the TOKEN value with the saved token from 2.
4. Generate a token for Jenkins to enable remote trigger of jobs and replace the JENKINS_TOKEN value
5. Adjust the TIMEOUT in seconds
6. Invite the bot user created above to any #channel
7. Build the docker image - `docker build . -t qaslackbot:qa`
8. Use Docker swarm or compose to run the container - `docker-compose up`
9. After test env reservation, the bot can launch a Jenkins build job based on the parameters passed and will post the url to the channel for quick access.

# Sample output


![ScreenShot](https://raw.github.com/jaipaddy/env-reserve-slackbot/master/SlackBotScreenshot.png)

# Applications
The methodology used in this app can be extended to spinning-up new test environments in the cloud and deploying specific versions

# Resource
https://github.com/jeffk/PyBot
