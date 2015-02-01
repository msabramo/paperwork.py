from paperworks import wrapper
from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger('models')


class Model:
    def __init__(self, title, id, api):
        self.id = id
        self.title = title
        self.api = api

    def __str__(self):
        return "{}:'{}'".format(self.id, self.title)

    def to_json(self):
        """Return model as json-dict."""
        return {
            'id': self.id,
            'title': self.title
            }

    @classmethod
    def from_json(cls, json):
        """Creates model from json-dict."""
        return cls(
            json['title'],
            json['id']
            )


class Notebook(Model):
    def __init__(self, title, id, api, type=0, updated_at=''):
        super().__init__(title, id, api)
        self.type = type
        self.updated_at = updated_at
        self.notes = {}

    def to_json(self):
        return {
            'type': self.type,
            'id': self.id,
            'title': self.title
            }

    @classmethod
    def from_json(cls, json, api):
        return cls(
            json['title'],
            json['id'],
            api,
            type=json['type'],
            updated_at='')

    @classmethod
    def create(cls, api, title):
        logger.info('Created notebook {}'.format(title))
        return cls.from_json(api.create_notebook(title), api)

    def delete(self):
        """Deletes notebook from remote host."""
        logger.info('Deleting notebook {}'.format(self))
        self.api.delete_notebook(self.id)

    def update(self, force=True):
        """Updates local or remote notebook, depending on time stamp."""
        logger.info('Updating {}'.format(self))
        remote = self.api.get_notebook(self.id)
        if remote is None:
            logger.error('Remote notebook could not be found.'
                         'Wrong id or deleted.')
        elif force or remote['updated_at'] < self.updated_at:
            self.api.update_notebook(self.to_json())
        else:
            logger.info('Remote version is higher.'
                        'Updating local notebook.')
            self.title = remote['title']
            self.updated_at = remote['updated_at']

    def get_notes(self):
        return sorted(self.notes.values(), key=lambda note: note.title)

    def create_note(self, title):
        note = Note.create(title, self)
        self.notes[note.id] = note
        logger.info('Created note {} in notebook {}'.format(note, self))

    def add_note(self, note):
        self.notes[note.id] = note
        logger.info('Added note {} to {}'.format(note, self))

    def download(self, tags):
        notes_json = self.api.list_notebook_notes(self.id)
        logger.info('Downloading notes of notebook {}'.format(self))
        for note_json in notes_json:
            note = Note.from_json(note_json, self)
            self.add_note(note)
            note.add_tags([tags[tag['id']] for tag in note_json['tags']])


class Note(Model):
    def __init__(self, title, id, notebook, content='', updated_at=''):
        super().__init__(title, id, notebook.api)
        self.notebook = notebook
        self.content = content
        self.updated_at = updated_at
        self.tags = set()

    def to_json(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tags': [tag.to_json() for tag in self.tags],
            'notebook_id': self.notebook.id
            }

    @classmethod
    def from_json(cls, json, notebook):
        return cls(
            json['title'],
            json['id'],
            notebook,
            json['content'],
            json['updated_at']
            )

    @classmethod
    def create(cls, title, notebook):
        logger.info('Creating note {} in notebook'.format(title, notebook))
        res = notebook.api.create_note(notebook.id, title)
        return cls(
            title,
            res['id'],
            notebook,
            '',
            res['updated_at']
            )

    def update(self, force=False):
        """Updates local or remote note, depending on timestamp.
        Creates if note id is 0."""
        logger.info('Updating note {}'.format(self))
        remote = self.api.get_note(self.notebook.id, self.id)
        if remote is None:
            logger.error('Remote note could not be found. Wrong id,'
                         'deleted or moved to another notebook')
        elif force or remote['updated_at'] <= self.updated_at:
            logger.info('Remote version is lower or force update.'
                        'Updating remote note.')
            self.updated_at = self.api.update_note(
                self.to_json())['updated_at']
        else:
            logger.info('Remote version is higher. Updating local note.')
            self.title = remote['title']
            self.content = remote['content']
            self.updated_at = remote['updated_at']

    def delete(self):
        logger.info('Deleting note {} in notebook {}'.format(self, self.notebook))
        self.api.delete_note(self.to_json())
        del(self.notebook.notes[self.id])

    def add_tags(self, tags):
        for tag in tags:
            logger.info('Adding tag {} to note {}'.format(tag, self))
            self.tags.add(tag)

    def move_to(self, new_notebook):
        self.api.move_note(self.to_json(), new_notebook.id)
        del(self.notebook.notes[self.id])
        new_notebook.add_note(self)


