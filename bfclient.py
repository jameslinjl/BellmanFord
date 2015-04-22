# create a host, to_string is IP address, port tuple
# read in from config file
# host has udp socket
# host has a list of <dest, cost> tuples as distance vectors
# need to update distance vectors
# poison reverse
# timeout, needs to be multi-threaded

import socket
import sys

def main():
    # create UDP socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print 'Socket created'
    except socket.error:
        print 'Failed to create socket'
        sys.exit()

    # bind UDP socket
    try:
        s.bind(('', 5000))
    except socket.error:
        print 'Bind failed'
        sys.exit()

    print 'Socket bind complete'

    # serve, echo server for now
    while 1:
        d = s.recvfrom(1024)
        data = d[0]
        addr = d[1]

        if not data:
            break

        reply = 'OK...' + data

        s.sendto(reply, addr)
        print 'replied'

    s.close()

if __name__ == '__main__':
    main()