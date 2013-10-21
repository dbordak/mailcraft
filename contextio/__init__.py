"""Provides an object-oriented interface for the Context.IO API.

To use it, you have to [sign up for an account](http://context.io).

Once you have an account, you can create a new `ContextIO` object and interact
with the API using the methods on that object as a starting point.

import contextio as c

CONSUMER_KEY = 'YOUR_API_KEY'
CONSUMER_SECRET = 'YOUR_API_SECRET'

context_io = c.ContextIO(
  consumer_key=CONSUMER_KEY, 
  consumer_secret=CONSUMER_SECRET
)

The module has tons of docstrings! Do help() calls in an interpreter to see
how to use the module.

The main context_io object is the parent of all objects and handles 
authentication. If you store things like account or message ids and want
to be lazy about querying, you can instantiate things like account objects
like this:

account = Account(context_io, {'id': 'ACCOUNT_ID'})

If you want to populate the other account properties from the api, just do a:

account.get()

If you want to instantiate a sub-resource of an Account, just pass the
account object as the parent.

message = Message(account, {'id': 'MESSAGE_ID'})
"""


import logging
import re

from rauth import OAuth1Session
from urllib import urlencode, quote

from util import as_bool, as_datetime, process_person_info, uncamelize

# check to see if we can get json, or if we're on app engine
try:
    import json
except:
    from django.utils import simplejson as json

class ArgumentError(Exception):
    """Class to handle bad arguments."""
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ContextIO(object):
    """Parent class of module. This handles authentication and requests.
    
    Parameters:
        consumer_key: string - your Context.IO consumer key
        consumer_secret: string - your Context.IO consumer secret
        debug: string - Set to None by default. If you want debug messages, 
            set to either 'print' or 'log'. If set to 'print', debug messages 
            will be printed out. Useful for python's interactive console. If 
            set to 'log' will send debug messages to logging.debug()
    """

    def __init__(self, consumer_key, consumer_secret, debug=None, 
                    url_base='https://api.context.io'):
        """Constructor that creates oauth2 consumer and client.
        
        Required Arguments:
            consumer_key: string - your api key
            consumer_secret: string - you api secret
        
        Optional Arguments:
            debug: if used, set to either 'print' or 'log' - if print, debug
                messages will be sent to stdout. If set to 'log' will send
                to logging.debug()
        """
        self.version = '2.0'
        self.debug = debug
        if self.debug is True:   # for people who don't read the code and just set debug=True
            self.debug = "print"
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.url_base = url_base

    def _debug(self, response):
        """Prints or logs a debug message.
        
        Required Arguments:
            response: object - the rauth response object.
        
        Returns:
            None
        """
        if self.debug:
            message = ("--------------------------------------------------\n"
                "URL:    %s\nMETHOD: %s\nSTATUS: %s\n\nREQUEST\n%s\n\nRESPON"
                "SE\n%s\n") % (
                    response.request.url,
                    response.request.method,
                    response.status_code,
                    response.request.__dict__,
                    response.__dict__
                )
            
            if self.debug == 'print':
                print message
            elif self.debug == 'log':
                logging.debug(message)

    def _request_uri(self, uri, method="GET", params={}, headers={}, body=''):
        """Assembles the request uri and calls the request method.
        
        Required Arguments:
            uri: string - the assembled API endpoint.
        
        Optional Parameters:
            method: string - the method of the request. Possible values are 
                'GET', 'POST', 'DELETE', 'PUT'
            params: dict - parameters to pass along
            headers: dict - any specific http headers
            body: string - request body, only used on a few PUT statements
        
        Returns:
            typically, JSON - depends on the API call, refer to the other 
                method docstrings for more details.
        """
        url = '/'.join((self.url_base, self.version, uri))
        response = self._request(url, method, params, headers, body)
        status = response.status_code
        
        if status >= 200 and status < 300:
            # look for a ValueError
            try:
                return response.json()
            except UnicodeDecodeError:
                return response.content
            except ValueError:
                return response.text
        else:
            self._handle_request_error(response)

    def _request(self, url, method, params, headers={}, body=''):
        """This method actually makes the request using the oauth client.
        
        Required Arguments:
            url: string - the API endpoint.
            method: string - the type of request, either 'GET', 'POST', 
                'DELETE', or 'PUT'
            params: dict - dictionary of parameters for the call
            headers: dict - dict of any custom headers.
        
        Optional Arguments:
            body: string - this is only used on a few API calls, mostly PUTS.
        
        Returns:
            typically JSON, depends on the API call. Refer to the specific 
                method you're calling to learn what the return will be.
        """
        
        session = OAuth1Session(self.consumer_key, self.consumer_secret)

        if method == 'POST':
            params['body'] = body
            response = session.request(method, url, header_auth=True, data=params, headers=headers)
        else:
            response = session.request(method, url, header_auth=True, params=params, headers=headers, data=body)

        self._debug(response)

        return response

    def _handle_request_error(self, response):
        """This method formats request errors and raises appropriate 
            exceptions."""
        response_json = response.json()
        if 'code' in response_json and 'value' in response_json:
            raise Exception(
                'HTTP %s: %s' % (
                    response_json['code'],
                    response_json['value']
                )
            )
        elif 'type' in response_json and 'value' in response_json:
            raise Exception(
                '%s: %s' % (
                    response_json['type'],
                    response_json['value']
                )
            )
        else:
            raise Exception(response.text)

    def get_accounts(self, **params):
        """List of Accounts.
        
        GET method for the accounts resource. 
        
        Documentation: http://context.io/docs/2.0/accounts#get
        
        Optional Arguments:
            email: string - Only return account associated 
                to this email address
            status: string - Only return accounts with sources 
                whose status is of a specific value. If an account has many 
                sources, only those matching the given value will be 
                included in the response. Possible statuses are: 
                INVALID_CREDENTIALS, CONNECTION_IMPOSSIBLE, 
                NO_ACCESS_TO_ALL_MAIL, OK, TEMP_DISABLED and DISABLED
            status_ok: int - Only return accounts with sources 
                whose status is of a specific value. If an account has many 
                sources, only those matching the given value will be included 
                in the response. Possible statuses are: INVALID_CREDENTIALS, 
                CONNECTION_IMPOSSIBLE, NO_ACCESS_TO_ALL_MAIL, OK, TEMP_DISABLED
                and DISABLED
            limit: int - The maximum number of results to return
            offset: int - Start the list at this offset (zero-based)
        
        Returns:
            A list of Account objects
        """
        all_args = ['email', 'status', 'status_ok', 'limit', 'offset']
        
        params = Resource.sanitize_params(params, all_args)
        return [Account(self, obj) for obj in self._request_uri(
            'accounts', params=params
        )]

    def post_account(self, **params):
        """Add a new account.
        
        POST method for the accounts resource.
        
        You can optionally pass in the params to simultaneously add a source
        with just this one call.

        Documentation: http://context.io/docs/2.0/accounts#post

        Required Arguments:
            email: string - The primary email address of the account holder.
            
        Optional Arguments:
            first_name: string - First name of the account holder.
            last_name: string - Last name of the account holder.
        
        If adding a source in the same call:
        Required Arguments:
            server: string - Name of IP of the IMAP server, eg. imap.gmail.com
            username: string - The username used to authentify an IMAP 
                connection. On some servers, this is the same thing as 
                the primary email address.
            use_ssl: integer - Set to 1 if you want SSL encryption to 
                be used when opening connections to the IMAP server. Any 
                other value will be considered as "do not use SSL"
            port: integer - Port number to connect to on the server. Keep in 
                mind that most IMAP servers will have one port for standard 
                connection and another one for encrypted connection (see 
                use-ssl parameter above)
            type: string - Currently, the only supported type is IMAP
        
        Optional Arguments:
            sync_period: string - Sets the period at which the Context.IO 
                index for this source is synced with the origin email 
                account on the IMAP server. Possible values are 1h, 4h, 12h 
                and 24h (default).
            raw_file_list: integer - By default, we filter out files like 
                signature images or those winmail.dat files form the files 
                list. Set this parameter to 1 to turn off this filtering and 
                show every single file attachments.
            password: string - Password for authentication on the IMAP server. 
                Ignored if any of the provider_* parameters are set below.
            provider_token: string - An OAuth token obtained from the IMAP 
                account provider to be used to authentify on this email 
                account.
            provider_token_secret: string - An OAuth token secret obtained 
                from the IMAP account provider to be used to authentify on 
                this email account.
            provider_consumer_key: string - The OAuth consumer key used to 
                obtain the the token and token secret above for that account. 
                That consumer key and secret must be configured in your 
                Context.IO account.
            callback_url: string (url) - If specified, we'll make a POST 
                request to this URL when the initial sync is completed.

        Returns:
            An Account object
        """
        req_args = ['email', ]
        all_args = ['email', 'first_name', 'last_name', 'server', 
            'username', 'use_ssl', 'port', 'type', 'sync_period', 
            'raw_file_list', 'password', 'provider_token', 
            'provider_token_secret', 'provider_consumer_key', 'callback_url'
        ]
        
        params = Resource.sanitize_params(params, all_args, req_args)

        return Account(self, self._request_uri(
            'accounts', method="POST", params=params
        ))

    def get_connect_tokens(self):
        """Get a list of connect tokens created with your API key.
        
        Documentation: http://context.io/docs/2.0/connect_tokens#get
        
        Arguments:
            None
        
        Returns:
            A list of ConnectToken objects.
        """
        return [ConnectToken(self, obj) for obj in self._request_uri(
            'connect_tokens'
        )]

    def post_connect_token(self, **params):
        """Obtain a new connect token.
        
        Documentation: http://context.io/docs/2.0/connect_tokens#post
        
        Required Arguments:
            callback_url: string (url) - When the user's mailbox is connected 
                to your API key, the browser will call this url (GET). This 
                call will have a parameter called contextio_token indicating 
                the connect_token related to this callback. You can then do a 
                get on this connect_token to obtain details about the account 
                and source created through that token and save that account id 
                in your own user data.
        
        Optional Arguments:
            email: string - The email address of the account to be added. If 
                specified, the first step of the connect UI where users are 
                prompted for their email address, first name and last name is 
                skipped.
            first_name: string - First name of the account holder.
            last_name: string - Last name of the account holder.
            source_callback_url: string - If specified, we'll make a POST 
                request to this URL when the initial sync is completed.
            source_sync_all_folders: integer - By default, we filter out some 
                folders like 'Deleted Items' and 'Drafts'. Set this parameter 
                to 1 to turn off this filtering and show every single folder.
            source_sync_flags: integer - By default, we don't synchronize IMAP 
                flags. Set this parameter to 1 to turn on IMAP flag syncing 
                for the 'seen' and 'flagged' flags.
            source_raw_file_list: integer - By default, we filter out files 
                like signature images from the files list. Set this parameter 
                to 1 to turn off this filtering and show every single file 
                attachment.
        
        Returns:
            A dictionary, data format below
            
            {
              "success": string - true if connect_token was successfully 
                  created, false otherwise,
              "token": string - Id of the token,
              "resource_url": string - URL to of the token,
              "browser_redirect_url": string - Redirect the user's browser to 
                  this URL to have them connect their mailbox through this 
                  token
            }
        """
        req_args = ['callback_url', ]
        all_args = [
            'callback_url', 'email', 'first_name', 'last_name', 
            'source_callback_url', 'source_sync_all_folders', 
            'source_sync_flags', 'source_raw_file_list'
        ]
        
        params = Resource.sanitize_params(params, all_args, req_args)
        
        return self._request_uri('connect_tokens', method='POST', params=params)

    def get_discovery(self, **params):
        """Attempts to discover IMAP settings for a given email address.
        
        Documentation: http://context.io/docs/2.0/discovery
        
        Required Arguments:
            source_type: string - The type of source you want to discover 
                settings for. Right now, the only supported source type is IMAP
            email: string - An email address you want to discover IMAP 
                settings for. Make sure source_type is set to IMAP.
        
        Returns:
            A Discovery object.
        """
        if 'source_type' not in params:
            params['source_type'] = 'IMAP'

        req_args = ['source_type', 'email']
        all_args = ['source_type', 'email']
        
        params = Resource.sanitize_params(params, all_args, req_args)

        return Discovery(self, self._request_uri('discovery', params=params))

    def get_oauth_providers(self):
        """List of oauth providers configured.
        
        Documentation: http://context.io/docs/2.0/oauth_providers#get
        
        Arguments:
            None
        
        Returns:
            A list of OauthProvider objects.
        """
        return [OauthProvider(self, obj) for obj in
            self._request_uri('oauth_providers')
        ]
    
    def post_oauth_provider(self, **params):
        """Add a new OAuth provider.
        
        Required Arguments:
            type: string - 	Identification of the OAuth provider. This must be 
                either GMAIL and GOOGLEAPPSMARKETPLACE.
            provider_consumer_key: string - The OAuth consumer key
            provider_consumer_secret: string - The OAuth consumer secret
        
        Returns:
            a dict
        """
        req_args = [
            'type', 'provider_consumer_key', 'provider_consumer_secret']
        all_args = [
            'type', 'provider_consumer_key', 'provider_consumer_secret']
        
        params = Resource.sanitize_params(params, all_args, req_args)
        
        self._request_uri('oauth_providers', method='POST', params=params)


