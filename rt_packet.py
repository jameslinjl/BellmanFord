class RTPacket:
    'packets that can be sent back and forth'

    def __init__(self, code, hostname, dvs=[], link = ''):
        self.code = code
        self.hostname = hostname
        self.dvs = dvs
        self.link = link

    def __str__(self):
        if self.code == 'ROUTEUDPATE':
            return self.hostname + '\n' + 'ROUTEUDPATE' + '\n' + str(self.dvs)
        if self.code == 'LINKDOWN':
            return self.hostname + '\n' + 'LINKDOWN' + '\n' + self.link
        if self.code == 'LINKUP':
            return self.hostname + '\n' + 'LINKUP'