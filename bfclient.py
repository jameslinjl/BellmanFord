# create a host, to_string is IP address, port tuple
# read in from config file
# host has udp socket
# host has a list of <dest, cost> tuples as distance vectors
# need to update distance vectors
# poison reverse
# timeout, needs to be multi-threaded

import socket
import signal
import sys
import datetime
import time
import threading
from multiprocessing import Lock

# instantiate global variables, values of this host
ip_port = ('', 0)
udp_sock = None
my_dvs = []
dv_tables = {}
original_dv_dic = {}
TIMEOUT = 30
lock = Lock()
dead = False
HOSTNAME = ''

# timeout function
def timeout_function():
    global TIMEOUT
    global dead
    # need to fill this out
    time.sleep(TIMEOUT)
    if not dead:
        print 'TIMEOUT'

    t = threading.Thread(target=timeout_function)
    t.daemon = True
    t.start()
    return(0)

# changes a dv to a certain value, avoids race conditions
def thread_change_dv(dv_to_change, new_value):
    global lock
    global my_dvs
    lock.acquire()
    try:
        for dv in my_dvs:
            if dv[0] == dv_to_change:
                my_dvs.remove(dv)
                my_dvs.append((dv_to_change, new_value))
    finally:
        lock.release()

# changes a dv to a certain value, avoids race conditions
def thread_close_host():
    global lock
    global my_dvs
    lock.acquire()
    new_dv_list = []
    try:
        for dv in my_dvs:
            new_dv_list.append((dv[0], float('inf')))
        my_dvs = new_dv_list
    finally:
        lock.release()

# checks to see if the dv is adjacent or not
def in_original(dv_to_check):
    global original_dv_dic
    try:
        original_dv_dic[dv_to_check]
    except Exception:
        return False
    return True

# checks if input is a number
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def main():
    global ip_port
    global udp_sock
    global my_dvs
    global dv_tables
    global original_dv_dic
    global TIMEOUT
    global dead
    global HOSTNAME

    # check number of args
    if len(sys.argv) != 2:
        print 'format: python bfclient.py <client_config.txt>'
        sys.exit(1)
    
    # opens the config file
    try:
        config_file = open(sys.argv[1], 'r')
    except IOError:
        print 'cannot locate ' + sys.argv[1]
        sys.exit(1)

    is_first_line = True
    port = 0

    # uses the config file to set up the node
    for line in config_file:

        if is_first_line:
            is_first_line = False
            port_timeout = line.split()
            port = int(port_timeout[0])
            ip_port = ('', int(port_timeout[0]))
            TIMEOUT = int(port_timeout[1])
        else:
            dest_cost = line.split()
            my_dvs.append((dest_cost[0], float(dest_cost[1])))
            original_dv_dic[dest_cost[0]] = float(dest_cost[1])

    sock_name = socket.gethostbyname(socket.gethostname())
    HOSTNAME = '127.0.0.1' + ':' + str(port)

    dv_tables[HOSTNAME] = my_dvs
    print dv_tables
    print ip_port
    print TIMEOUT
    print my_dvs
    print original_dv_dic

    # launch the timeout thread
    t = threading.Thread(target=timeout_function)
    t.daemon = True
    t.start()

    # input loop
    '''
    SHOWRT - shows the routing table
    LINKDOWN - makes link value inf
    LINKUP - restores link value to original
    CHANGECOST - changes the cost of the link to custom value
    CLOSE - shuts down the node
    '''
    while True:
        user_input = raw_input()
        user_input = user_input.split()

        if user_input[0] == 'SHOWRT':

            if len(user_input) != 1:
                print 'format: SHOWRT'
                continue

            print ('<' + str(datetime.datetime.now()) + '> ' + 
                'Distance vector list is:')

            for dv in my_dvs:
                print ('Destination = ' + dv[0] + ', Cost = ' + str(dv[1]) + 
                    ', Link = ()')
        elif user_input[0] == 'LINKDOWN':

            if len(user_input) != 3:
                print 'format: LINKDOWN <IP address> <local port>'
                continue

            dv = user_input[1] + ':' + user_input[2]

            if in_original(dv):
                thread_change_dv(dv, float('inf'))
                # send LINKDOWN signal
                # stop exchanging ROUTE UPDATE messages
            else:
                print 'The host you entered is not your neighbor.'
        elif user_input[0] == 'CLOSE':

            if len(user_input) != 1:
                print 'format: CLOSE'
                continue

            dead = True

            for dv in my_dvs:
                thread_close_host()

        elif user_input[0] == 'LINKUP':

            if len(user_input) != 3:
                print 'format: LINKUP <IP address> <local port>'
                continue

            dead = False

            dv = user_input[1] + ':' + user_input[2]

            if in_original(dv):
                thread_change_dv(dv, original_dv_dic[dv])
                # resume sending ROUTE UPDATE messages
            else:
                print 'The host you entered is not your neighbor.'
        elif user_input[0] == 'CHANGECOST':

            if len(user_input) != 4 or not is_number(user_input[3]):
                print 'format: CHANGECOST <IP address> <local port> <cost>'
                continue

            dv = user_input[1] + ':' + user_input[2]

            if in_original(dv):
                thread_change_dv(dv, float(user_input[3]))
            else:
                print 'The host you entered is not your neighbor.'


    '''

    # create UDP socket

    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print 'Socket created'
    except socket.error:
        print 'Failed to create socket'
        sys.exit()

    
    # bind UDP socket
    try:
        udp_sock.bind(('', 5000))
    except socket.error:
        print 'Bind failed'
        sys.exit()

    print 'Socket bind complete'

    # serve, echo server for now
    while 1:
        d = udp_sock.recvfrom(1024)
        data = d[0]
        addr = d[1]

        if not data:
            break

        reply = 'OK...' + data

        udp_sock.sendto(reply, addr)
        print 'replied'
    '''

# ^C terminate gracefully
def ctrl_c_handler(signum, frame):
    global udp_sock
    udp_sock.close()
    exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_c_handler)
    main()