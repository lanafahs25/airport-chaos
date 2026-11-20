class Node:
    def __init__ (self, flight):
        self. key = (flight.start, flight.flight_id)
        self.end = flight.end
        self.flight = flight

        self.left = None
        self.right = None
        self.parent = None 

class RunwayBST:        #where the tree starts and how many nodes it has
    def __init__ (self):
        self.root = None
        self.size = 0


    def insert (self, flight):
        z = Node (flight)
        y = None 
        x = self.root

        while x is not None:
            y = x

            if z.key < x.key:
                x = x.left
            else:
                x = x.right

        z.parent = y

        if y is None:
            self.root = z

        elif y.key > z.key:
            y.left = z

        else:
            y.right = z

        self.size += 1
        return z
