class RTPacket:
    'packets that can be sent back and forth'

    '''
    code - code to define function of packet
    hostname - source in format <IP>:<local port>
    dvs - for ROUTEUPDATE, list of my current dvs
    link - the link that went down or up
    '''
    def __init__(self, code, hostname, dvs=[], link = '', value = 0):
        self.code = code
        self.hostname = hostname
        self.dvs = dvs
        self.link = link
        self.value = value

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
        if self.code == 'CHANGECOST':
            return self.hostname + '&' + self.code + '&' + str(self.value)