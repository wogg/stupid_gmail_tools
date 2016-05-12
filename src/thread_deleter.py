from __future__ import print_function
import httplib2
import os

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse
    argparser = argparse.ArgumentParser(parents=[tools.argparser])
    argparser.add_argument("--label", dest='label')
    argparser.add_argument("--limit", dest='limit', type=int)
    argparser.add_argument("--before", dest='before')
    flags = argparser.parse_args()
except ImportError:
    flags = None

#:SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
SCOPES = 'https://mail.google.com/'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Gmail API Python Quickstart'

class MarksMailMurder():
    def __init__(self):
        """Shows basic usage of the Gmail API.

        Creates a Gmail API service object and outputs a list of label names
        of the user's Gmail account.
        """
        self.credentials = self.get_credentials()
        self.http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('gmail', 'v1', http=self.http)
        self.label_by_name = None
        self.limit = 1000

    @classmethod
    def get_credentials(cls):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'gmail-python-quickstart.json')

        store = oauth2client.file.Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            if flags:
                credentials = tools.run_flow(flow, store, flags)
            else: # Needed only for compatibility with Python 2.6
                credentials = tools.run(flow, store)
            print('Storing credentials to ' + credential_path)
        return credentials

    def messages_for_label(self, label=None):
        query = "before:%s" % self.before
        response = self.service.users().messages().\
                list(userId='me', labelIds=[label['id']], 
                        q=query).execute()
        messages=[]
        if 'messages' in response:
            messages.extend(response['messages'])
            while 'nextPageToken' in response:
                if len(messages) >= self.limit:
                    break
                page_token = response['nextPageToken']
                response = self.service.users().messages().\
                        list(userId='me', labelIds=[label['id']],
                                q=query, pageToken=page_token).execute()
                messages.extend(response['messages'])
        return messages

    def label_for_name(self, name=None):
        if self.label_by_name is None:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            self.label_by_name = {}
            for label in labels:
                self.label_by_name[label['name']] = label
        return self.label_by_name[name]

    def delete_message(self, message):
        response = self.service.users().messages().\
                delete(userId='me', id=message['id']).execute()


def main():
    print("%s" % flags)
    mmm = MarksMailMurder()
    mmm.limit = flags.limit
    mmm.before = flags.before
    messages = mmm.messages_for_label(mmm.label_for_name(flags.label))
    # print("Labels: %s" % labels.__dir__()
    for m in messages:
        mmm.delete_message(m)
        print("deleted %s" % m)
        #message = mmm.service.users().messages().\
        #        get(userId='me', id=m['id']).execute()
        #print('Message snippet: %s' % message['snippet'])
    print("%d returned" % len(messages))

if __name__ == '__main__':
    main()