class Resource(object):
    """Base class for resource objects."""
    keys = []
    
    def __init__(self, parent, base_uri, defn):
        """Constructor."""
        defn = uncamelize(defn)

        for k in self.__class__.keys:
            if k in defn:
                setattr(self, k, defn[k])
            else:
                setattr(self, k, None)

        self.parent = parent
        self.base_uri = quote(base_uri.format(**defn))

    def _uri_for(self, *elems):
        """Joins API endpoint elements and returns a string."""
        return '/'.join([self.base_uri] + list(elems))

    def _request_uri(
        self, uri_elems, method="GET", params={}, headers={}, body=''):
        """Gathers up request elements and helps form the request object.
        
        Required Arguments:
            uri_elems: list - list of strings, joined to form the endpoint.
        
        Optional Arguments:
            method: string - the method of the request. Possible values are 
                'GET', 'POST', 'DELETE', 'PUT'
            params: dict - parameters to pass along
            headers: dict - any specific http headers
            body: string - request body, only used on a few PUT statements
        """
        uri = self._uri_for(uri_elems)
        return self.parent._request_uri(
            uri, method=method, params=params, headers=headers, body=body
        )
        
    @staticmethod
    def sanitize_params(params, all_args, required_args=None):
        """Removes parameters that aren't valid.
        
        Required Arguments:
            params: dict - key/value pairs of arguments
            all_args: list - list of strings, each string is a 
                valid parameter.
        
        Optional Args:
            required_arguments: list - ironically, required_arguments is an 
                optional argument here. a list of string, each string is a 
                required argument.
        
        Returns:
            dictionary of key, value pairs of valid parameters.
        """
        if required_args:
            # check to be sure we have all the required params
            missing_required_args = []
            for required_arg in required_args:
                param = params.get(required_arg)
                if param == None:
                    missing_required_args.append(required_arg)
        
            # yell if we're missing a required argument
            if missing_required_args:
                raise ArgumentError(
                    'Missing the following required arguments: %s' \
                    % ', '.join(missing_required_args)
                )
        
        # remove any arguments not recognized
        cleaned_args = {}
        for arg in all_args:
            if arg in params:
                cleaned_args[arg] = params[arg]
                del params[arg]
        
        # quietly yell in a non-breaking way if there's any unrecognized 
        # arguments left
        if params:
            logging.warning('Invalid arguments found: %s' % \
                ', '.join(param for param in params))
        
        return cleaned_args


