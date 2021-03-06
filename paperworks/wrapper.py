# License: MIT
# Author: Nelo Wallus, http://github.com/ntnn

import logging
import json
try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen
from base64 import b64encode

logger = logging.getLogger(__name__)

__version__ = '0.14.1'
api_version = '/api/v1/'
default_agent = 'paperwork.py api wrapper v{}'.format(__version__)

api_path = {
    'notebooks':   'notebooks',
    'notebook':    'notebooks/{}',
    'notes':       'notebooks/{}/notes',
    'note':        'notebooks/{}/notes/{}',
    'move':        'notebooks/{}/notes/{}/move/{}',
    'versions':    'notebooks/{}/notes/{}/versions',
    'version':     'notebooks/{}/notes/{}/versions/{}',
    'attachments': 'notebooks/{}/notes/{}/versions/{}/attachments',
    'attachment':  'notebooks/{}/notes/{}/versions/{}/attachments/{}',
    'tags':        'tags',
    'tag':         'tags/{}',
    'tagged':      'tagged/{}',
    'search':      'search/{}',
    'i18n':        'i18n',
    'i18nkey':     'i18n/{}'
    }


def b64(string):
    """Returns given string as base64 hash-string.

    :type string: str
    :rtype: str
    """
    return b64encode(string.encode('UTF-8')).decode('ASCII')


