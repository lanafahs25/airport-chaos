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


    #sort the tree 
    def inorder (self):
        result = []
        trail = []
        x = self.root 

        while x is not None or len(trail) != 0: 

            while x is not None:

                trail.append(x)
                x = x.left

            x = trail.pop()
            result.append(x.flight)

            x = x.right

        return result 


    #search the tree
    def search (self, key):
        x = self.root

        while x is not None:
            if key == x.key:
                return x

            elif key > x.key:
                x = x.right

            else:
                x = x.left

        return None


    def minimum(self, x):
        while x.left is not None:
            x = x.left
        return x

    def maximum(self, x):
        while x.right is not None:
            x = x.right
        return x

    def successor(self, x):
        if x.right is not None:
            return self.minimum(x.right)
        
        y = x.parent

        while y is not None and x is y.right:
            x = y
            y = y.parent

        return y


    def predecessor(self, x):
        if x.left is not None:
            return self.maximum(x.left)
        
        y = x.parent

        while y is not None and x is y.left:
            x = y
            y = y.parent

        return y

        