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
import rt_packet
from multiprocessing import Lock

# instantiate global variables, values of this host
'''
neighbors - the host's one-hop neighbors
my_dvs - this consists of the host's routing table
dv_tables - the routing tables of all other nodes in network
original_neighbors - original neighbor values
'''
ip_port = ('', 0)
udp_sock = None
my_dvs = []
neighbors = []
dv_tables = {}
original_neighbors = {}
TIMEOUT = 0
lock = Lock()
dead = False
HOSTNAME = ''

# update the paths, returns True if paths have actually been changed
def thread_update_paths():
    global lock
    global dv_tables
    global my_dvs
    global HOSTNAME
    updated = False
    lock.acquire()
    try:
        # go through entire dictionary
        for host, lst in dv_tables.iteritems():
            # ignore yourself
            if host == HOSTNAME:
                continue
            # record the link cost
            neighbor_cost = find_neighbor_value(host)
            
            # go through each tuple
            for tup in lst:
                if tup[0] == HOSTNAME:
                    continue

                # if this is the first time, go ahead and record
                if not is_recorded(tup[0]):
                    dv_tables[HOSTNAME].append((tup[0], tup[1] + 
                        neighbor_cost, host))
                    updated = True
                else:
                    # see what the potential path cost is
                    
                    for node in dv_tables[HOSTNAME]:
                        original_cost = node[1]
                        min_cost = find_neighbor_value(node[0])
                        min_step = node[0]
                        for other_path in dv_tables[HOSTNAME]:
                            if other_path[0] == node[0]:
                                continue
                            try:
                                other_table = dv_tables[other_path[0]]
                            except Exception:
                                continue
                            for alt in other_table:
                                cost = other_path[1] + alt[1]
                                # print cost
                                if alt[0] == node[0] and cost < min_cost:
                                    min_cost = cost
                                    min_step = other_path[0]

                        if original_cost != min_cost:
                            updated = True
                            dv_tables[HOSTNAME].remove(node)
                            dv_tables[HOSTNAME].append((node[0], min_cost,
                                min_step))
                
    finally:
        lock.release()
        return updated


# update row on dv_table
def thread_update_dv_tables(host, new_row):
    global lock
    global dv_tables
    lock.acquire()
    try:
        dv_tables[host] = new_row
    finally:
        lock.release()

# handle the packet that was received
def handle_recv_packet(data):
    global dead
    global neighbors
    global HOSTNAME
    global my_dvs
    global dv_tables

    # parse the data
    data_arr = data.split('&')
    sender = data_arr[0]
    code = data_arr[1]
    
    if code == 'ROUTEUPDATE':
        # retrieve the data and get rid of delimeter
        row = data_arr[2].split('/')
        tup_row = []
        for i in range(0, len(row)-1):
            result = eval(row[i])
            if type(result) is tuple:
                tup_row.append(result)

        thread_update_dv_tables(sender, tup_row)
        updated = thread_update_paths()
        my_dvs = dv_tables[HOSTNAME]

        if updated and not dead:
            for neighbor in neighbors:
                send_packet(neighbor[0], 
                    rt_packet.RTPacket('ROUTEUPDATE', HOSTNAME, my_dvs))

    if code == 'CHANGECOST':
        value = float(data_arr[2])
        change_neighbor(sender, value)

    return 0

# manager thread 
def listener_thread():
    global udp_sock

    while True:
        d = udp_sock.recvfrom(4096)
        data = d[0]
        server = threading.Thread(target=handle_recv_packet, args=(data,))
        server.start()


# timeout function
def timeout_function():
    global TIMEOUT
    global dead
    global neighbors
    global HOSTNAME
    global my_dvs
    time.sleep(TIMEOUT)

    # only send ROUTEUPDATE if alive
    if not dead:
        # send to all neighbors
        for neighbor in neighbors:
            # adjust for poison reverse
            # custom my_dvs based on how routing happens
            # change what you report but not actual my_dvs
            send_packet(neighbor[0], 
                rt_packet.RTPacket('ROUTEUPDATE', HOSTNAME, my_dvs))

    t = threading.Thread(target=timeout_function)
    t.daemon = True
    t.start()
    return(0)

'''
destination - destination to send in str format <IP>:<local port>
packet - packet we actually want to send 
'''
def send_packet(destination, packet):
    # send the actual packet
    # create the socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        print 'Failed to create socket'
        sys.exit()

    dest_ip_port = destination.split(':')
    sock.sendto(str(packet), (dest_ip_port[0], int(dest_ip_port[1])))
    sock.close()
    # actually send the stuff


