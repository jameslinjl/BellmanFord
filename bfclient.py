'''
James Lin
jl3782
CSEE 4119 - Computer Networks
Programming Assignment 2
'''

import socket
import signal
import sys
import datetime
import time
import threading
import rt_packet
import transfer_packet
import struct
from multiprocessing import Lock

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

                        # check neighbors paths first
                        original_cost = node[1]
                        min_cost = find_neighbor_value(node[0])
                        min_step = node[0]

                        # check other possible paths
                        for other_path in dv_tables[HOSTNAME]:
                            if other_path[0] == node[0]:
                                continue
                            try:
                                other_table = dv_tables[other_path[0]]
                            except Exception:
                                continue

                            # go through alternate routes
                            for alt in other_table:
                                cost = (find_neighbor_value(other_path[0]) + 
                                    alt[1])
                                if alt[0] == node[0] and cost < min_cost:
                                    min_cost = cost
                                    min_step = other_path[0]

                        is_down = (min_cost >= sys.float_info.max)

                        # make sure it's clear if there is a change
                        if original_cost != min_cost and not is_down:
                            updated = True
                            dv_tables[HOSTNAME].remove(node)
                            dv_tables[HOSTNAME].append((node[0], min_cost,
                                min_step))
                        elif original_cost != min_cost and is_down:
                            updated = True
                            dv_tables[HOSTNAME].remove(node)
                            dv_tables[HOSTNAME].append((node[0], min_cost,
                                'DOWN'))
                
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

    try:
        # remove the header bytes
        header = struct.unpack('cBBBBHBBBBH', data[:14])
        name = struct.unpack('16p', data[14:30])

        # make sure it's a transfer file
        if header[0] == 'T':
            source = (str(header[1]) + '.' + str(header[2]) + '.' + 
                str(header[3]) + '.' + str(header[4]) + ':' + str(header[5]))
            destination = (str(header[6]) + '.' + str(header[7]) + '.' + 
                str(header[8]) + '.' + str(header[9]) + ':' + str(header[10]))

            # if we have arrived, start writing
            if destination == HOSTNAME:
                print 'Packet received'
                print 'Source = ' + str(source)
                print 'Destination = ' + str(destination)
                f = open(name[0], 'ab')
                f.write(bytes(data[30:]))
                f.close()
            else:
                print 'Packet received'
                print 'Source = ' + str(source)
                print 'Destination = ' + str(destination)

                node = ()
                for element in dv_tables[HOSTNAME]:
                    if element[0] == destination:
                        node = element
                        break

                # only finite costs
                if node[1] >= sys.float_info.max:
                    print 'This node is not reachable. Packet dropped.'
                    return 0

                # send on its way
                next_hop = node[2]
                print 'Next hop = ' + next_hop
                time.sleep(.05)
                header = transfer_packet.TransferPacket(source, destination,
                    name[0])
                send_packet(next_hop, bytes(header) + bytes(data[30:]))
            return 0
    except Exception:
        pass

    # parse the data
    data_arr = []
    sender = ''
    code = ''
    try:
        data_arr = data.split('&')
        sender = data_arr[0]
        code = data_arr[1]
    except Exception:
        return 0
    
    if code == 'ROUTEUPDATE':
        # retrieve the data and get rid of delimeter
        row = data_arr[2].split('/')
        tup_row = []
        for i in range(0, len(row)-1):
            result = ()
            try:
                result = eval(row[i])
            except Exception:
                result = (row[i][0], float('inf'), row[i][2])
            if type(result) is tuple:
                tup_row.append(result)

        # perform all necessary changes
        change_neighbor_active(sender, True, True)
        thread_update_dv_tables(sender, tup_row)
        updated = thread_update_paths()
        my_dvs = dv_tables[HOSTNAME]

        if updated and not dead:
            for neighbor in neighbors:
                if neighbor[3] == False:
                    continue

                custom_dvs = []
                for dv in dv_tables[HOSTNAME]:
                    if dv[2] == neighbor[2]:
                        custom_dvs.append((dv[0], sys.float_info.max, dv[2]))
                    else:
                        custom_dvs.append(dv)
                send_packet(neighbor[0], 
                    rt_packet.RTPacket('ROUTEUPDATE', HOSTNAME, custom_dvs))

    if code == 'CHANGECOST':
        value = float(data_arr[2])
        change_neighbor(sender, value)

    if code == 'LINKDOWN':
        destroy_neighbor_link(sender)

    if code == 'LINKUP':
        restore_neighbor_link(sender)

    return 0

