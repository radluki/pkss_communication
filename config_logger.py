import logging


def configure_logger(logfile,console=False,level=logging.ERROR):
    """
    Configures logging
    :param logfile - string - name of logfile
    :param console - boolean - if True sets logging to console
    """
    # logger configuration
    logFormatter = logging.Formatter('%(levelname)s - %(asctime)s:\t\t\t%(message)s')
    rootLogger = logging.getLogger()
    rootLogger.setLevel(level)

    #if not os.path.isabs(args.logfile):
    #    args.logfile = os.path.abspath(args.logfile)
    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    if console:
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        rootLogger.addHandler(consoleHandler)