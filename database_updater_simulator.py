import logging
from database_updater_interface import DBUpdater

logger = logging.getLogger(__name__)


class DatabaseUpdaterSimulator(DBUpdater):
    """Class created for debugging purposes, no database connection needed"""

    class StateSimulator(object):

        COLUMNS = {'time', 'Tzm', 'Fzm', 'To', 'Tpco', 'Fzco', 'Tpm', 'Tzco', 'Tr'}

        def __init__(self, state_dict):
            for k, v in state_dict.items():
                if k in self.COLUMNS:
                    self.__dict__[k] = v

    def __init__(self, login, password, database, host='localhost', table=StateSimulator):
        logger.info("Creating database updater")
        self.table = table
        self.login = login
        self.password = password
        self.database = database
        self.host = host

    def add(self, row):
        logger.info("Adding {} to buffer".format(row))

    def commit(self):
        logger.info("Commiting data to database")