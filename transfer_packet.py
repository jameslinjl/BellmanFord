class TransferPacket:
    'packets that can be sent back and forth for file transfer'

    '''
    source - source of the packet
    destination - final destination of packet
    data - the data itself
    '''
    def __init__(self, source, destination):
        self.sourceIP = source.split(':')[0]
        self.sourcePT = source.split(':')[1]
        self.destinationIP = destination.split(':')[0]
        self.destinationPT = destination.split(':')[1]

    def __str__(self):
        import struct
        sourceIPArr = self.sourceIP.split('.')
        sourcePT = int(self.sourcePT)
        destinationIPArr = self.destinationIP.split('.')
        destinationPT = int(self.destinationPT)

        header = struct.pack('cBBBBHBBBBH', 'T', int(sourceIPArr[0]), 
            int(sourceIPArr[1]), int(sourceIPArr[2]), int(sourceIPArr[3]), 
            sourcePT, int(destinationIPArr[0]), int(destinationIPArr[1]), 
            int(destinationIPArr[2]), int(destinationIPArr[3]), destinationPT)
        return header