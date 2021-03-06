### A Red-Black Tree Implementation
# Properties of RBTrees:
# 1) Every node is Red Or Black
# 2) The root is black
# 3) Every leaf is Black, leaves are null nodes
# 4) If a node is red, it's children are black
# 5) All paths from a node to its leaves contain the same number of black nodes

from .RBTree import RBTree
from .Node import Node
from .ComparisonFunctions import Directions
