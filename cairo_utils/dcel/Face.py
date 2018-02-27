""" The highest level data structure in a dcel, apart from the dcel itself """
import logging as root_logger
import numpy as np
from numbers import Number
from itertools import cycle, islice
from functools import partial, cmp_to_key
import IPython

from .HalfEdge import HalfEdge

logging = root_logger.getLogger(__name__)

class Face(object):
    """ A Face with a start point for its outer component list,
    and all of its inner components """

    nextIndex = 0

    def __init__(self, site_x, site_y, index=None, dcel=None):
        assert(isinstance(site_x, Number))
        assert(isinstance(site_y, Number))
        #Site is the voronoi point that the face is built around
        self.site = np.array([site_x, site_y])
        #Starting point for bounding edges, going anti-clockwise
        self.outerComponent = None
        #Clockwise inner loops - check this
        #Opposing face halfedges
        self.outerBoundaryEdges = []
        #Primary list of edges for this face
        self.edgeList = []
        #mark face for cleanup:
        self.markedForCleanup = False
        #Additional Data:
        self.data = {}
        self.dcel = dcel
        
        #todo: add a 'free vertices' field, which can be used to build the face
        
        if index is None:
            logging.debug("Creating Face {}".format(Face.nextIndex))
            self.index = Face.nextIndex
            Face.nextIndex += 1
        else:
            assert(isinstance(index, int))
            logging.debug("Re-creating Face: {}".format(index))
            self.index = index
            if self.index >= Face.nextIndex:
                Face.nextIndex = self.index + 1


    def __str__(self):
        return "Face: {}".format(self.getCentroid())

    def __repr__(self):
        if self.outerComponent is not None:
            outer = self.outerComponent.index
        else:
            outer = False
        inner = len(self.outerBoundaryEdges)
        edgeList = len(self.edgeList)
        return "(Face: {}, outer: {}, inner: {}, edgeList: {})".format(self.index,
                                                                       outer,
                                                                       inner,
                                                                       edgeList)        
    
    def _export(self):
        """ Export identifiers rather than objects, to allow reconstruction """
        logging.debug("Exporting face: {}".format(self.index))
        return {
            'i' : self.index,
            'edges' : [x.index for x in self.edgeList if x is not None],
            'sitex' : self.site[0],
            'sitey' : self.site[1],
        }

    def removeEdge(self, edge):
        """ Remove an edge from this face, if the edge has this face
        registered, remove that too """
        assert(isinstance(edge, HalfEdge))
        #todo: should the edge be connecting next to prev here?
        if not bool(self.outerBoundaryEdges) and not bool(self.edgeList):
            return
        if edge in self.outerBoundaryEdges:
            self.outerBoundaryEdges.remove(edge)
        if edge in self.edgeList:
            self.edgeList.remove(edge)
        if edge.face is self:
            edge.face = None

            
    def get_bbox(self):
        """ Get a rough bbox of the face """
        #TODO: fix this? its rough
        vertices = [x.origin for x in self.edgeList]
        vertexArrays = [x.toArray() for x in vertices if x is not None]
        if not bool(vertexArrays):
            return np.array([[0, 0], [0, 0]])
        allVertices = np.array([x for x in vertexArrays])
        bbox = np.array([[allVertices[:, 0].min(), allVertices[:, 1].min()],
                         [allVertices[:, 0].max(), allVertices[:, 1].max()]])
        logging.debug("Bbox for Face {}  : {}".format(self.index, bbox))
        return bbox

    def getAvgCentroid(self):
        """ Get the averaged centre point of the face from the vertices of the edges """
        k = len(self.edgeList)
        xs = [x.origin.x for x in self.edgeList]
        ys = [x.origin.y for x in self.edgeList]
        norm_x = sum(xs) / k
        norm_y = sum(ys) / k
        return np.array([norm_x, norm_y])


    def getCentroid(self):
        """ Get the user defined 'centre' of the face """
        return self.site.copy()

    def getCentroidFromBBox(self):
        """ Alternate Centroid, the centre point of the bbox for the face"""
        bbox = self.get_bbox()
        #max - min /2
        norm = bbox[1, :] + bbox[0, :]
        centre = norm * 0.5
        return centre


    def __getCentroid(self):
        """ An iterative construction of the centroid """
        vertices = [x.origin for x in self.edgeList if x.origin is not None]
        centroid = np.array([0.0, 0.0])
        signedArea = 0.0
        for i, v in enumerate(vertices):
            if i+1 < len(vertices):
                n_v = vertices[i+1]
            else:
                n_v = vertices[0]
            a = v.x*n_v.y - n_v.x*v.y
            signedArea += a
            centroid += [(v.x+n_v.x)*a, (v.y+n_v.y)*a]

        signedArea *= 0.5
        if signedArea != 0:
            centroid /= (6*signedArea)
        return centroid

    def getEdges(self):
        """ Return a copy of the edgelist for this face """
        return self.edgeList.copy()

    def add_edges(self, edges):
        assert(isinstance(edges, list))
        for x in edges:
            self.add_edge(x)
    
    def add_edge(self, edge):
        """ Add a constructed edge to the face """
        assert(isinstance(edge, HalfEdge))
        if edge.face is None:
            edge.face = self
        self.outerBoundaryEdges.append(edge)
        self.edgeList.append(edge)

    def sort_edges(self):
        """ Order the edges clockwise, by starting point """
        logging.debug("Sorting edges")
        centre = self.getAvgCentroid()
        self.edgeList.sort(key=cmp_to_key(partial(HalfEdge.compareEdges, centre)))
        self.edgeList.reverse()

        paired = zip(self.edgeList, islice(cycle(self.edgeList), 1, None))
        try:
            for a,b in paired:
                assert(a.twin.origin == b.origin)
        except AssertionError as e:
            IPython.embed(simple_prompt=True)

    def has_edges(self):
        """ Check if its a null face or has actual edges """
        innerEdges = bool(self.outerBoundaryEdges)
        outerEdges = bool(self.edgeList)
        return innerEdges and outerEdges

    def markForCleanup(self):
        self.markedForCleanup = True

    def subdivide(self, edge_a, r_a, edge_b, r_b):
        """ Divide a face in half by creating a new line
        between the ratio point on edge_a -> ration point of edge_b,
        returning the new pair of faces
        """
        #TODO
        #todo: add a check for if the new edge intersects any other 
        assert(edge_a is not edge_b)
        assert(isinstance(edge_a, HalfEdge))
        assert(isinstance(edge_b, HalfEdge))
        assert(0 <= r_a <= 1)
        assert(0 <= r_b <= 1)

        #split the two edges
        #create a new line between them

        #sort all vertices of the face
        #get the sequence of new av -> ... -> ab
        #get the disjoint set from that sequence
        #create a new face
        #put the av->bv sequence in one, disjoint set in the other
        
        return ()
