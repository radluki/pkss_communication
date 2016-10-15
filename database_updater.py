from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
import getpass
import logging

Base = declarative_base()



class State(Base):
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

class DatabaseUpdater(object):

    def __init__(self,login,password,database,table=State):
        #TODO substitute localhost
        engine = create_engine(\
                 'mysql+mysqlconnector://{login}:{password}@localhost/{base}'\
                 .format(login=login, base=database, password=password))

        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.table = table

    def send(self,row):
        row = {k:v for k,v in row.items() if k in self.table.COLUMNS}
        table_element = self.table(row)
        logging.info('updating database with: {}'.format(table_element))
        try:
            self.session.add(table_element)
            self.session.commit()
        except Exception as e:
            logging.error(e)



if __name__ == '__main__':
    password = getpass.getpass()
    database_updater = DatabaseUpdater('root',password,'luki_testing')
    session = database_updater.session

    test_dict = dict()
    import random
    for k in State.COLUMNS:
        test_dict[k] = random.random()*100

    database_updater.send(test_dict)

    for instance in session.query(State).order_by(State.time):
        print(instance)
        if instance == test_dict:
            print('hurra')

