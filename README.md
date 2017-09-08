# env-reserve-slackbot
Reserve/release test environments from Slack

Use Slack chat bot to help streamline test environment reservation. Users can reserve a test environment without worrying about stepping on others with the added ability to release it when their work is done. The environment is also released after a configurable number of hours. This is a Python app that uses the Slack real time messaging (RTM) API and packaged as a Docker container.

# How to run
1. Create a bot using the Slack Web UI using your team account under Configure Apps - Custom Integrations
2. Add new Bot configuration and save the API token 
3. Copy QASlackBot.env.sample to QASlackBot.env and replace the TOKEN value with the saved token from 2.
4. Adjust the TIMEOUT in seconds
5. Invite the bot user created above to any #channel 
6. Build the docker image - `docker build . -t qaslackbot:qa`
7. Use Docker swarm or compose to run the container - `docker-compose up`

# Sample output


![ScreenShot](https://raw.github.com/jaipaddy/env-reserve-slackbot/master/SlackBotScreenshot.png)

# Applications
The methodology used in this app can be extended to starting and shutting down test environments via another script/API or any task that requires exclusive access

# Credit
https://github.com/jeffk/PyBot
