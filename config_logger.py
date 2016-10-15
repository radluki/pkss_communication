import logging

def configure_logger(args,level=logging.ERROR):
    """
    Configures logging
    Requires args to have:
    args.logfile - string - name of logfile
    args.console - boolean - if True sets logging to console
    """
    # logger configuration
    logFormatter = logging.Formatter('%(levelname)s - %(asctime)s:\t\t\t%(message)s')
    rootLogger = logging.getLogger()
    rootLogger.setLevel(level)

    #if not os.path.isabs(args.logfile):
    #    args.logfile = os.path.abspath(args.logfile)
    fileHandler = logging.FileHandler(args.logfile)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    if args.console:
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        rootLogger.addHandler(consoleHandler)