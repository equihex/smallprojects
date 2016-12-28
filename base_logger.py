# currently a simple console logger, can be extended
import logging
import sys


class BaseLogger(object):
    cache = {}

    @classmethod
    def get_logger(cls, name='Unnamed Logger'):

        if name in cls.cache:
            return cls.cache[name]

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # catch duplicate handler instances
        if not logger.handlers:
            ch = logging.StreamHandler(sys.stderr)
            ch.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            logger.addHandler(ch)

        cls.cache[name] = logger
        return logger

    @classmethod
    def send_all_logs_to_file(cls, filename='unnamed.log'):
        for logger in cls.cache.values():
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler = logging.FileHandler(filename)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)