# manager thread 
def listener_thread():
    global udp_sock

    while True:
        d = udp_sock.recvfrom(4096)
        data = bytes(d[0])
        addr = d[1]
        server = threading.Thread(target=handle_recv_packet, args=(data,))
        server.start()


# timeout function
def timeout_function(counter):
    global TIMEOUT
    global dead
    global neighbors
    global HOSTNAME
    global my_dvs
    time.sleep(TIMEOUT)

    # only send ROUTEUPDATE if alive
    if not dead:
        # need to destroy these if they fail pulse check
        to_destroy = []
        # send to all neighbors
        for neighbor in neighbors:
            if neighbor[4] == False and counter == 3:
                if neighbor[2] == 'DOWN':
                    continue
                # necessary because of iteration issues
                to_destroy.append(neighbor[0])
                continue
            
            if neighbor[3] == False:
                continue
            # adjust for poison reverse
            custom_dvs = []
            for dv in dv_tables[HOSTNAME]:
                if dv[2] == neighbor[2]:
                    custom_dvs.append((dv[0], sys.float_info.max, dv[2]))
                else:
                    custom_dvs.append(dv)
            send_packet(neighbor[0], 
                rt_packet.RTPacket('ROUTEUPDATE', HOSTNAME, custom_dvs))

        # necessary because of iteration issues
        if counter == 3:
            counter = 0
            for neighbor in to_destroy:
                destroy_neighbor_link(neighbor)
            to_change = []
            for neighbor in neighbors:
                to_change.append(neighbor[0])
            for neighbor in to_change:
                change_neighbor_active(neighbor, False)

    t = threading.Thread(target=timeout_function, args=(counter + 1,))
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

# change neighbor value
def change_neighbor(neighbor_to_change, new_value):
    global lock
    global neighbors
    ignore = False
    lock.acquire()
    try:
        for neighbor in neighbors:
            if neighbor[0] == neighbor_to_change:
                if neighbor[3] == False:
                    ignore = True
                else:
                    new_neighbor = (neighbor_to_change, new_value, 
                        neighbor_to_change, True, True)
                    neighbors.remove(neighbor)
                    neighbors.append(new_neighbor)
                break
    finally:
        lock.release()
        return ignore

# change the activeness of neighbors
def change_neighbor_active(neighbor_to_change, t_or_f, resurrect = False):
    global lock
    global neighbors
    lock.acquire()
    try:
        for neighbor in neighbors:
            if neighbor[0] == neighbor_to_change and neighbor[3] == True:
                new_neighbor = ()
                if resurrect:
                    new_neighbor = (neighbor[0], neighbor[1], 
                        neighbor[2], True, t_or_f)
                else:
                    new_neighbor = (neighbor[0], neighbor[1], 
                        neighbor[2], neighbor[3], t_or_f)
                neighbors.remove(neighbor)
                neighbors.append(new_neighbor)
                break
    finally:
        lock.release()


# down the link
def destroy_neighbor_link(neighbors_link):
    global lock
    global neighbors
    lock.acquire()
    try:
        for neighbor in neighbors:
            if neighbor[0] == neighbors_link:
                new_neighbor = (neighbor[0], sys.float_info.max, 
                    'DOWN', False, False)
                neighbors.remove(neighbor)
                neighbors.append(new_neighbor)
                break
    finally:
        lock.release()

# up the link
def restore_neighbor_link(neighbors_link, new_link_value = 0):
    global lock
    global neighbors
    global original_neighbors
    lock.acquire()
    try:
        for neighbor in neighbors:
            if neighbor[0] == neighbors_link and new_link_value == 0:
                new_neighbor = (neighbor[0], original_neighbors[neighbors_link], 
                    neighbor[0], True, True)
                neighbors.remove(neighbor)
                neighbors.append(new_neighbor)
                break
    finally:
        lock.release()