# changes a dv to a certain value, avoids race conditions
def thread_change_dv(dv_to_change, new_value, new_link=''):
    global lock
    global my_dvs
    lock.acquire()
    try:
        for dv in my_dvs:
            if dv[0] == dv_to_change:
                new_dv = ()
                if new_link == '':
                    new_dv = (dv_to_change, new_value, dv[2])
                else:
                    new_dv = (dv_to_change, new_value, new_link)
                my_dvs.remove(dv)
                my_dvs.append(new_dv)
    finally:
        lock.release()

# changes a dv to a certain value, avoids race conditions
def thread_change_dv_row():
    global lock
    global dv_tables
    global HOSTNAME
    global neighbors
    lock.acquire()
    try:
        dv_tables[HOSTNAME] = neighbors
    finally:
        lock.release()

# actual neighbors
def change_neighbor(neighbor_to_change, new_value):
    global neighbors

    for neighbor in neighbors:
        if neighbor[0] == neighbor_to_change:
            new_neighbor = (neighbor_to_change, new_value, neighbor_to_change)
            neighbors.remove(neighbor)
            neighbors.append(new_neighbor)
            break

# find link value to neighbor
def find_neighbor_value(neighbor_to_find):
    global neighbors

    for neighbor in neighbors:
        if neighbor[0] == neighbor_to_find:
            return neighbor[1]
    return float('inf')

# see if link is recorded
def is_recorded(to_find):
    global dv_tables
    global HOSTNAME

    for node in dv_tables[HOSTNAME]:
        if node[0] == to_find:
            return True
    return False

# changes a dv to a certain value, avoids race conditions
def thread_close_host():
    global lock
    global my_dvs
    lock.acquire()
    new_dv_list = []
    try:
        for dv in my_dvs:
            new_dv_list.append((dv[0], float('inf'), 'None'))
        my_dvs = new_dv_list
    finally:
        lock.release()

# checks to see if the dv is adjacent or not
def in_original(dv_to_check):
    global original_neighbors
    try:
        original_neighbors[dv_to_check]
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
    global neighbors
    global dv_tables
    global original_neighbors
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
            my_dvs.append((dest_cost[0], float(dest_cost[1]), dest_cost[0]))
            # neighbors.append((dest_cost[0], float(dest_cost[1])))
            neighbors.append((dest_cost[0], float(dest_cost[1]), dest_cost[0]))
            original_neighbors[dest_cost[0]] = float(dest_cost[1])

    # sock_name = socket.gethostbyname(socket.gethostname())
    HOSTNAME = '127.0.0.1' + ':' + str(port)

    dv_tables[HOSTNAME] = my_dvs
    # print dv_tables
    # print ip_port
    # print TIMEOUT
    # print my_dvs
    # print original_neighbors

    # launch the timeout thread
    t = threading.Thread(target=timeout_function)
    t.daemon = True
    t.start()

    '''
    UDP sock stuff
    '''
    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print 'Socket created'
    except socket.error:
        print 'Failed to create socket'
        sys.exit()    

    # bind UDP socket
    try:
        udp_sock.bind((ip_port[0], ip_port[1]))
    except socket.error:
        print 'Bind failed'
        sys.exit()

    t = threading.Thread(target=listener_thread)
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
                    ', Link = (' + dv[2] + ')')
        elif user_input[0] == 'LINKDOWN':

            if len(user_input) != 3:
                print 'format: LINKDOWN <IP address> <local port>'
                continue

            dv = user_input[1] + ':' + user_input[2]

            if in_original(dv):
                change_neighbor(dv, float('inf'))
                # set any path using link to inf, if so send ROUTEUPDATE
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
                change_neighbor(dv, original_neighbors[dv])
                # should send LINKUP message to destination
                # resume sending ROUTEUPDATE messages
            else:
                print 'The host you entered is not your neighbor.'
        elif user_input[0] == 'CHANGECOST':

            if len(user_input) != 4 or not is_number(user_input[3]):
                print 'format: CHANGECOST <IP address> <local port> <cost>'
                continue

            dv = user_input[1] + ':' + user_input[2]

            if in_original(dv) and not dead:
                change_neighbor(dv, float(user_input[3]))
                thread_change_dv_row()
                send_packet(dv, rt_packet.RTPacket('CHANGECOST', HOSTNAME, 
                    value=float(user_input[3])))
            else:
                print 'The host you entered is not your neighbor.'


# ^C terminate gracefully
def ctrl_c_handler(signum, frame):
    global udp_sock
    udp_sock.close()
    exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_c_handler)
    main()