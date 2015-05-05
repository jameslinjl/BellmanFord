class RTPacket:
    'packets that can be sent back and forth'

    '''
    code - code to define function of packet
    hostname - source in format <IP>:<local port>
    dvs - for ROUTEUPDATE, list of my current dvs
    link - the link that went down or up
    '''
    def __init__(self, code, hostname, dvs=[], link = ''):
        self.code = code
        self.hostname = hostname
        self.dvs = dvs
        self.link = link

    def __str__(self):
        if self.code == 'ROUTEUPDATE':
            s = ''
            for dv in self.dvs:
                s = s + str(dv) + '/'
            return self.hostname + '&' + self.code + '&' + s
        if self.code == 'LINKDOWN':
            return self.hostname + '&' + self.code + '&' + self.link
        if self.code == 'LINKUP':
            return self.hostname + '&' + self.code