import json
import flask
import httplib2
import base64
import email
import time
import time, threading
import atexit
import threading
import os
from slackclient import SlackClient
import logging
logging.basicConfig()
from apscheduler.scheduler import Scheduler
from flask import Flask

from flask.json import jsonify
from apiclient import discovery, errors
from oauth2client import client
from flask_cors import CORS, cross_origin

app = flask.Flask(__name__)
CORS(app)

cron = Scheduler(daemon=True)
# Explicitly kick off the background thread
cron.start()

SLACK_TOKEN = 'xoxp-67056869062-67233104082-74326384304-3afc19ca4d'

slack_client = SlackClient(SLACK_TOKEN)


@app.route('/')
def index():
    if 'credentials' not in flask.session:
        return flask.redirect(flask.url_for('oauth2callback'))
    credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
    if credentials.access_token_expired:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        http_auth = credentials.authorize(httplib2.Http())
        global gmail_service
        gmail_service = discovery.build('gmail', 'v1', http_auth)
        ListThreadsMatchingQuery(gmail_service,'me')
        a= int(time.time()) - 120
        b=str(a)
        threads = gmail_service.users().threads().list(userId='me',q= 'after:' + b).execute() 
        text=json.dumps(threads)  
        snippet=json.loads(text)
        if text == '{"resultSizeEstimate": 0}':
                print('')
        else:  
            m=snippet['threads']
            t=m[0]  
            channels = list_channels()
            if channels:
                print("Channels: ")
                for channel in channels:
                    print(channel['name'] + " (" + channel['id'] + ")")
                    if channel['name'] == 'general':
                        send_message(channel['id'], t['snippet'])
        return json.dumps(threads)
       
 
#@cron.interval_schedule(minutes=1)
def ListThreadsMatchingQuery(service, user_id):   
    a= int(time.time()) - 120
    b=str(a)
    threads = service.users().threads().list(userId='me',q= 'after:' + b).execute()
    text=json.dumps(threads)  
    snippet=json.loads(text)
    if text == '{"resultSizeEstimate": 0}':
                print('')
    else:  
        m=snippet['threads']
        t=m[0]  
        channels = list_channels()
        if channels:
            print("Channels: ")
            for channel in channels:
                print(channel['name'] + " (" + channel['id'] + ")")
                if channel['name'] == 'general':
                    send_message(channel['id'], '*' + t['snippet'] + '*')
    threading.Timer(120, ListThreadsMatchingQuery,args=[gmail_service,'me']).start()


def list_channels():
    channels_call = slack_client.api_call("channels.list")
    if channels_call.get('ok'):
        return channels_call['channels']
    return None


def send_message(channel_id, message):
    slack_client.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=message,
        username='Gmail_NotifyBOT',
        icon_emoji=':robot_face:'
    )

@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        'client_secrets.json',
        scope='https://mail.google.com/',
        redirect_uri=flask.url_for('oauth2callback', _external=True)
    )
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        flask.session['credentials'] = credentials.to_json()
        return flask.redirect(flask.url_for('index'))
atexit.register(lambda: cron.shutdown(wait=False))

if __name__ == '__main__':
    import uuid
    app.secret_key = str(uuid.uuid4())
    app.debug = True
    app.run()