class Tag(Model):
    def __init__(self, title, id, api, visibility=0):
        super().__init__(title, id, api)
        self.visibility = visibility
        self.notes = set()

    def to_json(self):
        return {
            'id': self.id,
            'title': self.title,
            'visibility': self.visibility
            }

    @classmethod
    def from_json(cls, json, api):
        return cls(
            json['title'],
            json['id'],
            api,
            json['visibility']
            )

    def get_notes(self):
        """Returns notes in a sorted list."""
        return sorted(self.notes, key=lambda note: note.title)


class Paperwork:
    def __init__(self, user, passwd, host):
        self.notebooks = {}
        self.tags = {}
        self.api = wrapper.api()
        self.authenticated = self.api.basic_authentication(host, user, passwd)

    def create_notebook(self, title):
        if title != 'All Notes':
            notebook = Notebook.create(self.api, title)
            self.notebooks[notebook.id] = notebook
            logger.info('Created notebook {}'.format(notebook))

    def add_notebook(self, notebook):
        if notebook.id != 0:
            self.notebooks[notebook.id] = notebook
            logger.info('Added notebook {}'.format(notebook))

    def add_tag(self, tag):
        self.tags[tag.id] = tag
        logger.info('Added tag {}'.format(tag))

    def download(self):
        """Downloading tags, notebooks and notes from host."""
        logger.info('Downloading all')

        logger.info('Downloading tags')
        for tag in self.api.list_tags():
            tag = Tag.from_json(tag, self.api)
            self.tags[tag.id] = tag

        logger.info('Downloading notebooks')
        for notebook in self.api.list_notebooks():
            notebook = Notebook.from_json(notebook, self.api)
            self.notebooks[notebook.id] = notebook
            notebook.download(self.tags)

    def update(self):
        """Updating notebooks and notes to host."""
        logger.info('Updating notebooks and notes')
        for nb in self.notebooks.values():
            nb.update()
            for note in nb.get_notes():
                note.update()

    def find_tag(self, key):
        """Finds tag with key (id or title)."""
        if isinstance(key, str):
            for tag in self.tags.values():
                if key == tag.title:
                    return tag
        else:
            return self.tags[key]

    def find_notebook(self, key):
        """Find notebook with key (id or title)."""
        if isinstance(key, str):
            for nb in self.notebooks.values():
                if key == nb.title:
                    return nb
        else:
            return self.notebooks[key]

    def find_note(self, key):
        """Find note with key (id or title)."""
        for note in self.get_notes():
            if key in (note.id, note.title):
                return note

    def fuzzy_find(self, title, choices):
        """Fuzzy find for title in choices. Returns highest match."""
        top_choice = (0, None)
        for choice in choices:
            val = fuzz.ratio(choice.title, title)
            if val > top_choice[0]:
                top_choice = (val, choice)
        return top_choice[1]

    def fuzzy_find_tag(self, title):
        """Fuzzy search for tag with given title."""
        return self.fuzzy_find(title, self.tags.values())

    def fuzzy_find_notebook(self, title):
        """Fuzzy search for notebook with given title."""
        return self.fuzzy_find(title, self.notebooks.values())

    def fuzzy_find_note(self, title):
        """Fuzze search for note with given title."""
        return self.fuzzy_find(title, self.get_notes())

    def search(self, key):
        """Searches for given key and returns note-instances."""
        json_notes = self.api.search(key)
        notes = []
        for json_note in json_notes:
            self.find_note(json_note['id'])
        return notes

    def get_notes(self):
        """Returns notes in a sorted list."""
        return sorted(
            [note for nb in self.notebooks.values()
             for note in nb.notes.values()],
            key=lambda note: note.title)

    def get_notebooks(self):
        """Returns notebooks in a sorted list."""
        return sorted(self.notebooks.values(), key=lambda nb: nb.title)

    def get_tags(self):
        """Returns tags in a sorted list."""
        return sorted(self.tags.values(), key=lambda tag: tag.title)
