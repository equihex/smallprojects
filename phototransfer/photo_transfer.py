import json
import os

from base_logger import BaseLogger
from dropbox_connector import DropboxConnector
from google_drive_connector import GoogleDriveConnector


class PhotoTransfer(object):
    """
    Sync photos from Dropbox storage to Google storage
    """

    DROPBOX_DIRS = [
        '/Photos/',
        '/Global4/',
        '/MacbookAperture/',
        '/Lightroom/',
        '/Camera Uploads/'
    ]

    GDOCS_DB_FOLDER_ID = '0B8NZdrRKKIkBazJFcUxUZ3V0OW8'

    JSON_PROCESSED_FILE_PATH = 'processed_hashes.json'

    def __init__(self):
        self._dbc = DropboxConnector()
        self._gdc = GoogleDriveConnector()
        self.logger = BaseLogger.get_logger(self.__class__.__name__)
        self.processed_hashes = set()
        BaseLogger.send_all_logs_to_file('photo_transfer.log')

    def _load_processed_hashes(self):
        try:
            with open(self.JSON_PROCESSED_FILE_PATH, 'r') as fin:
                self.processed_hashes = set(json.load(fin))
        except (IOError, ValueError):
            pass

    def _persist_processed_hashes(self):
        with open(self.JSON_PROCESSED_FILE_PATH, 'w') as fout:
            json.dump(
                list(self.processed_hashes),
                fout,
            )

    def _copy_photo(self, path, md5hash):
        self.logger.info('Copying photo {0}'.format(path))
        local_path = '{0}.jpg'.format(md5hash)
        self._dbc.download_file(path, local_path)
        self._gdc.upload_file(
            local_path,
            photo_name=md5hash,
            folder_id=self.GDOCS_DB_FOLDER_ID,
        )
        self.logger.info('Copy complete')
        os.unlink(local_path)

    def process(self):
        self._load_processed_hashes()
        google_hashes = self._gdc.get_all_photo_md5s()
        for (photo_path, md5hash) in self._dbc.yield_all_photos(self.DROPBOX_DIRS):
            skip_hashes = google_hashes | self.processed_hashes

            if md5hash in skip_hashes:
                self.logger.info('Skipping {0}'.format(photo_path))
                continue
            # do copy
            self._copy_photo(photo_path, md5hash)
            self.processed_hashes.add(md5hash)
            self._persist_processed_hashes()


if __name__ == '__main__':
    pt = PhotoTransfer()
    pt.process()