# find link value to neighbor
def find_neighbor_value(neighbor_to_find):
    global neighbors

    for neighbor in neighbors:
        if neighbor[0] == neighbor_to_find:
            return neighbor[1]
    return sys.float_info.max

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

    # get networking information
    is_first_line = True
    port = 0
    ip = socket.gethostbyname(socket.gethostname())

    # uses the config file to set up the node
    for line in config_file:

        if is_first_line:
            is_first_line = False
            port_timeout = line.split()
            port = int(port_timeout[0])
            ip_port = (ip, int(port_timeout[0]))
            TIMEOUT = int(port_timeout[1])
        else:
            dest_cost = line.split()
            my_dvs.append((dest_cost[0], float(dest_cost[1]), dest_cost[0]))
            neighbors.append((dest_cost[0], float(dest_cost[1]), 
                dest_cost[0], True, True))
            original_neighbors[dest_cost[0]] = float(dest_cost[1])

    
    HOSTNAME = ip + ':' + str(port)
    dv_tables[HOSTNAME] = my_dvs

    # launch the timeout thread
    t = threading.Thread(target=timeout_function, args=(1,))
    t.daemon = True
    t.start()

    # UDP socket stuff
    try:
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # print 'Socket created'
    except socket.error:
        print 'Failed to create socket'
        sys.exit()    

    # bind UDP socket
    try:
        udp_sock.bind((ip_port[0], ip_port[1]))
    except socket.error:
        print 'Bind failed'
        sys.exit()

    # start the listening manager thread
    t = threading.Thread(target=listener_thread)
    t.daemon = True
    t.start()

    # send LINKUP at start to your neighbors
    for neighbor in neighbors:
        send_packet(neighbor[0], rt_packet.RTPacket('LINKUP', HOSTNAME))

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
                # down the link
                destroy_neighbor_link(dv)
                send_packet(dv, rt_packet.RTPacket('LINKDOWN', HOSTNAME))
            else:
                print 'The host you entered is not your neighbor.'
        elif user_input[0] == 'CLOSE':

            if len(user_input) != 1:
                print 'format: CLOSE'
                continue

            dead = True

            for dv in my_dvs:
                destroy_neighbor_link(dv[0])

        elif user_input[0] == 'LINKUP':

            if len(user_input) != 3:
                print 'format: LINKUP <IP address> <local port>'
                continue

            dead = False

            dv = user_input[1] + ':' + user_input[2]

            if in_original(dv):
                restore_neighbor_link(dv)
                send_packet(dv, rt_packet.RTPacket('LINKUP', HOSTNAME))
            else:
                print 'The host you entered is not your neighbor.'
        elif user_input[0] == 'CHANGECOST':

            if len(user_input) != 4 or not is_number(user_input[3]):
                print 'format: CHANGECOST <IP address> <local port> <cost>'
                continue

            dv = user_input[1] + ':' + user_input[2]

            if in_original(dv) and not dead:
                ignore = change_neighbor(dv, float(user_input[3]))
                if not ignore:
                    send_packet(dv, rt_packet.RTPacket('CHANGECOST', HOSTNAME, 
                        value=float(user_input[3])))
            else:
                print 'The host you entered is not your neighbor.'
        elif user_input[0] == 'TRANSFER':

            if len(user_input) != 4:
                print 'format: TRANSFER <file name> <IP address> <local port>'
                continue

            if len(user_input[1]) > 16:
                print 'Keep file name less than 15 characters please.'
                continue

            # find the right node
            destination = user_input[2] + ':' + user_input[3]
            node = ()
            for element in dv_tables[HOSTNAME]:
                if element[0] == destination:
                    node = element
                    break

            # only finite costs
            if node[1] >= sys.float_info.max:
                print 'This node is not reachable'
                continue

            next_hop = node[2]
            print 'Next hop = ' + next_hop

            # start sending the data
            with open(user_input[1],'rb') as f:
                while True:
                    # needs a bit of time to not flood 
                    time.sleep(.05)
                    data=f.read(2048)
                    if not data: break
                    header = transfer_packet.TransferPacket(HOSTNAME, 
                        destination, user_input[1])
                    send_packet(next_hop, bytes(header) + bytes(data))
            print 'File sent successfully'

# ^C terminate gracefully
def ctrl_c_handler(signum, frame):
    global udp_sock
    udp_sock.close()
    exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, ctrl_c_handler)
    main()