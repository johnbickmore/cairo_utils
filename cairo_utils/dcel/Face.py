""" The highest level data structure in a dcel, apart from the dcel itself """
import logging as root_logger
import numpy as np
from numbers import Number
from itertools import cycle, islice
from functools import partial, cmp_to_key
from math import radians
from scipy.spatial import ConvexHull
import IPython

from ..constants import START, END, SMALL_RADIUS, FACE, EDGE, VERTEX, WIDTH
from ..drawing import drawRect, drawCircle, clear_canvas, drawText
from .constants import EditE, FaceE, SampleFormE
from .Vertex import Vertex
from .HalfEdge import HalfEdge
from .Drawable import Drawable
from ..constants import TWOPI
from .. import math as cumath
from ..math import rotatePoint, calc_bbox_corner, within_bbox

logging = root_logger.getLogger(__name__)

class Face(Drawable):
    """ A Face with a start point for its outer component list,
    and all of its inner components """

    nextIndex = 0

    def __init__(self, site=None, index=None, data=None, dcel=None):
        if site is not None:
            #site = np.array([0,0])
            assert(isinstance(site, np.ndarray))
        #Site is the voronoi point that the face is built around
        self.site = site
        #Primary list of ccw edges for this face
        self.edgeList = []
        self.coord_list = None
        #mark face for cleanup:
        self.markedForCleanup = False
        #Additional Data:
        self.data = {}
        if data is not None:
            self.data.update(data)
        self.dcel = dcel

        #free vertices to build a convex hull from:
        self.free_vertices = set()
        
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
                
        if self.dcel is not None and self not in self.dcel.faces:
            self.dcel.faces.add(self)

                
    def copy(self):
        with self.dcel:
            #copy the halfedges
            es = [x.copy() for x in self.edgeList]
            #create a new face
            f = self.dcel.newFace(edges=es)
            #copy the data
            f.data.update(self.data)
            #return it
            return f

    #------------------------------
    # def hulls
    #------------------------------

    @staticmethod
    def hull_from_vertices(verts):
        """ Given a set of vertices, return the convex hull they form,
        and the vertices to discard """
        #TODO: put this into dcel?
        assert(all([isinstance(x, Vertex) for x in verts]))
        #convert to numpy:
        npPairs = [(x.toArray(),x) for x in verts]
        hull = ConvexHull([x[0] for x in npPairs])
        hullVerts = [npPairs[x][1] for x in hull.vertices]
        discardVerts = set(verts).difference(hullVerts)
        assert(len(discardVerts.intersection(hullVerts)) == 0)
        assert(len(discardVerts) + len(hullVerts) == len(verts))
        return (hullVerts, list(discardVerts))

    @staticmethod
    def hull_from_coords(coords):
        """ Given a set of coordinates, return the hull they would form 
        DOESN NOT RETURN DISCARDED, as the coords are not vertices yet
        """
        assert(isinstance(coords, np.ndarray))
        assert(coords.shape[1] == 2)
        hull = ConvexHull(coords)
        hullCoords = np.array([coords[x] for x in hull.vertices])
        return hullCoords

    #------------------------------
    # def Human Readable Representations
    #------------------------------
    
                
    def __str__(self):
        return "Face: {}".format(self.getCentroid())

    def __repr__(self):
        edgeList = len(self.edgeList)
        return "(Face: {}, edgeList: {})".format(self.index, edgeList)        

    def draw(self, ctx, clear=False, force_centre=False, text=False, data_override=None):
        """ Draw a single Face from a dcel. 
        Can be the only thing drawn (clear=True),
        Can be drawn in the centre of the context for debugging (force_centre=True)
        """
        data = self.data.copy()
        if data_override is not None:
            assert(isinstance(data, dict))
            data.update(data_override)
        
        #early exits:
        if len(self.edgeList) < 2:
            return
        #Custom Clear
        if clear:
            clear_canvas(ctx)

        #Data Retrieval:
        lineWidth = WIDTH
        vertColour = START
        vertRad = SMALL_RADIUS
        faceCol = FACE
        radius = SMALL_RADIUS
        text_string = "F: {}".format(self.index)
        should_offset_text = FaceE.TEXT_OFFSET in data
        centroidCol = VERTEX
        drawCentroid = FaceE.CENTROID in data
        sampleDescr = None
    
        if drawCentroid and isinstance(data[FaceE.CENTROID], (list, np.ndarray)):
            centroidCol = data[FaceE.CENTROID]
        if FaceE.STARTVERT in data and isinstance(data[FaceE.STARTVERT], (list, np.ndarray)):
            vertColour = data[FaceE.STARTVERT]
        if FaceE.STARTRAD in data:
            vertRad = data[FaceE.STARTRAD]
        if FaceE.FILL in data and isinstance(data[FaceE.FILL], (list, np.ndarray)):
            faceCol = data[FaceE.FILL]
        if FaceE.CEN_RADIUS in data:
            radius = data[FaceE.CEN_RADIUS]
        if FaceE.TEXT in data:
            text_string = data[FaceE.TEXT]
        if FaceE.WIDTH in data:
            lineWidth = data[FaceE.WIDTH]
        if FaceE.SAMPLE in data:
            sampleDescr = data[FaceE.SAMPLE]

            
        #Centre to context
        midPoint = (self.dcel.bbox[2:] - self.dcel.bbox[:2]) * 0.5
        faceCentre = self.getCentroid()
        if force_centre:
            invCentre = -faceCentre
            ctx.translate(*invCentre)
            ctx.translate(*midPoint)

        if sampleDescr is not None:
            #draw as a sampled line
            sampleDescr(ctx, self)
            
        if FaceE.NULL in data:
            return
        
        ctx.set_line_width(lineWidth)
        ctx.set_source_rgba(*faceCol)
        #Setup Edges:
        initial = True
        for x in self.getEdges():
            v1, v2 = x.getVertices()
            assert(v1 is not None)
            assert(v2 is not None)
            logging.debug("Drawing Face {} edge {}".format(self.index, x.index))
            logging.debug("Drawing Face edge from ({}, {}) to ({}, {})".format(v1.loc[0], v1.loc[1],
                                                                               v2.loc[0], v2.loc[1]))
            if initial:
                ctx.move_to(*v1.loc)
                initial = False
            ctx.line_to(*v2.loc)

            #todo move this out
            if FaceE.STARTVERT in data:
                ctx.set_source_rgba(*vertColour)
                drawCircle(ctx, *v1.loc, vertRad)

            
        #****Draw*****
        if FaceE.FILL not in data:
            ctx.stroke()
        else:
            ctx.close_path()
            ctx.fill()


        #Drawing the Centroid point
        ctx.set_source_rgba(*END)
        if drawCentroid:
            ctx.set_source_rgba(*centroidCol)
            drawCircle(ctx, *faceCentre, radius)
        
        #Text Retrieval and drawing
        if text or FaceE.TEXT in data:
            drawText(ctx, *faceCentre, text_string, offset=should_offset_text)
        
        #Reset the forced centre
        if force_centre:
            ctx.translate(*(midPoint * -1))
            ctx.translate(*centre)
    
    #------------------------------
    # def Exporting
    #------------------------------
    
    
    def _export(self):
        """ Export identifiers rather than objects, to allow reconstruction """
        logging.debug("Exporting face: {}".format(self.index))
        enumData = {a.name:b for a,b in self.data.items() if a in FaceE}
        nonEnumData = {a:b for a,b in self.data.items() if a not in FaceE}

        return {
            'i' : self.index,
            'edges' : [x.index for x in self.edgeList if x is not None],
            'sitex' : self.site[0],
            'sitey' : self.site[1],
            "enumData" : enumData,
            "nonEnumData": nonEnumData
        }


            
    def get_bbox(self):
        """ Get a rough bbox of the face """
        #TODO: fix this? its rough
        vertices = [x.origin for x in self.edgeList]
        vertexArrays = [x.toArray() for x in vertices if x is not None]
        if not bool(vertexArrays):
            return np.array([[0, 0], [0, 0]])
        allVertices = np.array([x for x in vertexArrays])
        bbox = np.array([np.min(allVertices, axis=0),
                         np.max(allVertices, axis=0)])
        logging.debug("Bbox for Face {}  : {}".format(self.index, bbox))
        return bbox

    def markForCleanup(self):
        self.markedForCleanup = True
    
    #------------------------------
    # def centroids
    #------------------------------

    def getCentroid(self):
        """ Get the user defined 'centre' of the face """
        if self.site is not None:
            return self.site.copy()
        else:
            return self.getAvgCentroid()

    
    def getAvgCentroid(self):
        """ Get the averaged centre point of the face from the vertices of the edges """
        k = len(self.edgeList)
        coords = np.array([x.origin.loc for x in self.edgeList])
        norm_coord = np.sum(coords, axis=0) / k
        if self.site is None:
            self.site = norm_coord
        return norm_coord

    def getCentroidFromBBox(self):
        """ Alternate Centroid, the centre point of the bbox for the face"""
        bbox = self.get_bbox()
        difference = bbox[1,:] - bbox[0,:]
        centre = bbox[0,:] + (difference * 0.5)
        if self.site is None:
            self.site = centre
        return centre


    #------------------------------
    # def edge access
    #------------------------------
            
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
        if edge.face is self:
            return
        if edge.face is not self and edge.face is not None:
            edge.face.remove_edge(edge)
        self.coord_list = None
        edge.face = self
        if edge not in self.edgeList:
            self.edgeList.append(edge)
        edge.markedForCleanup = False

    def remove_edge(self, edge):
        """ Remove an edge from this face, if the edge has this face
        registered, remove that too """
        assert(isinstance(edge, HalfEdge))
        #todo: should the edge be connecting next to prev here?
        if not bool(self.edgeList):
            return
        if edge in self.edgeList:
            self.edgeList.remove(edge)
        if edge.face is self:
            edge.face = None
        if edge.twin is None or edge.twin.face is None:
            edge.markForCleanup()
        
    def sort_edges(self):
        """ Order the edges clockwise, by starting point, ie: graham scan """
        logging.debug("Sorting edges")
        centre = self.getCentroid()
        #verify all edges are ccw
        edges = self.edgeList.copy()
        for x in edges:
            if not x.he_ccw(centre):
                x.swapFaces()

        try:
            assert(all([x.he_ccw(centre) for x in self.edgeList]))
        except AssertionError as e:
            IPython.embed(simple_prompt=True)

        # withDegrees = [(x.degrees(centre), x) for x in self.edgeList]
        # withDegrees.sort()
        # self.edgeList = [hedge for (deg,hedge) in withDegrees]
        self.edgeList.sort()

    def has_edges(self):
        """ Check if its a null face or has actual edges """
        return bool(self.edgeList)


    #------------------------------
    # def modifiers
    #------------------------------
    
        
    def subdivide(self, edge, ratio=None, angle=0):
        """ Bisect / Divide a face in half by creating a new line
        on the ratio point of the edge, at the angle specified, until it intersects
        a different line of the face.
        Angle is +- from 90 degrees.
        returns the new face
        """
        self.sort_edges()
        if ratio is None:
            ratio = 0.5
        assert(isinstance(edge, HalfEdge))
        assert(edge in self.edgeList)
        assert(0 <= ratio <= 1)
        assert(-90 <= angle <= 90)
        #split the edge
        newPoint, newEdge = edge.split_by_ratio(ratio)

        #get the bisecting vector
        asCoords = edge.toArray()
        bisector = cumath.get_bisector(asCoords[0], asCoords[1])
        #get the coords of an extended line
        extended_end = cumath.extend_line(newPoint.toArray(), bisector, 1000)
        el_coords = np.row_stack((newPoint.toArray(), extended_end))

        #intersect with coords of edges
        intersection = None
        oppEdge = None
        for he in self.edgeList:
            if he in [edge, newEdge]:
                continue
            he_coords = he.toArray()
            intersection = cumath.intersect(el_coords, he_coords)
            if intersection is not None:
                oppEdge = he
                break
        assert(intersection is not None)
        assert(oppEdge is not None)
        #split that line at the intersection
        newOppPoint, newOppEdge = oppEdge.split(intersection)

        #create the other face
        newFace = self.dcel.newFace()
        
        #create the subdividing edge:
        dividingEdge = self.dcel.newEdge(newPoint, newOppPoint,
                                         face=self,
                                         twinFace=newFace,
                                         edata=edge.data,
                                         vdata=edge.origin.data)
        dividingEdge.addPrev(edge, force=True)
        dividingEdge.addNext(newOppEdge, force=True)
        dividingEdge.twin.addPrev(oppEdge, force=True)
        dividingEdge.twin.addNext(newEdge, force=True)

        #divide the edges into newOppEdge -> edge,  newEdge -> oppEdge
        newFace_Edge_Group = []
        originalFace_Edge_Update = []

        current = newOppEdge
        while current != edge:
            assert(current.next is not None)
            originalFace_Edge_Update.append(current)
            current = current.next
        originalFace_Edge_Update.append(current)
        originalFace_Edge_Update.append(dividingEdge)
        
        current = newEdge
        while current != oppEdge:
            assert(current.next is not None)
            newFace_Edge_Group.append(current)
            current.face = newFace
            current = current.next
        newFace_Edge_Group.append(current)
        current.face = newFace
        newFace_Edge_Group.append(dividingEdge.twin)        
        
        #update the two faces edgelists
        self.edgeList = originalFace_Edge_Update
        newFace.edgeList = newFace_Edge_Group

        #return both
        return (self, newFace)

    @staticmethod
    def merge_faces(*args):
        """ Calculate a convex hull from all passed in faces,
        creating a new face """
        assert(all([isinstance(x, Face) for x in args]))
        dc = args[0].dcel
        assert(dc is not None)
        all_verts = set()
        for f in args:
            all_verts.update(f.get_all_vertices())
        newFace = dc.newFace()
        #then build the convex hull
        hull, discarded = Face.hull_from_vertices(all_verts)
        for s,e in zip(hull, islice(cycle(hull),1, None)):
            #create an edge
            newEdge = dc.newEdge(s,e, face=newFace)
        #link the edges
        dc.linkEdgesTogether(newFace.edgeList, loop=True)
        #return the face
        return (newFace, discarded)
        
    def translate_edge(self, transform, e=None, i=None, candidates=None, force=False):
        assert(e is None or e in self.edgeList)
        assert(i is None or 0 <= i < len(self.edgeList))
        assert(not (e is None and i is None))
        assert(isinstance(transform, np.ndarray))
        assert(transform.shape == (2,))
        if i is None:
            i = self.edgeList.index(e)    

        if not force and self.has_constraints(candidates):
            copied, edit_e = self.copy().translate_edge(transform, i=i, force=True)
            return (copied, EditE.NEW)

        self.edgeList[i].translate(transform, force=True)
        return (self, EditE.MODIFIED)
        

    def scale(self, amnt=None, target=None, vert_weights=None, edge_weights=None,
              force=False, candidates=None):
        """ Scale an entire face by amnt,
        or scale by vertex/edge normal weights """
        if not force and self.has_constraints(candidates):
            facePrime, edit_type = self.copy().scale(amnt=amnt, target=target,
                                                     vert_weights=vert_weights,
                                                     edge_weights=edge_weights,
                                                     force=True)
            return (facePrime, EditE.NEW)

        if target is None:
            target = self.getCentroidFromBBox()
        if amnt is None:
            amnt = np.ndarray([1,1])
        assert(isinstance(amnt, np.ndarray))
        assert(amnt.shape == (2,))
        if vert_weights is not None:
            assert(isinstance(vert_weights, np.ndarray))
        if edge_weights is not None:
            assert(isinstance(edge_weights, np.ndarray))

        verts = self.get_all_vertices()
        for vert in verts:
            loc = vert.loc.copy()
            loc -= target
            loc *= amnt
            loc += target
            vert.translate(loc, abs=True, force=True)
            
        return (self, EditE.MODIFIED)
        

    def cut_out(self, candidates=None, force=False):
        """ Cut the Face out from its verts and halfedges that comprise it,
        creating new verts and edges, so the face can be moved and scaled
        without breaking the already existing structure """
        if not force and self.has_constraints(candidates):
            return (self.copy(), EditE.NEW)
        else:
            return (self, EditE.MODIFIED)

    def rotate(self, rads, target=None, candidates=None, force=False):
        """ copy and rotate the entire face by rotating each point """
        assert(-TWOPI <= rads <= TWOPI)
        if not force and self.has_constraints(candidates):
            facePrime, edit_e = self.copy().rotate(rads, target=target, force=True)
            return (facePrime, EditE.NEW)
            
        if target is None:
            target = self.getCentroidFromBBox()
        assert(isinstance(target, np.ndarray))
        assert(target.shape == (2,))

        for l in self.edgeList:
            l.rotate(c=target, r=rads, candidates=candidates, force=True)
        return (self, EditE.MODIFIED)


    def constrain_to_circle(self, centre, radius, candidates=None, force=False):
        """ Constrain the vertices and edges of a face to be within a circle """
        if not force and self.has_constraints(candidates):
            logging.debug("Face: Constraining a copy")
            facePrime, edit_type = self.copy().constrain_to_circle(centre, radius, force=True)
            return (facePrime, EditE.NEW)

        logging.debug("Face: Constraining edges")
        #constrain each edge            
        edges = self.edgeList.copy()        
        for e in edges:
            logging.debug("HE: {}".format(e))
            eprime, edit_e = e.constrain_to_circle(centre, radius, force=True)
            logging.debug("Result: {}".format(eprime))
            assert(edit_e == EditE.MODIFIED)
            assert(eprime in self.edgeList)
            if eprime.markedForCleanup:
                self.edgeList.remove(eprime)

        return (self, EditE.MODIFIED)

    #todo: possibly add a shrink/expand to circle method

    def constrain_to_bbox(self, bbox, candidates=None, force=False):
        if not force and self.has_constraints(candidates):
            facePrime, edit_type = self.copy().constrain_to_bbox(bbox, force=True)
            return (facePrime, EditE.NEW)
            
        edges = self.edgeList.copy()

        for edge in edges:
            if edge.outside(bbox):
                self.remove_edge(edge)
                continue

            eprime, edit_e = edge.constrain_to_bbox(bbox, candidates=candidates, force=True)

        return (self, EditE.MODIFIED)


            
    #------------------------------
    # def Vertex access
    #------------------------------
        
    def add_vertex(self, vert):
        """ Add a vertex, then recalculate the convex hull """
        assert(isinstance(vert, Vertex))
        self.free_vertices.add(vert)
        self.coord_list = None

    def get_all_vertices(self):
        """ Get all vertices of the face. both free and in halfedges """
        all_verts = set()
        all_verts.update(self.free_vertices)
        for e in self.edgeList:
            all_verts.update(e.getVertices())
        return all_verts

    def get_all_coords(self):
        """ Get the sequence of coordinates for the edges """
        if self.coord_list is not None:
            return self.coord_list
        all_coords = np.array([x.toArray() for x in self.get_all_vertices()])
        self.coord_list = Face.hull_from_coords(all_coords)
        return self.coord_list


    #------------------------------
    # def verification
    #------------------------------
        
    def fixup(self, bbox=None):
        """ Verify and enforce correct designations of
        edge ordering, next/prev settings, and face settings """
        assert(bbox is not None)
        if not bool(self.edgeList):
            self.markForCleanup()
            return []
        if len(self.edgeList) < 2:
            return []

        for e in self.edgeList:
            self.add_edge(e)

        altered = False
        centre = self.getCentroid()
        avgCentre = self.getAvgCentroid()
        if not within_bbox(centre, bbox) and within_bbox(avgCentre, bbox):
            altered = True
            self.site = avgCentre
            
        self.sort_edges()
        
        inferred_edges = []
        edges = self.edgeList.copy()
        prev = edges[-1]
        for e in edges:
            #enforce next and prev
            if e.prev is not prev:
                e.addPrev(prev, force=True)
            #if verts don't align AND they intersect the border of the bbox on separate edges:
            dontAlign = not prev.connections_align(e)
            if dontAlign:
                logging.debug("connections don't align")
                newEdge = self.dcel.newEdge(e.prev.twin.origin,
                                            e.origin,
                                            edata=e.data,
                                            vdata=e.origin.data)
                newEdge.face = self
                newEdge.addPrev(e.prev, force=True)
                newEdge.addNext(e, force=True)
                #insert that new edge into the edgeList
                index = self.edgeList.index(e)
                self.edgeList.insert(index, newEdge)
                inferred_edges.append(newEdge)

                #if the newEdge connects two different sides, split it and
                #force the middle vertex to the corner
                nib = newEdge.intersects_bbox(bbox)
                edgeEs = set([ev for (coord, ev) in nib])
                if len(nib) == 2 and len(edgeEs) > 1:
                    newPoint, newEdge2 = newEdge.split_by_ratio(0.5, face_update=False)
                    newEdge2.face = self
                    self.edgeList.insert(index+1, newEdge2)
                    # if newEdge.twin.face is not None:
                    #     newEdge.twin.face.add_edge(newEdge2.twin)
                    
                    moveToCoord = calc_bbox_corner(bbox, edgeEs)
                    newPoint.translate(moveToCoord, abs=True, force=True)

            prev = e

        self.sort_edges()

        if altered:
            self.site = centre
        
        return inferred_edges

    def has_constraints(self, candidateSet=None):
        """ Tests whether the face's component edges and vertices are claimed by
        anything other than the face's own halfedges and their twins, and any passed in 
        candidates """
        if candidateSet is None:
            candidateSet = set()
        candidatesPlusSelf = candidateSet.union([self], self.edgeList, [x.twin for x in self.edgeList if x.twin is not None])
        return any([x.has_constraints(candidatesPlusSelf) for x in self.edgeList])

    def are_points_within(self, points):
        assert(isinstance(points, np.ndarray))
        #see https://stackoverflow.com/questions/217578
        raise Exception("Unimplemented: are_points_within")
    
        
    #------------------------------
    # def deprecated
    #------------------------------
    
    
    def __getCentroid(self):
        """ An iterative construction of the centroid """
        raise Exception("Deprecated: use getavgcentroid or getcentroidfrombbox")
