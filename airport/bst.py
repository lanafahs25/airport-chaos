from . import trace


class Node:
    def __init__ (self, flight):
        self.key = (flight.start, flight.flight_id)
        self.end = flight.end
        self.flight = flight

        self.left = None
        self.right = None
        self.parent = None

class RunwayBST:        #where the tree starts and how many nodes it has
    def __init__ (self):
        self.root = None
        self.size = 0


    # CLRS TREE-INSERT: z = new_node, x = current, y = parent
    def insert (self, flight):
        new_node = Node(flight)
        parent = None
        current = self.root

        while current is not None:
            parent = current

            if new_node.key < current.key:
                current = current.left
            else:
                current = current.right

        new_node.parent = parent

        if parent is None:
            self.root = new_node

        elif parent.key > new_node.key:
            parent.left = new_node

        else:
            parent.right = new_node

        self.size += 1
        return new_node


    #sort the tree (left, node, right) with an explicit stack ("trail")
    def inorder (self, nodes = False):
        result = []
        trail = []
        current = self.root

        while current is not None or len(trail) != 0:

            while current is not None:

                trail.append(current)
                current = current.left

            current = trail.pop()
            result.append(current if nodes else current.flight)

            current = current.right

        return result


    #search the tree
    def search (self, key):
        current = self.root

        while current is not None:
            trace.log(f"search path: {current.flight.flight_id} {current.key[0].strftime('%H:%M')}")
            if key == current.key:
                return current

            elif key > current.key:
                current = current.right

            else:
                current = current.left

        return None


    def minimum(self, node):
        while node.left is not None:
            node = node.left
        return node

    def maximum(self, node):
        while node.right is not None:
            node = node.right
        return node

    # CLRS TREE-SUCCESSOR: x = node, y = ancestor
    def successor(self, node):
        if node.right is not None:
            return self.minimum(node.right)

        ancestor = node.parent

        while ancestor is not None and node is ancestor.right:
            node = ancestor
            ancestor = ancestor.parent

        return ancestor


    def predecessor(self, node):
        if node.left is not None:
            return self.maximum(node.left)

        ancestor = node.parent

        while ancestor is not None and node is ancestor.left:
            node = ancestor
            ancestor = ancestor.parent

        return ancestor

    def height(self):
        if self.root is None:
            return 0

        levels = 0
        level = [self.root]

        while len(level) != 0:
            levels += 1
            next_level = []

            for node in level:
                if node.left is not None:
                    next_level.append(node.left)

                if node.right is not None:
                    next_level.append(node.right)

            level = next_level

        return levels


    #helper method: instead of having a parent be attached to a child 3 times in the same code,
    #create helper method (transplant) to help rewire the links
    #in this case old is the node whose spot is being replaced/deleted (taken over)
    #(CLRS calls old and replacement u and v)

    def _transplant (self, old, replacement):
        if old.parent is None:                  #old was the root
            self.root = replacement

        elif old is old.parent.left:            #old was a left child
            old.parent.left = replacement
        else:
            old.parent.right = replacement      #old was a right child


        if replacement is not None:
            replacement.parent = old.parent     #link back up


    # CLRS TREE-DELETE: z = target, y = successor_node
    def delete (self, target):

        if target.left is None:
            self._transplant(target, target.right)

        elif target.right is None:
            self._transplant(target, target.left)

        else:
            successor_node = self.minimum(target.right)

            if successor_node.parent is not target:
                self._transplant(successor_node, successor_node.right)
                successor_node.right = target.right
                successor_node.right.parent = successor_node

            self._transplant(target, successor_node)
            successor_node.left = target.left
            successor_node.left.parent = successor_node
        self.size -= 1

    #flights starting in [window_start, window_end): skip before the start, stop at the end
    def range_search (self, window_start, window_end):
        result = []
        trail = []
        current = self.root

        while current is not None or len(trail) != 0:
            while current is not None:
                trail.append(current)

                if current.key[0] >= window_start:
                    current = current.left
                else:
                    current = None

            current = trail.pop()

            if current.key[0] >= window_end:
                break

            if current.key[0] >= window_start:
                result.append(current.flight)

            current = current.right

        return result

    #predecessor for a time that isnt in the tree (no node to call predecessor on)
    #node with the latest start <= time, who's right before or at that time?
    #walk down from the root and keep the best so far
    def floor(self, time):
        best = None
        current = self.root

        while current is not None:

            if current.key[0] <= time:
                best = current
                current = current.right

            else:
                current = current.left
        return best

    #successor for a time that isnt in the tree (no node to call successor on)
    #node with the earliest start >= time, who's right after or at that time?
    #walk down from the root and keep the best so far
    def ceiling (self, time):
        best = None
        current = self.root

        while current is not None:

            if current.key[0] >= time:
                best = current
                current = current.left

            else:
                current = current.right
        return best


    def conflicts(self, start, end):
        result = []
        before = self.floor(start)          # latest flight starting at or before `start`
        trace.log("floor (predecessor of the start): " + (f"{before.flight.flight_id} {before.key[0].strftime('%H:%M')}-{before.end.strftime('%H:%M')}" if before else "none"))
        after = self.ceiling(start)         # earliest flight starting at or after `start` (shown in TRACE)
        trace.log("ceiling (successor of the start): " + (f"{after.flight.flight_id} {after.key[0].strftime('%H:%M')}-{after.end.strftime('%H:%M')}" if after else "none"))

        if before is not None and before.key[0] < start and before.end > start:
            result.append(before.flight)

        result += self.range_search(start, end)
        return result
