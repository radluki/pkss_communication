import getpass
import logging
import sys
from abc import ABCMeta

logger = logging.getLogger(__name__)


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


try:

    """
    For debugging purposes clients do not need to have
    installed sqlalchemy. MODE is automatically set to SIMULATION
    and appropriate class DatabaseUpdaterSimulator is used
    """

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import Column, Integer, Float

    Base = declarative_base()


    class State(Base):
        """ Class represents table in MySQL"""
        __tablename__ = 'simulation_states'

        time = Column(Integer, primary_key=True)
        Tzm = Column(Float)
        Fzm = Column(Float)
        To = Column(Float)
        Tpco = Column(Float)
        Fzco = Column(Float)
        Tpm = Column(Float)
        Tzco = Column(Float)
        Tr = Column(Float)

        COLUMNS = {'time', 'Tzm', 'Fzm', 'To', 'Tpco', 'Fzco', 'Tpm', 'Tzco', 'Tr'}

        def __init__(self,state_dict):
            for k,v in state_dict.items():
                if k in dir(State):
                    self.__dict__[k] = v

        def __repr__(self):
            return "State<('%s')>" % ({k:v for k,v in self.__dict__.items() if k!='_sa_instance_state'})

        def __eq__(self,b):
            """Check equality with accuracy to four decimal places"""
            for k in State.COLUMNS:
                if k=='time':
                    if (self.__dict__[k] - b[k]) ** 2 > 1:
                        return False
                    else:
                        continue
                if (self.__dict__[k]-b[k])**2 > 0.0001**2:
                    return False
            return True


    class DatabaseUpdater(DBUpdater):

        def __init__(self,login,password,database,host='localhost',table=State):
            engine = create_engine(\
                     'mysql+mysqlconnector://{login}:{password}@{host}/{base}'\
                     .format(login=login, base=database, password=password, host=host))

            con = engine.connect()
            try:
                con.execute('drop table simulation_states')
            except:
                print("simulation_testing do not exist")

            Base.metadata.create_all(engine)

            Session = sessionmaker(bind=engine)
            self.session = Session()
            self.table = table
            self.login = login
            self.password = password
            self.database = database
            self.host = host

        def add(self, row):
            """Adds row (i.e. State object) to table buffer (associated with State)"""
            row = {k:v for k,v in row.items() if k in self.table.COLUMNS}
            table_element = self.table(row)
            logger.info('updating database with: {}'.format(table_element))
            try:
                self.session.add(table_element)
            except Exception as e:
                logger.error(e)

        def commit(self):
            """Sends data from buffer to database"""
            self.session.commit()




    if __name__ == '__main__':
        password = getpass.getpass()
        database_updater = DatabaseUpdater('root', password, 'luki_testing')
        session = database_updater.session

        test_dict = dict()
        import random

        for k in State.COLUMNS:
            test_dict[k] = random.random() * 100

        database_updater.add(test_dict)

        for instance in session.query(State).order_by(State.time):
            print(instance)
            if instance == test_dict:
                print('hurra')

except Exception as e:

    print(e,file=sys.stderr)
    print("Available only DatabaseUpdaterSimulator")
    print("Set MODE to Mode.SIMULATION")

finally:

    class DatabaseUpdaterSimulator(DBUpdater):
        """Class created for debugging purposes, no database connection needed"""
        class StateSimulator(object):

            COLUMNS = {'time', 'Tzm', 'Fzm', 'To', 'Tpco', 'Fzco', 'Tpm', 'Tzco', 'Tr'}

            def __init__(self, state_dict):
                for k, v in state_dict.items():
                    if k in dir(State):
                        self.__dict__[k] = v

        def __init__(self,login,password,database,host='localhost',table=StateSimulator):
            logger.info("Creating database updater")
            self.table = table
            self.login = login
            self.password = password
            self.database = database
            self.host = host

        def add(self,row):
            logger.info("Adding {} to buffer".format(row))

        def commit(self):
            logger.info("Commiting data to database")








