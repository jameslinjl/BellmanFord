James Lin
jl3782
CSEE 4119 - Computer Networks
Programming Assignment 2

Description:
This program implements the Bellman-Ford algorithm on distance vectors as described in class. It makes use of UDP
to simulate the transfer of packets between routers. The routing packets are structured in normal string format.
More specifically, they contain the source host, the type of packet it is, and potentially a payload depending on 
the type of packet. These are delimited by '&' and the payload, typically a neighbor's routing information, is 
delimited by '/'. These are stored in a routing table, which consists of a Python dictionary in which each key is
the neighbor's IP address and local port and the value for each key is a list with the appropriate routing information.
Each piece of routing information is a tuple, which contains the destination location, cost, and next hop. On top
of this layer is a transport layer, which allows for the transfer of files using the routing information built below.
The format of these transfer packets are a header consisting of 14 bytes with the source information and 16 bytes of
the file's name. The rest of the packet, up to 2018 bytes, is the payload, which can be binary or ascii data.

Things of note:
- No extra credit was done.
- Poison reverse is working BUT there are some cases in which CYCLES will result in a count to infinity. I don't 
have time to resolve this issue unfortunately. IF you test with any case without cycles, there will definitely not
be any problems.

Instructions:
To run the program, simply type the following command on each host -->
python bfclient.py <client-config-file>

where a <client-config-file> consists of this format

<local port> <TIMEOUT>
<neighbor1 IP>:<neighbor1 local port> <cost1>
<neighbor2 IP>:<neighbor2 local port> <cost2>
.
.
.
<neighbork IP>:<neighbork local port> <costk>

Sample Test Cases:

From the root directory of the submission
(A) python bfclient.py abcd/clientA.txt
(B) python bfclient.py abcd/clientB.txt
(C) python bfclient.py abcd/clientC.txt
(D) python bfclient.py abcd/clientD.txt

run SHOWRT on each (TIMEOUT is 10 seconds)
(A) CHANGECOST 127.0.0.1 4116 56
(B) CHANGECOST 127.0.0.1 4118 60
run SHOWRT on each (TIMEOUT is 10 seconds)
(D) LINKDOWN 127.0.0.1 4116
run SHOWRT on each (TIMEOUT is 10 seconds)
(C) TRANSFER <file in another directory> 127.0.0.1 4118
(C) CLOSE
(C) LINKUP 127.0.0.1 4116
(D) ^C
(D) python bfclient.py abcd/clientD.txt