class Account(Resource):
    """Class to represent the Account resource.
    
    Properties:
        id: string - Id of the account
        username: string - Username assigned to the account
        created: integer (unix timestamp) - account creation time 
        suspended: integer (unix timestamp) - account suspension time 0 means 
            not suspended
        email_addresses: list - email addresses for this account
        first_name: string - First name of account holder
        last_name: string - Last name of account holder
        password_expired: integer (unix timestamp) - user's password 
            expiration. 0 means still valid
        sources: list - email accounts where this account gets data from
        nb_messages: integer - Total number of messages in all sources of 
            this account
        nb_files: integer - Total number of files in all sources of this 
            account
    """
    keys = ['id', 'username', 'created', 'suspended', 'email_addresses', 
        'first_name', 'last_name', 'password_expired', 'sources', 
        'nb_messages', 'nb_files']

    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: ContextIO object - parent is the ContextIO object to handle
                authentication.
            defn: a dictionary of parameters. The 'id' parameter is required to
                make method calls.
        """
        super(Account, self).__init__(parent, 'accounts/{id}', defn)

    def get(self):
        """GET details for a given account.
        
        GET method for the account resource.
        
        Documentation: http://context.io/docs/2.0/accounts#id-get
        
        Arguments:
            None
            
        Returns:
            True if self is updated, else will throw a request error
        """
        self.__init__(self.parent, self._request_uri(''))
        return True
        
    def delete(self):
        """Remove a given account.
        
        DELETE method for the account resource.
        
        Documentation: http://context.io/docs/2.0/accounts#id-delete
        
        Arguments:
            None
        
        Returns:
            Bool
        """
        status = self._request_uri('', method='DELETE')
        return bool(status['success'])
        
    def post(self, **params):
        """Modifies a given account.
        
        POST method for the account resource.
        
        Documentation: http://context.io/docs/2.0/accounts#id-post
        
        Optional Arguments:
            first_name: string - First name of the account holder
            last_name: string - Last name of the account holder
        
        Returns:
            Bool
        """
        all_args = ['first_name', 'last_name']
        
        params = Resource.sanitize_params(params, all_args)
        
        # update account object with new values
        if 'first_name' in params:
            self.first_name = params['first_name']
        if 'last_name' in params:
            self.last_name = params['last_name']
        
        status = self._request_uri('', method='POST', params=params)
        return bool(status['success'])

    def get_connect_tokens(self):
        """List of connect tokens created for an account.
        
        Documentation: http://context.io/docs/2.0/accounts/connect_tokens#get
        
        Arguments:
            None
        
        Returns:
            A list of ConnectToken objects
        """
        return [ConnectToken(self, obj) for obj in self._request_uri(
            'connect_tokens'
        )]

    def post_connect_token(self, **params):
        """Obtain a new connect_token for a specific account.
        
        * Note: unused connect tokens are purged after 24 hours.
        
        Documentation: http://context.io/docs/2.0/accounts/connect_tokens#post
        
        Required Arguments:
            callback_url: string (url) - When the user's mailbox is connected 
                to your API key, the browser will call this url (GET). This 
                call will have a parameter called contextio_token indicating 
                the connect_token related to this callback. You can then do a 
                get on this connect_token to obtain details about the account 
                and source created through that token and save that account id 
                in your own user data.
        
        Optional Arguments:
            email: string (email) - The email address of the account to be 
                added. If specified, the first step of the connect UI where 
                users are prompted for their email address, first name and 
                last name is skipped.
            first_name: string - First name of the account holder.
            last_name: string - Last name of the account holder.
            source_callback_url: string (url) - If specified, we'll make a 
                POST request to this URL when the initial sync is completed.
            source_sync_all_folders: integer - By default, we filter out some 
                folders like 'Deleted Items' and 'Drafts'. Set this parameter 
                to 1 to turn off this filtering and show every single folder.
            source_sync_flags: integer - By default, we don't synchronize IMAP 
                flags. Set this parameter to 1 to turn on IMAP flag syncing 
                for the 'seen' and 'flagged' flags.
            source_raw_file_list: integer - By default, we filter out files 
                like signature images from the files list. Set this parameter 
                to 1 to turn off this filtering and show every single file 
                attachment.
            
        Returns:
            A dictionary (data format below)
            
            {
              "success": string - true if connect_token was successfully 
                  created, false otherwise,
              "token": string - Id of the token,
              "resource_url": string - URL to of the token,
              "browser_redirect_url": string - Redirect the user's browser to 
                  this URL to have them connect their mailbox through this 
                  token
            }
        """
        req_args = ['callback_url', ]
        all_args = ['callback_url', 'email', 'first_name', 'last_name', 
            'source_callback_url', 'source_sync_all_folders', 
            'source_sync_flags', 'source_raw_file_list'
        ]
        
        params = Resource.sanitize_params(params, all_args, req_args)
        
        return self._request_uri('connect_tokens', method='POST', params=params)

    def get_contacts(self, **params):
        """List contacts in an account.
        
        Documentation: http://context.io/docs/2.0/accounts/contacts#get
        
        Optional Arguments:
            search: string - String identifying the name or the email address 
                of the contact(s) you are looking for.
            active_before: integer (unix time) - Only include contacts 
                included in at least one email dated before a given time. This 
                parameter should be a standard unix timestamp
            active_after: integer (unix time) - Only include contacts included 
                in at least one email dated after a given time. This parameter 
                should be a standard unix timestamp
            limit: integer - The maximum number of results to return.
            offset: integer - Start the list at this offset (zero-based).
        
        Returns:
            A list of Contact objects
        """
        all_args = [
            'search', 'active_before', 'active_after', 'limit', 'offset'
        ]
        
        params = Resource.sanitize_params(params, all_args)
        
        return [Contact(self, obj) for obj in self._request_uri(
            'contacts', params=params).get('matches'
        )]

    def get_email_addresses(self):
        """List of email addresses used by an account.
        
        Documentation: http://context.io/docs/2.0/accounts/email_addresses#get
        
        Arguments:
            None
        
        Returns:
            A list of EmailAddress objects.
        """
        return [EmailAddress(self, obj) for obj in self._request_uri(
            'email_addresses'
        )]

    def post_email_address(self, **params):
        """Add a new email address as an alias for an account.
        
        Documentation: http://context.io/docs/2.0/accounts/email_addresses#post
        
        Required Arguments:
            email_address: string - An email address.
        
        Returns:
            An EmailAddress object.
        """
        req_args = ['email_address', ]
        all_args = ['email_address', ]
        
        params = Resource.sanitize_params(params, all_args, req_args)
        
        return EmailAddress(self, self._request_uri(
            'email_addresses', method='POST', params=params
        ))

    def get_files(self, **params):
        """List of files found as email attachments.
        
        GET method for the files resource.
        
        Documentation: http://context.io/docs/2.0/accounts/files
        
        Each of the email, to, from, cc and bcc parameters can be set to a 
        comma-separated list of email addresses. These multiple addresses 
        are treated as an OR combination.

        You can set more than one parameter when doing this call. Multiple 
        parameters are treated as an AND combination.
        
        Optional Arguments:
            file_name: string - Search for files based on their name. You can 
                filter names using typical shell wildcards such as *, ? and [] 
                or regular expressions by enclosing the search expression in a 
                leading / and trailing /. For example, *.pdf would give you 
                all PDF files while /\.jpe?g$/ would return all files whose 
                name ends with .jpg or .jpeg
            email: string - Email address of the contact for whom you want the 
                latest files exchanged with. By "exchanged with contact X" we 
                mean any email received from contact X, sent to contact X or 
                sent by anyone to both contact X and the source owner.
            to: string - Email address of a contact files have been sent to.
            from: string - Email address of a contact files have been received 
                from.
            cc: string - Email address of a contact CC'ed on the messages.
            bcc: string - Email address of a contact BCC'ed on the messages.
            date_before: integer (unix time) - Only include files attached to 
                messages sent before a given timestamp. The value this filter 
                is applied to is the Date: header of the message which refers 
                to the time the message is sent from the origin.
            date_after: integer (unix time) - Only include files attached to 
                messages sent after a given timestamp. The value this filter 
                is applied to is the Date: header of the message which refers 
                to the time the message is sent from the origin.
            indexed_before: integer (unix time) - Only include files attached 
                to messages indexed before a given timestamp. This is not the 
                same as the date of the email, it is the time Context.IO 
                indexed this message.
            indexed_after: integer (unix time) - Only include files attached 
                to messages indexed after a given timestamp. This is not the 
                same as the date of the email, it is the time Context.IO 
                indexed this message.
            group_by_revisions: integer - If set to 1, the list will do an 
                intelligent grouping of files to reflect occurrences of the 
                same document. The grouping algorithm is exactly the same as 
                the one used to get file revisions but only the occurrences 
                matching the filters applied to the list will be included in 
                the results.
            sort_order: string - The sort order of the returned results. 
                Possible values are asc and desc
            limit: integer - The maximum number of results to return.
            offset: integer - Start the list at this offset (zero-based).
        
        Returns:
            A list of File objects
        """
        all_args = [
            'name', 'email', 'to', 'from', 'cc', 'bcc', 'date_before', 
            'date_after', 'indexed_before', 'indexed_after', 
            'group_by_revisions', 'limit', 'offset'
        ]
        
        params = Resource.sanitize_params(params, all_args)
        
        return [File(self, obj) for obj in self._request_uri(
            'files', params=params
        )]

    def get_messages(self, **params):
        """List email messages for an account.
        
        GET method for the messages resource.
        
        Each of the email, to, from, cc and bcc parameters can be set to a 
        comma-separated list of email addresses. These multiple addresses 
        are treated as an OR combination.

        You can set more than one parameter when doing this call. Multiple 
        parameters are treated as an AND combination.
        
        Optional Arguments:
            subject: string - Get messages whose subject matches this search 
                string. To use regular expressions instead of simple string 
                matching, make sure the string starts and ends with /.
            email: string - Email address of the contact for whom you want the 
                latest messages exchanged with. By "exchanged with contact X" 
                we mean any email received from contact X, sent to contact X 
                or sent by anyone to both contact X and the source owner.
            to: string - Email address of a contact messages have been sent to.
            sender: string - Email address of a contact messages have been 
                received from. Same as "from" in documentation. "from" is a
                python keyword and we can't use that...
            cc: string - Email address of a contact CC'ed on the messages.
            bcc: string - Email address of a contact BCC'ed on the messages.
            folder: string - Filter messages by the folder (or Gmail label). 
                This parameter can be the complete folder name with the 
                appropriate hierarchy delimiter for the mail server being 
                queried (eg. Inbox/My folder) or the "symbolic name" of the 
                folder (eg. \Starred). The symbolic name refers to attributes 
                used to refer to special use folders in a language-independant 
                way. See http://code.google.com/apis/gmail/imap/#xlist 
                (Gmail specific) and RFC-6154.
            file_name: string - Search for files based on their name. You can 
                filter names using typical shell wildcards such as *, ? and [] 
                or regular expressions by enclosing the search expression in a 
                leading / and trailing /. For example, *.pdf would give you 
                all PDF files while /\.jpe?g$/ would return all files whose 
                name ends with .jpg or .jpeg
            date_before: integer (unix time) - Only include messages before a 
                given timestamp. The value this filter is applied to is the 
                Date: header of the message which refers to the time the 
                message is sent from the origin.
            date_after: integer (unix time) - Only include messages after a 
                given timestamp. The value this filter is applied to is the 
                Date: header of the message which refers to the time the 
                message is sent from the origin.
            indexed_before: integer (unix time) - Only include messages 
                indexed before a given timestamp. This is not the same as the 
                date of the email, it is the time Context.IO indexed this 
                message.
            indexed_after: integer (unix time) - Only include messages indexed 
                after a given timestamp. This is not the same as the date of 
                the email, it is the time Context.IO indexed this message.
            include_body: integer - Set to 1 to include message bodies in the 
                result. Since message bodies must be retrieved from the IMAP 
                server, expect a performance hit when setting this parameter.
            include_headers: mixed - Can be set to 0 (default), 1 or raw. If 
                set to 1, complete message headers, parsed into an array, are 
                included in the results. If set to raw, the headers are also 
                included but as a raw unparsed string. Since full original 
                headers bodies must be retrieved from the IMAP server, expect 
                a performance hit when setting this parameter.
            include_flags: integer - Set to 1 to include IMAP flags of 
                messages in the result. Since message flags must be retrieved 
                from the IMAP server, expect a performance hit when setting 
                this parameter.
            body_type: string - Used when include_body is set to get only body 
                parts of a given MIME-type (for example text/html)
            sort_order: string - The sort order of the returned results. 
                Possible values are asc and desc
            limit: integer - The maximum number of results to return.
            offset: integer - Start the list at this offset (zero-based).
        
        Returns:
            A list of Message objects.
        """
        all_args = ['subject', 'email', 'to', 
            'sender', 'cc', 'bcc', 'folder', 'date_before', 'date_after', 
            'indexed_before', 'indexed_after', 'include_body', 'file_name',
            'include_headers', 'include_flags', 'body_type', 'sort_order', 
            'limit', 'offset'
        ]
        
        params = Resource.sanitize_params(params, all_args)
        
        # workaround to send param "from" even though it's a reserved keyword 
        # in python
        if 'sender' in params:
            params['from'] = params['sender']
            del params['sender']
        
        return [Message(self, obj) for obj in self._request_uri(
            'messages', params=params
        )]

    def post_message(self, **params):
        """Add a mesage in a given folder.
        
        Documentation: http://context.io/docs/2.0/accounts/messages#post
        
        Required Arguments:
            dst_source: string - Label of the source you want the message 
                copied to
            dst_folder: string - The folder within dst_source the message 
                should be copied to
            message: file - Raw RFC-822 message data. If you use the "view 
                message source" function of your email client, what you'll see 
                there is what we expect to receive here. Hint: you can get 
                this with the accounts/messages/source call.
        
        Returns:
            Bool
        """
        headers = {'Content-Type': 'multipart/form-data'}
        
        req_args = ['dst_source', 'dst_folder', 'message']
        all_args = ['dst_source', 'dst_folder', 'message']
        
        params = Resource.sanitize_params(params, all_args, req_args)
        
        return self._request_uri(
            'messages', method='POST', params=params, headers=headers)

    def get_sources(self, **params):
        """Lists IMAP sources assigned for an account.
        
        GET method for sources resource.
        
        Documentation: http://context.io/docs/2.0/accounts/sources#get
        
        Optional Arguments:
            status: string - Only return sources whose status is of a specific 
                value. Possible statuses are: INVALID_CREDENTIALS, 
                CONNECTION_IMPOSSIBLE, NO_ACCESS_TO_ALL_MAIL, OK, 
                TEMP_DISABLED, and DISABLED
            status_ok: integer - Set to 0 to get sources that are not working 
                correctly. Set to 1 to get those that are.
        
        Returns:
            A list of Source objects
        """
        all_args = ['status', 'status_ok']
        params = Resource.sanitize_params(params, all_args)
        
        return [Source(self, obj) for obj in self._request_uri(
            'sources', params=params
        )]

    def post_source(self, **params):
        """Add a mailbox to a given account.
        
        Documentation: http://context.io/docs/2.0/accounts/sources#post
        
        Required Arguments:
            email: string - The primary email address used to receive emails 
                in this account
            server: string - Name of IP of the IMAP server, eg. imap.gmail.com
            username: string - The username used to authentify an IMAP 
                connection. On some servers, this is the same thing as 
                the primary email address.
            use_ssl: integer - Set to 1 if you want SSL encryption to 
                be used when opening connections to the IMAP server. Any 
                other value will be considered as "do not use SSL"
            port: integer - Port number to connect to on the server. Keep in 
                mind that most IMAP servers will have one port for standard 
                connection and another one for encrypted connection (see 
                use-ssl parameter above)
            type: string - Currently, the only supported type is IMAP
        
        Optional Arguments:
            sync_period: string - Sets the period at which the Context.IO 
                index for this source is synced with the origin email 
                account on the IMAP server. Possible values are 1h, 4h, 12h 
                and 24h (default).
            raw_file_list: integer - By default, we filter out files like 
                signature images or those winmail.dat files form the files 
                list. Set this parameter to 1 to turn off this filtering and 
                show every single file attachments.
            password: string - Password for authentication on the IMAP server. 
                Ignored if any of the provider_* parameters are set below.
            provider_refresh_token: An OAuth2 refresh token obtained from the
                IMAP account provider to be used to authentify on this email
                account.
            provider_token: string - An OAuth token obtained from the IMAP 
                account provider to be used to authentify on this email 
                account.
            provider_token_secret: string - An OAuth token secret obtained 
                from the IMAP account provider to be used to authentify on 
                this email account.
            provider_consumer_key: string - The OAuth consumer key used to 
                obtain the the token and token secret above for that account. 
                That consumer key and secret must be configured in your 
                Context.IO account.
            callback_url: string (url) - If specified, we'll make a POST 
                request to this URL when the initial sync is completed.
        
        Returns:
            A mostly empty Source object or False if something failed.
        """
        # set some default values
        if 'use_ssl' not in params:
            params['use_ssl'] = 1
        if 'port' not in params:
            params['port'] = 993
        if 'type' not in params:
            params['type'] = 'IMAP'
        
        req_args = ['email', 'server', 'username', 'port', 'type', 'use_ssl']
        all_args = [
            'email', 'server', 'username', 'port', 'type', 'use_ssl', 
            'sync_period', 'raw_file_list', 'password',
            'provider_refresh_token', 'provider_token', 
            'provider_token_secret', 'provider_consumer_key', 
            'callback_url'
        ]
        params = Resource.sanitize_params(params, all_args, req_args)
        
        data = self._request_uri('sources', method='POST', params=params)
        status = bool(data['success'])
        
        if status:
            return Source(self, {'label': data['label']})
        else:
            return False

    def get_sync(self):
        """Sync status for all sources of the account.
        
        Documentation: http://context.io/docs/2.0/accounts/sync#get
        
        Arguments:
            None
        
        Returns:
            A dictionary (see below for data structure)
        
        {ACCOUNT_NAME: 
            {SOURCE: 
                {u'last_sync_start': UNIX_TIMESTAMP, 
                u'last_sync_stop': UNIX_TIMESTAMP, 
                u'last_expunge': UNIX_TIMESTAMP, 
                u'initial_import_finished': BOOL}
            }
        }
        """
        return self._request_uri('sync')

    def post_sync(self):
        """Trigger a sync of all sources on the account.
        
        Documentation: http://context.io/docs/2.0/accounts/sync#post
        
        Arguments:
            None
        
        Returns:
            A dictionary (see below for data structure)
        
            {
                u'syncsQueued': STRING, 
                u'syncs_queued': STRING, 
                u'resource_url': STRING, 
                u'success': BOOL
            }
        """
        return self._request_uri('sync', method='POST')

    def get_threads(self, **params):
        """List of threads on an account.
        
        Documentation: http://context.io/docs/2.0/accounts/threads#get
        
        Optional Arguments:
            subject: string - Get threads with messages whose subject matches 
                this search string. To use regular expressions instead of 
                simple string matching, make sure the string starts and ends 
                with /.
            email: string - Email address of the contact for whom you want the 
                latest threads. This value is interpreted as received from 
                email X, sent to email X or sent by anyone to both email X and 
                the source owner.
            to: string - Get threads with at least one message sent to this 
                email address.
            sender: string - Get threads with at least one message sent from 
                this email address.
            cc: string - Get threads with at least one message having this 
                email address CC'ed.
            bcc: string - Get threads with at least one message having this 
                email address BCC'ed.
            folder: string - Filter threads by the folder (or Gmail label). 
                This parameter can be the complete folder name with the 
                appropriate hierarchy delimiter for the mail server being 
                queried (eg. Inbox/My folder) or the "symbolic name" of the 
                folder (eg. \Starred). The symbolic name refers to attributes 
                used to refer to special use folders in a language-independant 
                way. See http://code.google.com/apis/gmail/imap/#xlist (Gmail 
                specific) and RFC-6154.
            indexed_before: integer (unix time) - Get threads with at least 
                one message indexed before this timestamp. This is not the 
                same as the date of the email, it is the time Context.IO 
                indexed this message.
            indexed_after: integer (unix time) - Get threads with at least one 
                message indexed after this timestamp. This is not the same as 
                the date of the email, it is the time Context.IO indexed this 
                message.
            active_before: integer (unix time) - Get threads with at least one 
                message dated before this timestamp. The value this filter is 
                applied to is the Date: header of the message which refers to 
                the time the message is sent from the origin.
            active_after: integer (unix time) - Get threads with at least one 
                message dated after this timestamp. The value this filter is 
                applied to is the Date: header of the message which refers to 
                the time the message is sent from the origin.
            started_before: integer (unix time) - Get threads whose first 
                message is dated before this timestamp. The value this filter 
                is applied to is the Date: header of the message which refers 
                to the time the message is sent from the origin.
            started_after: integer (unix time) - Get threads whose first 
                message is dated after this timestamp. The value this filter 
                is applied to is the Date: header of the message which refers 
                to the time the message is sent from the origin.
            limit: integer - The maximum number of results to return.
            offset: integer - Start the list at this offset (zero-based).
        
        Returns:
            A list of Thread objects (nearly empty thread objects). Use the 
                Thread.get() method to populate the object.
        """
        all_args = [
            'subject', 'email', 'to', 'sender', 'cc', 'bcc', 'folder', 
            'indexed_before', 'indexed_after', 'active_before', 'active_after',
            'started_before', 'started_after', 'limit', 'offset'
        ]
        params = Resource.sanitize_params(params, all_args)
        
        # workaround to send param "from" even though it's a reserved keyword 
        # in python
        if 'sender' in params:
            params['from'] = params['sender']
            del params['sender']
        
        thread_urls = self._request_uri('threads', params=params)
        objs = []
        
        # isolate just the gmail_thread_id so we can instantiate Thread objects
        for thread_url in thread_urls:
            url_components = thread_url.split('/')
            objs.append({'gmail_thread_id': url_components[-1]})
        
        return [Thread(self, obj) for obj in objs]

    def get_webhooks(self):
        """Listing of WebHooks configured for an account.
        
        GET method for the webhooks resource.
        
        Documentation: http://context.io/docs/2.0/accounts/webhooks#get
        
        Arguments:
            None
        
        Returns:
            A list of Webhook objects.
        """
        return [WebHook(self, obj) for obj in self._request_uri('webhooks')]
    
    def post_webhook(self, **params):
        """Create a new WebHook on an account.
        
        POST method for the webhooks resource.
        
        Documentation: http://context.io/docs/2.0/accounts/webhooks#post
        
        Required Arguments:
            callback_url: string (url) - A valid URL Context.IO calls when a 
                matching message is found.
            failure_notif_url: string (url) - A valid URL Context.IO calls 
                if the WebHooks fails and will no longer be active. That may 
                happen if, for example, the server becomes unreachable or if 
                it closes an IDLE connection and we can't re-establish it.
        
        Optional Arguments:
            filter_to: string - Check for new messages sent to a given name or 
                email address.
            filter_from: string - Check for new messages received from a given 
                name or email address.
            filter_cc: string - Check for new messages where a given name or 
                email address is cc'ed
            filter_subject: string - Check for new messages with a subject 
                matching a given string or regular expresion
            filter_thread: string - Check for new messages in a given thread. 
                Value can be a gmail_thread_id or the email_message_id or 
                message_id of an existing message currently in the thread.
            filter_new_important: string - Check for new messages 
                automatically tagged as important by the Gmail Priority Inbox 
                algorithm. To trace all messages marked as important 
                (including those manually set by the user), use 
                filter_folder_added with value Important. Note the leading 
                back-slash character in the value, it is required to keep this 
                specific to Gmail Priority Inbox. Otherwise any message placed 
                in a folder called "Important" would trigger the WebHook.
            filter_file_name: string - Check for new messages where a file 
                whose name matches the given string is attached. Supports 
                wildcards and regular expressions like the file_name parameter 
                of the files list call.
            filter_file_revisions: string - Check for new message where a new 
                revision of a given file is attached. The value should be a 
                file_id, see getting file revisions for more info.
            filter_folder_added: string - Check for messages filed in a given 
                folder. On Gmail, this is equivalent to having a label applied 
                to a message. The value should be the complete name (including 
                parents if applicable) of the folder you want to track.
            filter_folder_removed: string - Check for messages removed from a 
                given folder. On Gmail, this is equivalent to having a label 
                removed from a message. The value should be the complete name 
                (including parents if applicable) of the folder you want to 
                track.
            include_body: integer - Set to 1 to include the message body in 
                the result. Since the body must be retrieved from the IMAP 
                server, expect a performance hit when setting this parameter.
            body_type: string - Used when include_body is set to get only body 
                parts of a given MIME-type (for example text/html)
            sync_period: string - Desired maximum delay between the moment the 
                email comes in the user's mailbox and the time we call the 
                callback_url. To have your callback_url called as soon as 
                possible (typically, this means within a minute after the 
                event occurred in the mailbox), set this parameter to 
                immediate or 0. Other possible values are 30m, 1h, 4h, 12h and 
                24h (default) meaning 30 minutes, 1 hour, 4 hours, 12 hours 
                and 24 hours respectively.
        
        Returns:
            A mostly empty WebHook object if successful, or False
        """
        req_args = ['callback_url', 'failure_notif_url']
        all_args = [
            'callback_url', 'failure_notif_url', 'filter_to', 'filter_from', 
            'filter_cc', 'filter_subject', 'filter_thread', 
            'filter_new_important', 'filter_file_name', 'filter_folder_added', 
            'filter_folder_removed', 'include_body', 'body_type', 'sync_period'
        ]
        
        params = Resource.sanitize_params(params, all_args, req_args)
        
        data = self._request_uri('webhooks', method='POST', params=params)
        status = bool(data['success'])
        
        if status:
            return WebHook(self, {'webhook_id': data['webhook_id']})
        else:
            return False


class Contact(Resource):
    """Class to represent the Contact resource.
    
    Properties:
        emails: list of strings (email) - Array of email addresses for this 
            contact
        name: string - Full name of contact
        thumbnail: string (url) - URL pointing to Gravatar image associated to 
            contact's email address, if applicable
        last_received: integer - Unix timestamp of date the last message was 
            received
        last_sent: integer - Unix timestamp of date the last message was sent
        count: integer - Number of emails exchanged with this contact
        email: string (email) - one of the contact's email addresses
    """
    keys = ['emails', 'name', 'thumbnail', 'last_received', 'last_sent', 
        'count', 'email']

    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: Account object - parent is an Account object.
            defn: a dictionary of parameters. The 'email' parameter is 
                required to make method calls.
        """
        super(Contact, self).__init__(parent, 'contacts/{email}',  defn)
        
        # if emails == None, populate with email
        if 'email' in defn:
            if defn['email']:
                if 'emails' not in defn:
                    self.emails = [defn['email']]
                elif not defn['emails']:
                    self.emails = [defn['email']]
        
        # if email == None, populate with 1st list item from emails
        if 'emails' in defn:
            if defn['emails']:
                if 'email' not in defn:
                    self.email = defn['email'][0]
                elif not defn['email']:
                    self.email = defn['email'][0]

    def get(self):
        """Retrieves information about given contact.
        
        Documentation: http://context.io/docs/2.0/accounts/contacts#id-get
        
        Arguments:
            None
        
        Returns:
            True if self is updated, else will throw a request error
        """
        # since the data returned doesn't have an email key, add it from emails
        data = self._request_uri('')
        if 'emails' in data:
            if data['emails']:
                data['email'] = data['emails'][0]

        self.__init__(self.parent, data)
        return True

    def get_files(self, **params):
        """List files exchanges with a contact.
        
        Documentation: http://context.io/docs/2.0/accounts/contacts/files#get
        
        Optional Arguments:
            limit: integer - The maximum number of results to return.
            offset: integer - Start the list at this offset (zero-based).
        
        Returns:
            A list of File objects
        """
        all_args = ['limit', 'offset']
        params = Resource.sanitize_params(params, all_args)
        
        return [File(self.parent, obj) for obj in self._request_uri(
            'files', params=params
        )]

    def get_messages(self, **params):
        """List messages where a contact is present.
        
        Documentation: 
            http://context.io/docs/2.0/accounts/contacts/messages#get
        
        Optional Arguments:
            limit: integer - The maximum number of results to return.
            offset: integer - Start the list at this offset (zero-based).
        
        Returns:
            A list of Message objects
        """
        all_args = ['limit', 'offset']
        params = Resource.sanitize_params(params, all_args)
        
        return [Message(self.parent, obj) for obj in self._request_uri(
            'messages', params=params
        )]

    def get_threads(self, **params):
        """List threads where contact is present.
        
        Documentation: http://context.io/docs/2.0/accounts/contacts/threads#get
        
        Optional Arguments:
            limit: integer - The maximum number of results to return.
            offset: integer - Start the list at this offset (zero-based).
        
        Returns:
            A list of Thread objects.
        """
        all_args = ['limit', 'offset']
        params = Resource.sanitize_params(params, all_args)
        
        thread_urls = self._request_uri('threads', params=params)
        objs = []
        
        # isolate just the gmail_thread_id so we can instantiate Thread objects
        for thread_url in thread_urls:
            url_components = thread_url.split('/')
            objs.append({'gmail_thread_id': url_components[-1]})
        
        return [Thread(self.parent, obj) for obj in objs]


