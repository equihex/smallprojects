import hashlib
from pprint import pprint

from collections import defaultdict
from dropbox import dropbox
import yaml
from dropbox.files import FileMetadata, FolderMetadata


class DropboxConnector(object):
    """
    Interface to dropbox
    """

    def __init__(self):
        with open('config.yaml') as fin:
            config = yaml.load(fin)
        self.d = dropbox.Dropbox(config['dropbox-token'])

    def _is_valid_photo(self, f_meta):
        if f_meta.path_lower[-4:] == '.jpg' or f_meta.path_lower[-5:] == '.jpeg':
            return True

    def _get_photo_md5(self, f_meta):
        md5 = hashlib.md5()
        photo_meta = f_meta.media_info.get_metadata()
        # dims
        try:
            time_taken = photo_meta.time_taken.strftime('%Y:%m:%d%H:%M:%S')
        except AttributeError:
            time_taken = ''

        for meta_val in [
            photo_meta.dimensions.height,
            photo_meta.dimensions.width,
            time_taken,
        ]:
            md5.update(str(meta_val))

        return md5.hexdigest()

    def _walk_folder_for_photos(self, folder):
        contents = self.d.files_list_folder(folder, include_media_info=True)
        while True:
            for f_meta in contents.entries:
                if isinstance(f_meta, FolderMetadata):
                    for r in self._walk_folder_for_photos(f_meta.path_lower):
                        yield r
                elif isinstance(f_meta, FileMetadata):
                    if self._is_valid_photo(f_meta):
                        yield (f_meta.path_lower, self._get_photo_md5(f_meta))

            if contents.has_more:
                print 'paging'
                contents = self.d.files_list_folder_continue(cursor=contents.cursor)
            else:
                break

    def yield_all_photos(self, folders):
        """
        Produce a list / iterator of all photos stored in a folder or its subfolders
        """
        for folder in folders:
            for x in self._walk_folder_for_photos(folder):
                yield x

    def download_file(self, db_path, local_path):
        self.d.files_download_to_file(local_path, db_path)

    def process(self):
        res = self.d.files_list_folder('/Photos/').entries
        pprint(filter(lambda x: isinstance(x, FileMetadata), res))
        pprint(self.d.files_get_metadata(filter(lambda x: isinstance(x, FileMetadata), res)[5].path_display, include_media_info=True))


if __name__ == '__main__':
    dc = DropboxConnector()
    # dc.process()
    hashes = defaultdict(int)
    f_map = defaultdict(list)
    for x in dc.yield_all_photos(['/Photos/']):
        hashes[x[1]] += 1
        f_map[x[1]].append(x[0])



    pprint(dict(hashes))
    pprint(dict(f_map))

    # TODO: dims + timetaken + optional GPS + [rounded filesize?] should produce a unique identifier for a given image
