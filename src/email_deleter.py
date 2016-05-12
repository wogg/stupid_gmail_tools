from __future__ import print_function
import httplib2
import os
import sys

from apiclient import discovery
from apiclient import errors

import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse
    argparser = argparse.ArgumentParser(parents=[tools.argparser])
    argparser.add_argument("--label", dest='label')
    argparser.add_argument("--limit", dest='limit', type=int)
    argparser.add_argument("--before", dest='before')
    argparser.add_argument("--from", dest='match_from')
    argparser.add_argument("--threads", dest='threads', action='store_true')
    argparser.add_argument("--unread-only", dest='unread_only', action='store_true')
    flags = argparser.parse_args()
except ImportError:
    flags = None

#:SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
SCOPES = 'https://mail.google.com/'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Commit Gmailicide'

class MarksMailMurder():
    def __init__(self, limit=1000, before=None, match_from=None,
            unread_only=False):
        """Shows basic usage of the Gmail API.

        Creates a Gmail API service object and outputs a list of label names
        of the user's Gmail account.
        """
        self.credentials = self.get_credentials()
        self.http = self.credentials.authorize(httplib2.Http())
        self.service = discovery.build('gmail', 'v1', http=self.http)
        self.label_by_name = None
        self.limit = limit
        self.before = before
        self.match_from = match_from
        self.unread_only = unread_only
        self.returned = 0
        self.deleted = 0

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

    def get_query(self):
        query = "before:%s" % self.before
        if self.match_from is not None:
            query += " from:%s" % self.match_from
        if self.unread_only:
            query += " is:unread"
        return query

    def inbox_messages(self):
        query = self.get_query()
        response = self.service.users().messages().\
                list(userId='me', q=query).execute()
        messages=[]
        if 'messages' in response:
            messages.extend(response['messages'])
            while 'nextPageToken' in response:
                if len(messages) >= self.limit:
                    break
                page_token = response['nextPageToken']
                response = self.service.users().messages().\
                        list(userId='me', q=query, pageToken=page_token).execute()
                messages.extend(response['messages'])
        return messages

    def messages_for_label(self, label=None):
        query = self.get_query()
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
        self.returned = len(messages)
        return messages

    def threads_for_label(self, label=None):
        query = self.get_query()
        response = self.service.users().threads().\
                list(userId='me', labelIds=[label['id']], 
                        q=query).execute()
        mthreads=[]
        if 'threads' in response:
            mthreads.extend(response['threads'])
            while 'nextPageToken' in response:
                if len(mthreads) >= self.limit:
                    break
                page_token = response['nextPageToken']
                response = self.service.users().threads().\
                        list(userId='me', labelIds=[label['id']],
                                q=query, pageToken=page_token).execute()
                mthreads.extend(response['threads'])
        self.returned = len(mthreads)
        return mthreads

    def label_for_name(self, name=None):
        if self.label_by_name is None:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            self.label_by_name = {}
            for label in labels:
                self.label_by_name[label['name']] = label
        return self.label_by_name[name]

    def delete_messages(self, messages):
        if type(messages) is not list:
            messages = [messages]
        count = 0
        for message in messages:
            count += 1
            self.deleted += 1
            try:
                self.delete_message(message)
                print("deleted: %s" % message, file=sys.stdout, flush=True)
            except errors.HttpError as e:
                print("error deleting: %s" % e, file=sys.stdout, flush=True)
            if count >= self.limit:
                break
        return count

    def delete_message(self, message):
        self.service.users().messages().\
                delete(userId='me', id=message['id']).execute()

    def delete_thread(self, thread):
        self.service.users().threads().\
                delete(userId='me', id=thread['id']).execute()

    def delete_threads(self, threads):
        if type(threads) is not list:
            threads = [threads]
        count = 0
        for thread in threads:
            count += 1
            self.deleted += 1
            try:
                self.delete_thread(thread)
                print("deleted: %s" % thread, file=sys.stdout, flush=True)
            except errors.HttpError as e:
                print("error deleting: %s" % e, file=sys.stdout, flush=True)
            if count >= self.limit:
                break
        return count


def main():
    print("%s" % flags)
    mmm = MarksMailMurder(flags.limit, flags.before, flags.match_from,
            flags.unread_only)
    print("query: %s" % mmm.get_query())
    try:
        if flags.threads:
            threads = []
            threads = mmm.threads_for_label(mmm.label_for_name(flags.label))
            mmm.delete_threads(threads)
        else:
            messages = []
            if flags.label is None:
                messages = mmm.inbox_messages()
            else:
                messages = mmm.messages_for_label(mmm.label_for_name(flags.label))
            len(messages)
            mmm.delete_messages(messages)
    except KeyboardInterrupt:
        pass
    print("%d returned, %d deleted" % (mmm.returned, mmm.deleted))

if __name__ == '__main__':
    main()