class EmailAddress(Resource):
    """Class to represent the EmailAddress resource.
    
    Properties:
        email: string - Email address associated to an account.
        validated: integer - Unix timestamp of email address validation time
        primary: integer - whether or not this address is the primary one 
            associated to the account. 1 for yes, 0 for no.
    """
    keys = ['email', 'validated', 'primary']
    
    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: Account object - parent is an Account object.
            defn: a dictionary of parameters. The 'email' parameter is 
                required to make method calls.
        """
        # be sure that the email key exists in defn
        if 'email_address' in defn:
            defn['email'] = defn['email_address']
        
        super(EmailAddress, self).__init__(
            parent, 'email_addresses/{email}', defn
        )
    
    def get(self):
        """GET details for a given email address.
        
        GET method for the email_addresses resource.
        
        Documentation: 
            http://context.io/docs/2.0/accounts/email_addresses#id-get
        
        Arguments:
            None
            
        Returns:
            True if self is updated, else will throw a request error
        """
        self.__init__(self.parent, self._request_uri(''))
        return True
    
    def post(self, **params):
        """Modifies a given email address.
        
        POST method for the email_addresses resource.
        
        Documentation: 
            http://context.io/docs/2.0/accounts/email_addresses#id-post
        
        Optional Arguments:
            primary: int - Set to 1 to make this email address the primary one 
                for the account
        
        Returns:
            Bool
        """
        all_args = ['primary', ]
        params = Resource.sanitize_params(params, all_args)
        
        # update EmailAddress object with new values
        if 'primary' in params:
            self.primary = params['primary']
        
        status = self._request_uri('', method='POST', params=params)
        return bool(status['success'])
    
    def delete(self):
        """Remove a given email address.
    
        DELETE method for the email_addresses resource.
    
        Documentation: http://context.io/docs/2.0/accounts/email_addresses#id-delete
    
        Arguments:
            None
    
        Returns:
            Bool
        """
        status = self._request_uri('', method='DELETE')
        return bool(status['success'])


class File(Resource):
    """Class to represent the File resource.
    
    Properties:
        size: integer - size of file in bytes.
        type: string - MIME type as specified in message source
        subject: string - Subject line of message this file is attached to
        date: integer - Unix timestamp of the message
        date_indexed: integer - Time this message was first seen by Context.IO 
            (unix timestamp)
        addresses: dict - Email addresses and names of sender and recipients
        person_info: dict - Additional info about contacts on the message
        file_name: string - Name of file
        file_name_structure: list - Name of the file broken down in semantic 
            parts
        body_section: integer - IME section this file can be found in 
            (useful only if you're parsing raw source)
        file_id: string - Unique and persistent id for this file
        supports_preview: bool - whether or not the file supports our preview 
            function
        is_embedded: bool - Indicates whether this file is an object embedded 
            in the message or not
        content_disposition: string - Value of the Content-Disposition header 
            of the MIME part containing this file, if specified. Typically 
            'inline' or 'attachment'
        content_id: string - If this file is an embedded object, this is the 
            value of the Content-Id header of the MIME part containing this 
            file
        message_id: string - Context.IO id of the message this file is 
            attached to
        email_message_id: string - Value of RFC-822 Message-ID header this 
            file is attached to
        gmail_message_id: string - Gmail message id the file is attached to 
            (only present if source is a Gmail account)
        gmail_thread_id: string - Gmail thread id the file is attached to 
            (only present if source is a Gmail account)
        similarity: float - only present when using the related call -
            similarity factor of the file's name.
        supports_diff: bool - only present when using the revisions call - 
            whether or not the file changes with this file can be obtained
        """
    keys = ['size', 'type', 'subject', 'date', 'date_indexed', 'addresses', 
        'person_info', 'file_name', 'file_name_structure', 'body_section', 
        'file_id', 'supports_preview', 'is_embedded', 'content_disposition',
        'content_id', 'message_id', 'email_message_id', 'gmail_message_id', 
        'gmail_thread_id', 'similarity', 'supports_diff']

    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: Account object - parent is an Account object.
            defn: a dictionary of parameters. The 'file_id' parameter is 
                required to make method calls.
        """
        
        super(File, self).__init__(parent, 'files/{file_id}', defn)

    def get(self):
        """GET details for a given file.
        
        GET method for the files resource.
        
        Documentation: http://context.io/docs/2.0/accounts/files#id-get
        
        Arguments:
            None
            
        Returns:
            True if self is updated, else will throw a request error
        """
        self.__init__(self.parent, self._request_uri(''))
        return True

    def get_content(self, download_link=False):
        """Download a file.
        
        Documentation: http://context.io/docs/2.0/accounts/files/content
        
        Optional Arguments:
            download_link: bool - False by default, if True, returns a link 
                rather than the file
        
        Returns:
            Binary if getting content, String if getting download url
        """
        if download_link:
            headers = {
                'Accept': 'text/uri-list'
            }
        else:
            headers = {}

        return self._request_uri('content', headers=headers)

    def get_related(self):
        """Get list of other files related to a given file.
        
        Documentation: http://context.io/docs/2.0/accounts/files/related#get
        
        Arguments:
            None
        
        Returns:
            A list of File objects.
        """
        return [File(self, obj) for obj in self._request_uri('related')]

    def get_revisions(self):
        """Get list of other revisions of a given file.
        
        Documentation: http://context.io/docs/2.0/accounts/files/revisions#get
        
        Arguments:
            None
        
        Returns:
            A list of File objects.
        """
        return [File(self, obj) for obj in self._request_uri('revisions')]


class Message(Resource):
    """Class to represent the Message resource.
    
    Properties:
        date: integer - Unix timestamp of message date
        date_indexed: integer (unix timestamp) - Time this message was first 
            seen by Context.IO
        addresses: dict - Email addresses and names of sender and recipients
        person_info: dict - Additional info about contacts on this message
        email_message_id: string - Value of RFC-822 Message-ID header
        message_id: string - Unique and persistent id assigned by Context.IO 
            to the message
        gmail_message_id: string - Message id assigned by Gmail (only present 
            if source is a Gmail account)
        gmail_thread_id: string - Thread id assigned by Gmail (only present if 
            source is a Gmail account)
        files: list of File objects
        subject: string - Subject of the message
        folders: list - List of folders (or Gmail labels) this message is 
            found in
        sources: list of dicts
        body: list of dicts - Each dict represents a MIME part.
        flags: dict - the flags for this message
        folders: dict - the folders this message is in
        source: string - the raw email source
        thread: Thread object - the thread this message is in, includes other 
            messages in the thread
    """
    keys = ['date', 'date_indexed', 'addresses', 'person_info', 
        'email_message_id', 'message_id', 'gmail_message_id', 
        'gmail_thread_id', 'files', 'subject', 'folders', 'sources',
        'list_headers', 'facebook_headers']
    
    # set empty properties that will get populated by the get methods
    body = None
    flags = None
    folders = None
    headers = None
    source = None
    thread = None

    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: Account object - parent is an Account object.
            defn: a dictionary of parameters. The 'message_id' parameter is 
                required to make method calls.
        """
        
        super(Message, self).__init__(parent, 'messages/{message_id}', defn)

        if 'files' in defn:
            self.files = [File(self.parent, file) for file in defn['files']]
        
        # some calls optionally return a message with some extra data
        if 'body' in defn:
            self.body = defn['body']
        if 'flags' in defn:
            self.flags = defn['flags']
        if 'headers' in defn:
            self.headers = defn['headers']
    
    def get(self, **params):
        """Get file, contact and other information about a given email message.
        
        Documentation: http://context.io/docs/2.0/accounts/messages#id-get
        
        Optional Arguments:
            include_body: integer - Set to 1 to include the message body in 
                the result. Since the body must be retrieved from the IMAP 
                server, expect a performance hit when setting this parameter.
            include_headers: mixed - Can be set to 0 (default), 1 or raw. If 
                set to 1, complete message headers, parsed into an array, are 
                included in the results. If set to raw, the headers are also 
                included but as a raw unparsed string. Since full original 
                headers bodies must be retrieved from the IMAP server, expect 
                a performance hit when setting this parameter.
            include_flags: integer - Set to 1 to include IMAP flags for this 
                message in the result. Since message flags must be retrieved 
                from the IMAP server, expect a performance hit when setting 
                this parameter.
            body_type: string - Used when include_body is set to get only body 
                parts of a given MIME-type (for example text/html)
        
        Returns:
            True if self is updated, else will throw a request error
        """
        all_args = ['include_body', 'include_headers', 'include_flags', 
            'body_type']
        params = Resource.sanitize_params(params, all_args)
        
        self.__init__(self.parent, self._request_uri('', params=params))
        return True
        
    def post(self, **params):
        """Copy or move a message.
        
        Documentation: http://context.io/docs/2.0/accounts/messages#id-post
        
        Required Arguments:
            dst_folder: string - The folder within dst_source the message 
                should be copied to
        
        Optional Arguments:
            dst_source: string - Label of the source you want the message 
                copied to. This field is required if you're moving a message 
                that already exists in one source of the account to another 
                source of that account. If you only want to move the message 
                to a different folder within the same source, dst_folder is 
                sufficient.
            move: integer - By default, this calls copies the original message 
                in the destination. Set this parameter to 1 to move instead of 
                copy.
            dst_label: string - if copying between sources, you MUST use this 
                parameter to identify the source you want to move/copy the 
                message to
            return_bool: bool - True by default. If set to false, returns a 
                dict that includes "connection_log" which contains additional 
                info from the IMAP server if the call failed.
        
        Returns:
            Bool, unless return_bool parameter is set to False, then returns 
                dict
        """
        if 'return_bool' in params:
            return_bool = params['return_bool']
            # so sanitize params doesn't complain about an extra arg
            del params['return_bool']
        else:
            # return default True value
            return_bool = True
        
        req_args = ['dst_folder', ]
        all_args = ['dst_folder', 'dst_source', 'move', 'dst_label']
        params = Resource.sanitize_params(params, all_args, req_args)

        status = self._request_uri('', method='POST', params=params)

        if return_bool:
            return bool(status['success'])
        else:
            return status

    def delete(self):
        """Delete a message.
        
        Documentation: http://context.io/docs/2.0/accounts/messages#id-delete
        
        Arguments:
            None
        Returns:
            Bool
        """
        status = self._request_uri('', method='DELETE')
        return bool(status['success'])

    def get_body(self, **params):
        """Fetch the message body of a given email.
        
        This method sets self.body, and returns a data structure.
        
        Documentation: http://context.io/docs/2.0/accounts/messages/body#get
        
        Optional Arguments:
            type: string - Many emails are sent with both rich text and plain 
                text versions in the message body and by default, the response 
                of this call will include both. It is possible to only get 
                either the plain or rich text version by setting the type 
                parameter to text/plain or text/html respectively.
        
        Returns:
            a list of dictionaries, data format below
            
            [
              {
                "type": string - MIME type of message part being fetched,
                "charset": string - encoding of the characters in the part of 
                    message,
                "content": string - the actual content of the message part 
                    being pulled,
                "body_section": number - indicating position of the part in 
                    the body structure,
              }
            ]
        """
        all_args = ['type', ]
        params = Resource.sanitize_params(params, all_args)
        self.body = self._request_uri('body', params=params)
        return self.body
    
    def get_flags(self):
        """Get message flags.
        
        This method sets self.flags, and returns a data structure.
        
        Documentation: http://context.io/docs/2.0/accounts/messages/flags#get
        
        Arguments:
            None
        
        Returns:
            A dictionary, data format below
            
            {
              "seen": boolean - whether or not a message has been viewed,
              "answered": boolean - whether or not a message has been 
                  replied to,
              "flagged": boolean - whether or not a message has been flagged,
              "deleted": boolean - whether or not a message has been deleted,
              "draft": boolean - whether or not a message is in draft mode,
              "nonjunk": boolean - whether or not a message has been flagged 
                  as "junk" mail,
            }
        """
        self.flags = self._request_uri('flags')
        return self.flags
        
    
    def post_flag(self, **params):
        """Set message flags for a given email.
        
        Also, populates/updates self.flags with the new data.
        
        Optional Arguments:
            seen: integer - Message has been read. Set this parameter to 1 to 
                set the flag, 0 to unset it.
            answered: integer - Message has been answered. Set this parameter 
                to 1 to set the flag, 0 to unset it.
            flagged: integer - Message is "flagged" for urgent/special 
                attention. Set this parameter to 1 to set the flag, 0 to unset 
                it.
            deleted: integer - Message is "deleted" for later removal. An 
                alternative way of deleting messages is to move it to the 
                Trash folder. Set this parameter to 1 to set the flag, 0 to 
                unset it.
            draft: integer - Message has not completed composition (marked as 
                a draft). Set this parameter to 1 to set the flag, 0 to unset 
                it.
        
        Returns:
            Bool, after setting self.flags.
        """
        all_args = ['seen', 'answered', 'flagged', 'deleted', 'draft']
        params = Resource.sanitize_params(params, all_args)
        
        data = self._request_uri('flags', method='POST', params=params)
        status = bool(data['success'])
        
        if status:
            self.flags = data['flags']
        
        return status
        
    def get_folders(self):
        """List of folders a message is in.
        
        This method sets self.folders, and returns a data structure.
        
        Documentation: http://context.io/docs/2.0/accounts/messages/folders#get
        
        Arguments:
            None
        
        Returns:
            A list of dicts, data format below.
        
            [
              {
                "name": string - Name of an IMAP folder, 
                "symbolic_name": string - Special-use attribute of this folder 
                    (if and only if the server supports it and applicable to 
                    this folder)
              }, 
              ...
            ]
        """
        self.folders = self._request_uri('folders')
        return self.folders
    
    def post_folder(self, **params):
        """Edits the folders a message is in.
        
        This call supports adding and/or removing more than one folder 
            simultaneously using the [] suffix to the parameter name.
        
        Documentation: 
            http://context.io/docs/2.0/accounts/messages/folders#post
        
        Optional Arguments:
            add: string - New folder this message should appear in.
            remove: string - Folder this message should be removed from.
        
        Returns:
            Bool
        """
        all_args = ['add', 'remove', 'add[]', 'remove[]']
        params = Resource.sanitize_params(params, all_args)
        status = self._request_uri('folders', method='POST', params=params)
        return bool(status['success'])
    
    def put_folders(self, body):
        """Set folders a message should be in.
        
        Documentation: http://context.io/docs/2.0/accounts/messages/folders#put
        
        Required Arguments:
            body: string - The format of the request body follows the format 
                of the GET response above with the exception that you only 
                need to specify either the name or symbolic_name property for 
                each folder the message must appear in. As shown in the 
                example below, if you want to set folders using the symbolic 
                names as returned by the XLIST command, make sure you escape 
                the \ character.
                
                [{"name":"my personal label"},{"symbolic_name":"\\Starred"},
                {"name":"parent folder/child folder"}]
        
        Returns:
            Bool
        """
        status = self._request_uri('folders', method='PUT', body=body)
        status = bool(status['success'])
        
        if status:
            self.folders = body
        
        return status
    
    def get_headers(self, **params):
        """Get complete headers for a message.
        
        Documentation: http://context.io/docs/2.0/accounts/messages/headers#get
        
        Optional Arguments:
            raw: integer - By default, this returns messages headers parsed 
                into an array. Set this parameter to 1 to get raw unparsed 
                headers.
        
        Returns:
            Dict, data structure below.
            
            {
              Name-Of-Header: array - Values for that header (some headers can 
                  appear more than once in the message source),
              ...
            }
        """
        all_args = ['raw', ]
        params = Resource.sanitize_params(params, all_args)
        self.headers = self._request_uri('headers', params=params)
        return self.headers
    
    def get_source(self):
        """Get the message source.
        
        Documentation: http://context.io/docs/2.0/accounts/messages/source#get
        
        Arguments:
            None
        
        Returns:
            string - raw RFC-822 message
        """
        self.source = self._request_uri('source')
        return self.source
    
    def get_thread(self, **params):
        """List other messages in the same thread as this message.
        
        Documentation: http://context.io/docs/2.0/accounts/messages/thread#get
        
        Optional Arguments:
            include_body: integer - Set to 1 to include message bodies in the 
                result. Since message bodies must be retrieved from the IMAP 
                server, expect a performance hit when setting this parameter.
            include_headers: mixed - Can be set to 0 (default), 1 or raw. If 
                set to 1, complete message headers, parsed into an array, are 
                included in the results. If set to raw, the headers are also 
                included but as a raw unparsed string. Since full original 
                headers bodies must be retrieved from the IMAP server, expect 
                a performance hit when setting this parameter.
            include_flags: integer - Set to 1 to include IMAP flags of 
                messages in the result. Since message flags must be retrieved 
                from the IMAP server, expect a performance hit when setting 
                this parameter.
            body_type: string - Used when include_body is set to get only body 
                parts of a given MIME-type (for example text/html)
            limit: integer - The maximum number of messages to include in the 
                messages property of the response.
            offset: integer - Start the list of messages at this offset 
                (zero-based).
        
        Returns:
            a Thread object. Unless we can't find a thread id, then just the 
                response
        """
        all_args = [
            'include_body', 'include_headers', 'include_flags', 'body_type', 
            'limit', 'offset'
        ]
        params = Resource.sanitize_params(params, all_args)
        
        data = self._request_uri('thread', params=params)
        
        # try to find the gmail_thread_id
        if data['messages']:
            if data['messages'][0]['gmail_thread_id']:
                data['gmail_thread_id'] = 'gm-%s' % (
                    data['messages'][0]['gmail_thread_id']
                )
        
        # if we have a gmail_thread_id, then return a thread object, if not
        # return the raw data
        if 'gmail_thread_id' in data:
            self.thread = Thread(self.parent, data)
        else:
            self.thread = data
        
        # if we have the subject, set thread.subject
        if self.subject and self.thread:
            self.thread.subject = self.subject
        
        return self.thread


class Source(Resource):
    """Class to represent the Source resource.
    
    Properties:
        username: string - The username used to authentify an IMAP connection. 
            On some servers, this is the same thing as the primary email 
            address.
        status: string - If the status of the source is TEMP_DISABLED or 
            DISABLED. You can do a POST/PUT with status set to 1 to reset it.
        service_level: string - Changes the service level for the source. 
            Possible values are PRO and BASIC.
        type: string - Currently, the only supported type is IMAP
        label: string - The label property of the source instance. You can use 
            0 as an alias for the first source of an account.
        authentication_type: string - what method was used to authenticate the 
            source.
        use_ssl: integer - Set to 1 if you want SSL encryption to be used when 
            opening connections to the IMAP server. Any other value will be 
            considered as "do not use SSL"
        resource_url: string (url) - Complete url of the source.
        server: string - Name of IP of the IMAP server, eg. imap.gmail.com
        sync_period: string - Changes the period at which the Context.IO index 
            for this source is synced with the origin email account on the 
            IMAP server. Possible values are 1h, 4h, 12h and 24h (default).
        port: integer - Port number to connect to on the server. Keep in mind 
            that most IMAP servers will have one port for standard connection 
            and another one for encrypted connection (see use-ssl parameter 
            above)
    """
    keys = ['username', 'status', 'service_level', 'type', 'label', 
        'authentication_type', 'use_ssl', 'resource_url', 'server', 
        'sync_period', 'port'
    ]

    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: Account object - parent is an Account object.
            defn: a dictionary of parameters. The 'label' parameter is 
                required to make method calls.
        """
        
        super(Source, self).__init__(parent, 'sources/{label}',  defn)

    def get(self):
        """Get parameters and status for an IMAP source.
        
        Documentation: http://context.io/docs/2.0/accounts/sources#id-get
        
        Arguments:
            None
        
        Returns:
            True if self is updated, else will throw a request error
        """
        self.__init__(self.parent, self._request_uri(''))
        return True
    
    def delete(self):
        """Delete a data source for an account.
        
        Documentation: http://context.io/docs/2.0/accounts/sources#id-delete
        
        Arguments:
            None
        
        Returns:
            Bool
        """
        status = self._request_uri('', method='DELETE')
        return bool(status['success'])
    
    def post(self, **params):
        """Update a data source for an account.
        
        Documentation: http://context.io/docs/2.0/accounts/sources#id-post
        
        Optional Arguments:
            status: integer - If the status of the source is TEMP_DISABLED or 
                DISABLED. You can do a POST/PUT with status set to 1 to reset 
                it.
            force_status_check: integer - Creates an IMAP connection and 
                resets the source status to to one reported by the IMAP
                backend. Don't combine this with other parameters.
            sync_period: string - Changes the period at which the Context.IO 
                index for this source is synced with the origin email account 
                on the IMAP server. Possible values are 1h, 4h, 12h and 24h 
                (default).
            password: string - New password for this source. Ignored if any of 
                the provider_* parameters are set below.
            provider_token: string - An OAuth token obtained from the IMAP 
                account provider to be used to authentify on this email 
                account.
            provider_token_secret: string - An OAuth token secret obtained 
                from the IMAP account provider to be used to authentify on 
                this email account.
            provider_consumer_key: string - The OAuth consumer key used to 
                obtain the the token and token secret above for that account. 
                That consumer key and secret must be configured in your 
                Context.IO account
        
        Returns:
            Bool
        """
        all_args = ['status', 'force_status_check', 'sync_period', 
            'password', 'provider_token', 'provider_token_secret', 
            'provider_consumer_key'
        ]
        params = Resource.sanitize_params(params, all_args)
        
        status = self._request_uri('', method='POST', params=params)
        return bool(status['success'])

    def get_folders(self, **params):
        """Get list of folders in an IMAP source.
        
        Documentation: http://context.io/docs/2.0/accounts/sources/folders#get
        
        Optional Arguments:
            include_extended_counts: integer - 
        
        Returns:
            A list of Folder objects.
        """
        all_args = ['include_extended_counts', ]
        params = Resource.sanitize_params(params, all_args)
        
        return [Folder(self, obj) for obj in self._request_uri(
            'folders', params=params
        )]
    
    def get_sync(self):
        """Get sync status of a data source.
        
        Documentation: http://context.io/docs/2.0/accounts/sources/sync#get
        
        Arguments:
            None
        
        Returns:
            A dictionary, data format below
            
            {
                'Source.label': {
                    'last_sync_start': UNIX TIME STAMP (int), 
                    'last_sync_stop': UNIX TIME STAMP (int), 
                    'last_expunge': UNIX TIME STAMP (int), 
                    'initial_import_finished': BOOL
                }
            }
        """
        return self._request_uri('sync')
    
    def post_sync(self):
        """Trigger a sync of a data source.
        
        Documentation: http://context.io/docs/2.0/accounts/sources/sync#post
        
        Arguments:
            None
        
        Returns
            a dictionary, data format below
            
            {
                'syncsQueued': LIST of syncs queued, 
                'syncs_queued': LIST of syncs queued, 
                'resource_url': STRING, complete url of resource, 
                'success': BOOL, 
                'label': STRING, source label
            }
        """
        return self._request_uri('sync', method='POST')


class ConnectToken(Resource):
    """Class to represent the connect_token resource.
    
    Properties:
        token: string - Id of the connect_token
        email: string - email address specified on token creation
        created: integer - Unix timestamp of the connect_token was created
        used: integer - Unix time this token was been used. 0 means it no 
            account has been created with this token yet
        expires: mixed - Unix time this token will expire and be purged. Once 
            the token is used, this property will be set to false
        callback_url: string - URL of your app we'll redirect the browser to 
            when the account is created
        first_name: string - First name specified on token creation
        last_name: string - Last name specified on token creation
        account: Account object
    """
    keys = ['token', 'email', 'created', 'used', 'expires', 'callback_url', 
        'first_name', 'last_name', 'account']

    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: ContextIO object - parent is an ContextIO object.
            defn: a dictionary of parameters. The 'token' parameter is 
                required to make method calls.
        """
        
        super(ConnectToken, self).__init__(
            parent, 'connect_tokens/{token}', defn
        )
        
        if 'account' in defn:
            if defn['account']:
                self.account = Account(self.parent, defn['account'])

    def get(self):
        """Information about a given connect token.
        
        Documentation: 
            http://context.io/docs/2.0/accounts/connect_tokens#id-get
        
        Arguments:
            None
        
        Returns:
            True if self is updated, else will throw a request error
        """
        self.__init__(self.parent, self._request_uri(''))
        return True
    
    def delete(self):
        """Remove a given connect token.
        
        Documentation: 
            http://context.io/docs/2.0/accounts/connect_tokens#id-delete
        
        Arguments:
            None
        
        Returns:
            Bool
        """
        status = self._request_uri('', method='DELETE')
        return bool(status['success'])

class Discovery(Resource):
    """Class to represent the Discovery resource.
    
    Properties:
        email: string - The email address requested for discovery
        found: bool - true if settings were found, false otherwise
        type: string - Type of provider, (eg. "gmail")
        imap: dict - information about the imap server, data format below
            "imap": {
                "server": string - FQDN of the IMAP server,
                "username": string - What the username should be for 
                    authentication,
                "port": number - Network port IMAP server is listening on,
                "use_ssl": boolean - Whether that server:port uses SSL 
                    encrypted connections,
                "oauth": boolean - true if the IMAP server support 
                    authentication through OAuth (setting related OAuth 
                    consumers)
              }
        documentation: list - List of documentation pages that may be useful 
            for end-users for this specific IMAP provider
    """
    keys = ['email', 'found', 'type', 'imap', 'documentation']
    
    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: ContextIO object - parent is an ContextIO object.
            defn: a dictionary of parameters.
        """
        super(Discovery, self).__init__(parent, 'discovery', defn)


class Folder(Resource):
    """Class to represent the Folder resource.
    
    Properties:
        name: string - Name of the folder
        attributes: dictinary - IMAP Attributes of the folder given as a hash
        delim: string - Character used to delimite hierarchy in the folder name
        nb_messages: integer - Number of messages found in this folder
        nb_unseen_messages: integer - Number of unread messages in this folder 
            (present only if include_extended_counts is set to 1)
    """
    keys = ['name', 'attributes', 'delim', 'nb_messages', 'nb_unseen_messages']
    
    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: Source object - parent is an Source object.
            defn: a dictionary of parameters. The 'name' parameter is 
                required to make method calls.
        """
        super(Folder, self).__init__(parent, 'folders/{name}', defn)

    def put(self, **params):
        """Create a folder on an IMAP source.
        
        Documentation: 
            http://context.io/docs/2.0/accounts/sources/folders#id-put
        
        Optional Arguments:
            delim: string - If / isn't fancy enough as a hierarchy delimiter 
                when specifying the folder you want to create, you're free to 
                use what you want, just make sure you set this delim parameter 
                to tell us what you're using.
        
        Returns:
            Bool
        """
        all_args = ['delim', ]
        params = Resource.sanitize_params(params, all_args)
        status = self._request_uri('', method='PUT')
        return bool(status['success'])

    def delete(self):
        """Remove a given folder.
        
        DELETE method for the folder resource.
        
        Documentation: 
        
        Arguments:
            None
        
        Returns:
            Bool
        """
        status = self._request_uri('', method='DELETE')
        return bool(status['success'])

    def get_messages(self, **params):
        """Get current listings of email messages in a given folder.
        
        NOTE: this gets all messages including since last sync. It's fresher, 
            but expect slower performance than using Account.get_messages()
        
        Documentation: 
            http://context.io/docs/2.0/accounts/sources/folders/messages#get
        
        Optional Arguments:
            include_body: integer - Set to 1 to include message bodies in the 
                result. Since message bodies must be retrieved from the IMAP 
                server, expect a performance hit when setting this parameter.
            body_type: string - Used when include_body is set to get only body 
                parts of a given MIME-type (for example text/html)
            include_headers: mixed - Can be set to 0 (default), 1 or raw. If 
                set to 1, complete message headers, parsed into an array, are 
                included in the results. If set to raw, the headers are also 
                included but as a raw unparsed string. Since full original 
                headers bodies must be retrieved from the IMAP server, expect 
                a performance hit when setting this parameter.
            include_flags: integer - Set to 1 to include IMAP flags for this 
                message in the result. Since message flags must be retrieved 
                from the IMAP server, expect a performance hit when setting 
                this parameter.
            flag_seen: integer - Set to 1 to restrict list to messages having 
                the \Seen flag set, set to 0 to have the messages with that 
                flag unset (ie. list unread messages in the folder).
            limit: integer - The maximum number of results to return.
            offset: integer - Start the list at this offset (zero-based).
        
        Returns:
            a list of Message objects.
        """
        all_args = ['include_body', 
            'body_type', 'include_headers', 'include_flags', 'flag_seen', 
            'limit', 'offset'
        ]
        params = Resource.sanitize_params(params, all_args)
        
        return [Message(self.parent.parent, obj) for obj in self._request_uri(
            'messages', params=params
        )]


class Thread(Resource):
    """Class to represent the thread resource.
    
    Properties:
        gmail_thread_id: string - Thread id assigned by Gmail (only present if 
            source is a Gmail account)
        email_message_ids: list of strings - List of email_message_ids forming 
            the thread
        person_info: dict - Additional info about contacts on this message
        messages: list of Message objects
        subject: string - Subject of the message
        folders: list - List of folders (or Gmail labels) this message is 
            found in
        sources: list of Source objects
    """
    keys = ['gmail_thread_id', 'email_message_ids', 'person_info', 'messages', 
        'subject', 'folders', 'sources'
    ]
    
    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: Account object - parent is an Account object.
            defn: a dictionary of parameters. The 'gmail_thread_id' parameter 
                is required to make method calls.
        """
        super(Thread, self).__init__(parent, 'threads/{gmail_thread_id}', defn)
        
        if 'messages' in defn:
            self.messages = [
                Message(self.parent, message) for message in defn['messages']
            ]
        
        if 'sources' in defn:
            self.sources = [
                Source(self.parent, source) for source in defn['sources']
            ]
    
    def get(self, **params):
        """Returns files, contacts, and messages on a given thread.
    
        Documentation: http://context.io/docs/2.0/accounts/threads#id-get
        
        Optional Arguments:
            include_body: integer - Set to 1 to include message bodies in the 
                result. Since message bodies must be retrieved from the IMAP 
                server, expect a performance hit when setting this parameter.
            include_headers: mixed - Can be set to 0 (default), 1 or raw. If 
                set to 1, complete message headers, parsed into an array, are 
                included in the results. If set to raw, the headers are also 
                included but as a raw unparsed string. Since full original 
                headers bodies must be retrieved from the IMAP server, expect 
                a performance hit when setting this parameter.
            include_flags: integer - Set to 1 to include IMAP flags of 
                messages in the result. Since message flags must be retrieved 
                from the IMAP server, expect a performance hit when setting 
                this parameter.
            body_type: string - Used when include_body is set to get only body 
                parts of a given MIME-type (for example text/html)
            limit: integer - The maximum number of messages to include in the 
                messages property of the response.
            offset: integer - Start the list of messages at this offset 
                (zero-based).
    
        Returns:
            True if self is updated, else will throw a request error
        """
        all_args = ['include_body', 
            'include_headers', 'include_flags', 'body_type', 'limit', 'offset'
        ]
        params = Resource.sanitize_params(params, all_args)
        self.__init__(self.parent, self._request_uri('', params=params))
        return True        


class WebHook(Resource):
    """Class to represent the WebHook resource.
    
    Properties:
        callback_url: string - Your callback URL to which we'll POST 
            message data
        failure_notif_url: string - Your callback URL for failure 
            notifications
        active: bool - Whether this webhook is currently applied to 
            new messages we find in the account or not
        failure: bool - true means we're having issues connecting to 
            the account and gave up after a couple retries. The 
            failure_notif_url is called when a webhook's failure 
            property becomes true.
        sync_period: string - Maximum time allowed between the event 
            happening in the mailbox and your callback_url being 
            called
        webhook_id: string - Id of the webhook
        filter_to: string - Check for new messages sent to a given name or 
            email address.
        filter_from: string - Check for new messages received from a given 
            name or email address.
        filter_cc: string - Check for new messages where a given name or 
            email address is cc'ed
        filter_subject: string - Check for new messages with a subject 
            matching a given string or regular expresion
        filter_thread: string - Check for new messages in a given thread. 
            Value can be a gmail_thread_id or the email_message_id or 
            message_id of an existing message currently in the thread.
        filter_new_important: string - Check for new messages 
            automatically tagged as important by the Gmail Priority Inbox 
            algorithm. To trace all messages marked as important 
            (including those manually set by the user), use 
            filter_folder_added with value Important. Note the leading 
            back-slash character in the value, it is required to keep this 
            specific to Gmail Priority Inbox. Otherwise any message placed 
            in a folder called "Important" would trigger the WebHook.
        filter_file_name: string - Check for new messages where a file 
            whose name matches the given string is attached. Supports 
            wildcards and regular expressions like the file_name parameter 
            of the files list call.
        filter_file_revisions: string - Check for new message where a new 
            revision of a given file is attached. The value should be a 
            file_id, see getting file revisions for more info.
        filter_folder_added: string - Check for messages filed in a given 
            folder. On Gmail, this is equivalent to having a label applied 
            to a message. The value should be the complete name (including 
            parents if applicable) of the folder you want to track.
        filter_folder_removed: string - Check for messages removed from a 
            given folder. On Gmail, this is equivalent to having a label 
            removed from a message. The value should be the complete name 
            (including parents if applicable) of the folder you want to 
            track.
    """
    keys = ['callback_url', 'failure_notif_url', 'active', 'failure', 
        'sync_period', 'webhook_id', 'filter_to', 'filter_from', 'filter_cc', 
        'filter_subject', 'filter_thread', 'filter_new_important', 
        'filter_file_name', 'filter_file_revisions', 'filter_folder_added', 
        'filter_folder_removed'
    ]
    
    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: Account object - parent is an Account object.
            defn: a dictionary of parameters. The 'webhook_id' parameter 
                is required to make method calls.
        """
        super(WebHook, self).__init__(parent, 'webhooks/{webhook_id}', defn)
    
    def get(self):
        """Get properties of a given webhook.
        
        Documentation: http://context.io/docs/2.0/accounts/webhooks#id-get
        
        Arguments:
            None
        
        Returns:
            True if self is updated, else will throw a request error
        """
        self.__init__(self.parent, self._request_uri(''))
        return True
    
    def delete(self):
        """Delete a webhook.
        
        Documentation: http://context.io/docs/2.0/accounts/webhooks#id-delete
        
        Arguments:
            None
        
        Returns:
            Bool
        """
        status = self._request_uri('', method='DELETE')
        return bool(status['success'])
    
    def post(self, **params):
        """Change properties of a given WebHook.
        
        Required Arguments:
            active: integer - The active property of a WebHook allows you to 
                pause (set to 0) or resume (set to 1).
        
        Returns:
            Bool
        """
        req_args = ['active', ]
        all_args = ['active', ]
        params = Resource.sanitize_params(params, all_args, req_args)
        status = self._request_uri('', method='POST', params=params)
        return bool(status['success'])
        

class OauthProvider(Resource):
    """Class representation of the OauthProvider resource.

    Properties:
        type: string - Identification of the OAuth provider. This must be 
            either GMAIL and GOOGLEAPPSMARKETPLACE.
        provider_consumer_key: string - The OAuth consumer key
        provider_consumer_secret: string - The OAuth consumer secret
        resource_url: string - full url of the resource
    """
    keys = ['type', 'provider_consumer_key', 'provider_consumer_secret', 
        'resource_url'
    ]
    def __init__(self, parent, defn):
        """Constructor.
        
        Required Arguments:
            parent: ContextIO object - parent is an ContextIO object.
            defn: a dictionary of parameters. The 'provider_consumer_key' 
                parameter is required to make method calls.
        """
        super(OauthProvider, self).__init__(
            parent, 
            'oauth_providers/{provider_consumer_key}', 
            defn
        )

    def get(self):
        """Get information about a given oauth provider.

        Documentation: http://context.io/docs/2.0/oauth_providers#id-get

        Arguments:
            None

        Returns:
            True if self is updated, else will throw a request error
        """
        self.__init__(self.parent, self._request_uri(''))
        return True

    def delete(self):
        """Remove a given oauth provider.

        Documentation: http://context.io/docs/2.0/oauth_providers#id-delete

        Arguments:
            None

        Returns:
            Bool
        """
        status = self._request_uri('', method='DELETE')
        return bool(status['success'])