class api:
    def __init__(self, user_agent=default_agent):
        """Api instance.

        :type user_agent: str
        """
        self.user_agent = user_agent

    def basic_authentication(self, host, user, passwd):
        """Basic authentication with host.

        Returns false if connection fails.
        :type host: str
        :type user: str
        :type passwd: str
        :rtype: bool
        """
        self.host = host if 'http://' in host else 'http://' + host
        self.headers = {
            'Application-Type': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + b64('{}:{}'.format(user, passwd)),
            'Connection': 'keep-alive',
            'User-Agent': self.user_agent
            }
        if self.request(None, 'GET', 'notebooks'):
            return True
        else:
            return False

    def request(self, data, method, keyword, *args):
        """Sends a request to the host and returns the parsed json data
        if successfull.

        :type data: dict
        :type method: str
        :type keyword: str
        :type args: str
        :rtype: dict or None
        """
        try:
            if data:
                data = json.dumps(data).encode('ASCII')
            uri = self.host + api_version + api_path[keyword].format(*args)
            request = Request(uri, data, self.headers)
            request.get_method = lambda: method
            logger.info('{} request to {} with {}'.format(method, uri, data))
            res = urlopen(request)
            json_res = json.loads(res.read().decode('ASCII'))
            if json_res['success'] is False:
                logger.error('Unsuccessful request.')
            else:
                return json_res['response']
        except Exception as e:
            logger.error(e)

    def get(self, keyword, *args):
        """Convenience wrapper for GET request.

        :type keyword: str
        :type *args: str
        :rtype: dict or list or None
        """
        return self.request(None, 'GET', keyword, *args)

    def post(self, data, keyword, *args):
        """Convenience wrapper for POST request.

        :type data: dict
        :type keyword: str
        :type *args: str
        :rtype: dict or list or None
        """
        return self.request(data, 'POST', keyword, *args)

    def put(self, data, keyword, *args):
        """Convenience wrapper for PUT request.

        :type data: dict
        :type keyword: str
        :type *args: str
        :rtype: dict or None
        """
        return self.request(data, 'PUT', keyword, *args)

    def delete(self, keyword, *args):
        """Convenience wrapper for DELETE request.

        :type keyword: str
        :type *args: str
        :rtype: dict or None
        """
        return self.request(None, 'DELETE', keyword, *args)

    def list_notebooks(self):
        """Return all notebooks in a list.

        :rtype: list
        """
        return self.get('notebooks')

    def create_notebook(self, title):
        """Create new notebook with title.

        :type title: str
        :rtype: dict
        """
        return self.post(
            {'type': 0, 'title': title, 'shortcut': ''},
            'notebooks')

    def get_notebook(self, notebook_id):
        """Returns notebook.

        :type notebook_id: int
        :rtype: dict
        """
        return self.get('notebook', notebook_id)

    def update_notebook(self, notebook):
        """Updates notebook.

        :type notebook: dict
        :rtype: dict
        """
        return self.put(notebook, 'notebook', notebook['id'])

    def delete_notebook(self, notebook_id):
        """Deletes notebook and all containing notes.

        :type notebook_id: int
        :rtype: dict
        """
        return self.delete('notebook', notebook_id)

    def list_notebook_notes(self, notebook_id):
        """Returns notes in notebook in a list.

        :type notebook_id: int
        :rtype: list
        """
        return self.get('notes', notebook_id)

    def create_note(self, notebook_id, note_title, content=''):
        """Creates note with note_title in notebook.

        :type notebook_id: int
        :type note_title: str
        :type content: str
        :rtype: dict
        """
        content_preview = content[:15] if len(content) >= 15 else content
        return self.post(
            {'title': note_title,
             'content': content,
             'content_preview': content_preview},
            'notes',
            notebook_id)

    def get_note(self, notebook_id, note_id):
        """Returns note with note_id from notebook with notebook_id.

        :type notebook_id: int
        :type note_id: int
        :rtype: dict
        """
        return self.get_notes(notebook_id, [note_id])

    def get_notes(self, notebook_id, note_ids):
        """Returns note with note_id from notebook with notebook_id.

        :type notebook_id: int
        :type note_ids: list or set or tuple
        :rtype: list
        """
        return self.get('note', notebook_id, ','.join(
            [str(note_id) for note_id in note_ids]))

    def update_note(self, note):
        """Update note.

        :type note: models.Note
        :rtype: dict
        """
        return self.put(note, 'note', note['notebook_id'], note['id'])

    def delete_note(self, note):
        """Delete note.

        :type note: models.Note
        :rtype: dict
        """
        return self.delete_notes([note])[0]

    def delete_notes(self, notes):
        """Delete notes.

        :type note: list
        :rtype: list
        """
        return self.delete('note', notes[0]['notebook_id'], ','.join(
            [str(note['id']) for note in notes]))

    def move_note(self, note, new_notebook_id):
        """Moves note to new_notebook_id.

        :type note: models.Note
        :type new_notebook_id: int
        :rtype: dict
        """
        return self.move_notes([note], new_notebook_id)[0]

    def move_notes(self, notes, new_notebook_id):
        """Moves notes to new_notebook_id.

        :type notes: list
        :type new_notebook_id: int
        :rtype: list
        """
        return self.get('move', notes[0]['notebook_id'], ','.join(
            [str(note['id']) for note in notes]), new_notebook_id)

    def list_note_versions(self, note):
        """Returns a list of versions of given note.

        :type note: models.Note
        :rtype: list
        """
        return self.list_notes_versions([note])

    def list_notes_versions(self, notes):
        """Returns lists of versions of given notes.

        :type notes: list
        :rtype: list
        """
        return self.get('versions', notes[0]['notebook_id'], ','.join(
            [str(note['id']) for note in notes]))

    def get_note_version(self, note, version_id):
        """Returns version with version_id of note.

        :type note: models.Note
        :type version_id: int
        :rtype: dict
        """
        return self.get('version', note['notebook_id'], note['id'], version_id)

    def list_note_attachments(self, note):
        """List attachments of note.

        :type note: models.Note
        :rtype: list
        """
        return self.get(
            'attachments',
            note['notebook_id'],
            note['id'],
            note['versions'][0]['id'])

    def get_note_attachment(self, note, attachment_id):
        """Returns attachment with attachment_id of note.

        :type note: models.Note
        :type attachment_id: int
        :rtype: dict
        """
        return self.get(
            'attachment',
            note['notebook_id'],
            note['id'],
            note['versions'][0]['id'],
            attachment_id)

    def delete_note_attachment(self, note, attachment_id):
        """Deletes attachment with attachment_id on note.

        :type note: models.Note
        :type attachment_id: int
        :rtype: dict
        """
        return self.delete(
            'attachment',
            note['notebook_id'],
            note['id'],
            note['versions'][0]['id'],
            attachment_id)

    def upload_attachment(self, note, attachment):
        pass

    def list_tags(self):
        """Returns all tags.

        :rtype: list
        """
        return self.get('tags')

    def get_tag(self, tag_id):
        """Returns tag with tag_id.

        :type tag_id: int
        :rtype: dict
        """
        return self.get('tag', tag_id)

    def list_tagged(self, tag_id):
        """Returns notes tagged with tag.

        :type tag_id: int
        :rtype: list
        """
        return self.get('tagged', tag_id)

    def search(self, keyword):
        """Search for notes containing given keyword.

        :type keyword: str
        :rtype: list
        """
        return self.get('search', b64(keyword))

    def i18n(self, keyword=None):
        """Returns either the full i18n dict or the requested word.

        :type keyword: str
        :rtype: list or str
        """
        if keyword:
            return self.get('i18nkey', keyword)
        return self.get('i18n')
