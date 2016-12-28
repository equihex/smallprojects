import hashlib
import json
import re
from os.path import basename
from pprint import pprint

import httplib2
import yaml
from googleapiclient import discovery
from oauth2client.client import OAuth2Credentials

from base_logger import BaseLogger


class GoogleDriveConnector(object):
    """
    Connect to gdrive
    """
    JSON_PERSIST_FILE_PATH = 'persist_hashes.json'

    def __init__(self):
        self.logger = BaseLogger.get_logger(self.__class__.__name__)
        with open('config.yaml') as fin:
            config = yaml.load(fin)
        creds = OAuth2Credentials(
            access_token=config['google']['access_token'],
            refresh_token=config['google']['refresh_token'],
            client_id=config['google']['client_id'],
            client_secret=config['google']['client_secret'],
            token_expiry=config['google']['token_expiry'],
            token_uri=config['google']['token_uri'],
            user_agent=config['google']['user_agent'],
        )
        self._http = creds.authorize(httplib2.Http())
        creds.refresh(self._http)
        self.service = discovery.build('drive', 'v3', http=self._http)
        self.f = self.service.files()
        self._next_photos_page_token = None
        self.hashes = []

    def _get_photo_md5(self, file_id):
        photo = self.f.get(fileId=file_id, fields='imageMediaMetadata').execute()
        if not photo:
            self.logger.warning('Unable to find metadata for photo id {0}'.format(file_id))
            return None

        photo_meta = photo['imageMediaMetadata']
        md5 = hashlib.md5()
        try:
            md5.update(str(photo_meta['height']))
            md5.update(str(photo_meta['width']))
            md5.update(photo_meta['time'].replace(' ', ''))
        except KeyError:
            # incomplete metadata
            return None
        return md5.hexdigest()

    def _load_persisted_hashes(self):
        try:
            with open(self.JSON_PERSIST_FILE_PATH, 'r') as fin:
                obj = json.load(fin)
            self.hashes = obj['hashes']
            self._next_photos_page_token = obj['next_token']
        except (IOError, ValueError):
            pass

    def _persist_hashes(self):
        # remove dupes
        self.hashes = list(set(self.hashes))
        with open(self.JSON_PERSIST_FILE_PATH, 'w') as fout:
            json.dump(
                {
                    'hashes': self.hashes,
                    'next_token': self._next_photos_page_token,
                },
                fout,
            )

    def get_all_photo_md5s(self):
        self._load_persisted_hashes()
        self.logger.info('Loading photo hashes')
        while True:
            res = self.f.list(spaces='photos', pageToken=self._next_photos_page_token).execute()
            self.hashes.extend(map(lambda x: self._get_photo_md5(x['id']), res['files']))
            try:
                self._next_photos_page_token = res['nextPageToken']
                self.logger.info('Paging: token = {0}'.format(self._next_photos_page_token))
            except KeyError:
                break
            self._persist_hashes()
        #persist partials to files
        return set(self.hashes)

    def upload_file(self, file_path, photo_name):
        return self.f.create(media_body=file_path, body={'name': photo_name}).execute()

    def upload_photo(self, file_path, photo_name):
        """
        https://picasaweb.google.com/data/feed/api/user/default/albumid/default
        :param file_path:
        :param photo_name:
        :return:
        """
        with open(file_path, 'rb') as fin:
            img_data = fin.read()
        res = self._http.request(
            "https://picasaweb.google.com/data/feed/api/user/default/albumid/default",
            "POST",
            body=img_data,
            headers={
                'Content-Type': 'image/jpeg',
                'Content-Length': len(img_data),
                'Slug': photo_name,
            }
        )
        if not re.search(r'2\d{2}', res[0]['status']):
            self.logger.critical('Upload failed: {0}'.format(res))
            raise StopIteration


if __name__ == '__main__':
    gdc = GoogleDriveConnector()
    res = gdc.upload_photo(
        '/Users/warnerj1/PycharmProjects/smallprojects/phototransfer/22441b7280d5f63523bb6058a7636805.jpg',
        'fooo',
    )
