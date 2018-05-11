import logging as root_logger
from .Node import Node
from .ComparisonFunctions import Directions
import IPython

logging = root_logger.getLogger(__name__)

""" Below are the functional implementations of Red-Black Tree operations """
#todo: integrate these into the beachline class 
def rotateLeft(tree,node):
    """ Rotate the given node left, making the new head be node.right """
    logging.debug("Rotating Left: {}".format(node))
    assert(isinstance(node,Node))
    assert(node.right is not None)
    setAsRoot, newHead = node.rotate_left()
    if setAsRoot:
        tree.root = newHead
    return newHead

def rotateRight(tree,node):
    """ Rotate the given node right, making the new head be node.left """
    logging.debug("Rotating Right: {}".format(node))
    assert(isinstance(node, Node))
    assert(node.left is not None)
    setAsRoot, newHead = node.rotate_right()
    if setAsRoot:
        tree.root = newHead
    return newHead
        
def rbtreeFixup(tree,node):
    """ Verify and fix the RB properties hold """
    while node.parent != None and node.parent.red:
        parent = node.parent
        grandParent = parent.parent
        if grandParent == None:
            break
        elif parent == grandParent.left:
            y = grandParent.right
            if y != None and y.red:
                parent.red = False
                y.red = False
                grandParent.red = True
                node = grandParent
            else:
                if node == parent.right:
                    node = parent
                    rotateLeft(tree,node)#invalidates parent and grandparent
                node.parent.red = False
                node.parent.parent.red = True
                rotateRight(tree,node.parent.parent)
        else:
            y = grandParent.left
            if y != None and y.red:
                parent.red = False
                y.red = False
                grandParent.red = True
                node = grandParent
            else:
                if node == parent.left:
                    node = parent
                    rotateRight(tree,node)#invalidates parent and grandparent
                node.parent.red = False
                node.parent.parent.red = True
                rotateLeft(tree,node.parent.parent)
    tree.root.red = False

def transplant(tree,target,replacement):
    """ Transplant the node replacement, and its subtree, 
    in place of node target """
    #logging.debug("Transplanting {} into {}".format(replacement,target))
    if replacement is not None:
        replacement.disconnect_from_parent()

    if target.parent == None:
        logging.debug("Setting root to {}".format(replacement))
        tree.root = replacement
    elif target.parent.on_left(target):
        logging.debug("Transplant linking left")
        parent = target.parent
        target.disconnect_from_parent()
        parent.link_left(replacement)
    else:
        logging.debug("Transplant linking right")
        parent = target.parent
        target.disconnect_from_parent()
        parent.link_right(replacement)


def rbTreeDelete(tree,node):
    target = node 
    target_originally_red = target.red
    current = None
    logging.debug("Deleting Node: {}".format(node))
    if target.left is None:
        logging.debug("No left, transplanting right")
        current = target.right
        transplant(tree,target,target.right)
    elif target.right is None:
        logging.debug("No right, transplanting left")
        current = target.left
        transplant(tree,target,target.left)
    else:
        logging.debug("Both Left and right exist")
        target = target.right.min()
        target_originally_red = target.red
        current = target.right
        if target.parent == node:
            if current != None:
                logging.debug("target.parent == node")
                target.disconnect_from_parent()
                current.parent = target
        else:
            logging.debug("target.parent != node")
            transplant(tree,target,target.right)
            target.link_right(node.right)

        transplant(tree,node,target)
        target.link_left(node.left)
        target.red = node.red
        
    if not target_originally_red:
        logging.debug("Fixing up current: {}".format(current))
        rbDeleteFixup(tree,current)
    
def rbDeleteFixup(tree,node):
    while node != tree.root and node is not None and not node.red:
        if node.parent.on_left(node):
            w = node.parent.right
            if w is not None and w.red:
                w.red = False
                node.parent.red = True
                rotateLeft(tree,node.parent)
                w = node.parent.right
            if w is not None and (w.left is None or not w.left.red) and \
               (w.right is None or not w.right.red):
                w.red = True
                node = node.parent
            elif w is not None:
                if w.right is None or not w.right.red:
                    w.left.red = False
                    w.red = True
                    rotateRight(tree,w)
                    w = node.parent.right
                w.red = node.parent.red
                node.parent.red = False
                w.right.red = False
                rotateLeft(tree,node.parent)
                node = tree.root
        else: #mirror for right
            w = node.parent.left
            if w is not None and w.red:
                w.red = False
                node.parent.red = True
                rotateRight(tree,node.parent)
                w = node.parent.left
            if w is not None and (w.left is None or not w.left.red) and \
               (w.right is None or not w.right.red):
                w.red = True
                node = node.parent
            elif w is not None:
                if w.left is None or not w.left.red:
                    w.right.red = False
                    w.red = True
                    rotateLeft(tree,w)
                    w = node.parent.left
                w.red = node.parent.red
                node.parent.red = False
                w.left.red = False
                rotateRight(tree,node.parent)
                node = tree.root
        node.red = False
        if w is None:
            node = None
 


