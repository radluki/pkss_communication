from client import *

def parse_args():
    """Parses arguments from terminal"""
    parser = argparse.ArgumentParser(description="Sets up client app")
    parser.add_argument(dest='ip')
    parser.add_argument(dest='port')
    parser.add_argument(dest='outputfile')
    parser.add_argument('-r', '--request', dest='request', metavar='requested_variables', nargs='*')
    parser.add_argument('-f', '--file', dest='file', metavar='file_to_send')
    parser.add_argument('-s', '--string', dest='string', metavar='string_to_send',help="Example: -s \"{\"a\":1,\"b\":2}\"")
    parser.add_argument('-l', '--logfile', dest='logfile')
    parser.add_argument('-c', '--console', dest='console',action='store_true')

    args = parser.parse_args()

    if not (args.file is None):
        if not (args.string is None):
            warnings.warn("String will be overwritten by file contents")
        with open(args.file, "r") as f:
            args.string = " ".join(list(f))

    args.string = json.loads(args.string)
    args.port = int(args.port)

    return args


if __name__=="__main__":
    args = parse_args()

    # TODO remove f operations
    f = open('port.txt')
    port = int(f.__next__()) # overwriting args
    args.port = port

    client = Client(args.ip,args.port)
    data_received = client.exchange_data(args.string,args.request)
    with open(args.outputfile,"w+") as of:
        json.dump(data_received,of)
    print(data_received)
