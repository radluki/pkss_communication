from abc import ABCMeta


class DBUpdater(metaclass=ABCMeta):

    def get_db_dict(self):
        """Along with recreate_database_updater function allows for object recreation in another process"""
        d = {"class": self.__class__, "table": self.table, "login": self.login, \
             "password": self.password, "database": self.database, "host": self.host}
        return d

    def recreate_database_updater(db_dict):
        """Allows for recreation"""
        d = {k:v for k,v in db_dict.items() if k!='class'}
        db_updater = db_dict["class"](**d)
        return db_updater