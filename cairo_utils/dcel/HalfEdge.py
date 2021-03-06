""" HalfEdge: The intermediate level datastructure of the dcel """
import sys
import logging as root_logger
from math import pi, atan2, copysign, degrees
import numpy as np
import IPython
from itertools import islice, cycle
from ..math import inCircle, get_distance, intersect, sampleAlongLine, get_unit_vector, extend_line, rotatePoint, is_point_on_line, get_distance_raw, bbox_to_lines, get_midpoint, getRanges
from ..constants import TWOPI, IntersectEnum, EPSILON, TOLERANCE, START, END, SMALL_RADIUS, FACE, EDGE, VERTEX, WIDTH, D_EPSILON
from ..drawing import drawRect, drawCircle, clear_canvas, drawText
from .constants import EditE, EDGE_FOLLOW_GUARD, EdgeE, SampleFormE
from .Vertex import Vertex
from .Line import Line
from .Drawable import Drawable

logging = root_logger.getLogger(__name__)

PI = pi
TWOPI = 2 * PI
HALFPI = PI * 0.5
QPI = PI * 0.5

class HalfEdge(Drawable):
    """ A Canonical Half-Edge. Has an origin point, and a twin
    	half-edge for its end point,
        Auto-maintains counter-clockwise vertex order with it's twin.
    	Two HalfEdges make an Edge
    """
    nextIndex = 0

    def __init__(self, origin=None, twin=None, index=None, data=None, dcel=None):
        assert(origin is None or isinstance(origin, Vertex))
        assert(twin is None or isinstance(twin, HalfEdge))
        self.origin = origin
        self.twin = twin
        self.length_sq = -1
        #need to generate new faces:
        self.face = None
        #connected edges:
        self.next = None
        self.prev = None
        self.dcel=dcel

        if index is None:
            logging.debug("Creating Edge {}".format(HalfEdge.nextIndex))
            self.index = HalfEdge.nextIndex
            HalfEdge.nextIndex += 1
        else:
            assert(isinstance(index, int))
            logging.debug("Re-creating Edge: {}".format(index))
            self.index = index
            if self.index >= HalfEdge.nextIndex:
                HalfEdge.nextIndex = self.index + 1

        #register the halfedge with the vertex
        if origin is not None:
            self.origin.registerHalfEdge(self)

        #Additional:
        self.markedForCleanup = False
        self.constrained = False
        self.drawn = False
        self.fixed = False
        self.data = {}
        if data is not None:
            self.data.update(data)
        if self.dcel is not None and self not in self.dcel.halfEdges:
            self.dcel.halfEdges.add(self)

    def eq_verts(self, other):
        assert(isinstance(other, HalfEdge))
        sVerts = self.getVertices()
        oVerts = other.getVertices()
        return all([s == o for s,o in zip(sVerts,oVerts)])

    def copy(self):
        """ Copy the halfedge pair. sub-copies the vertexs too """
        assert(self.origin is not None)
        assert(self.twin is not None)
        #copy the vertices
        v1 = self.origin.copy()
        v2 = self.twin.origin.copy()
        #create the halfedge
        e = self.dcel.newEdge(v1, v2)
        #update next/prev?
        
        #copy data
        e.data.update(self.data)
        return e
            
        

    #------------------------------
    # def export
    #------------------------------
    
    
    def _export(self):
        """ Export identifiers instead of objects to allow reconstruction """
        logging.debug("Exporting Edge: {}".format(self.index))
        origin = self.origin
        if origin is not None:
            origin = origin.index
        twin = self.twin
        if twin is not None:
            twin = twin.index
        face = self.face
        if face is not None:
            face = face.index
        nextHE = None
        prevHE = None
        if self.next is not None:
            nextHE = self.next.index
        if self.prev is not None:
            prevHE = self.prev.index
        enumData = {a.name:b for a,b in self.data.items() if a in EdgeE}
        nonEnumData = {a:b for a,b in self.data.items() if a not in EdgeE}

            
        return {
            'i' : self.index,
            'origin' : origin,
            'twin' : twin,
            'face' : face,
            'next' : nextHE,
            'prev' : prevHE,
            "enumData" : enumData,
            "nonEnumData": nonEnumData
        }

    #------------------------------
    # def Human Readable Representations
    #------------------------------
    
    def __str__(self):
        return "HalfEdge {}: {} - {}".format(self.index, self.origin, self.twin.origin)

    def __repr__(self):
        origin = "n/a"
        twin = "n/a"
        if self.origin is not None:
            origin = self.origin.index
        if self.twin is not None:
            twin = self.twin.index
        n = "n/a"
        p = "n/a"
        if self.next is not None:
            n = self.next.index
        if self.prev is not None:
            p = self.prev.index
        f = "n/a"
        if self.face is not None:
            f = self.face.index
            
        coords = [str(x) for x in self.getVertices()]

        data = (self.index, f, origin, twin, p, n, coords)
        return "(HE: {}, f: {}, O: {}, T: {}, P: {}, N: {}, XY: {})".format(*data)

    def draw(self, ctx, data_override=None, clear=False, text=False, width=None):
        logging.debug("Drawing Edge: {} | {}".format(self.index, self.twin.index))
        if clear:
            clear_canvas(ctx)
        data = self.data.copy()
        if data_override is not None:
            assert(isinstance(data_override, dict))
            data.update(data_override)

        #defaults
        colour = EDGE
        startEndPoints = False
        startCol = START
        endCol = END
        startRad = width
        endRad = width
        writeText = "HE:{}.{}".format(self.index, self.twin.index)
        bezier = False
        bezier_simp = False
        sampleDescr = None
        
        #retrieve custom values
        if EdgeE.WIDTH in data:
            width = data[EdgeE.WIDTH]
            startRad = width
            endRad = width
        if EdgeE.STROKE in data:
            colour = data[EdgeE.STROKE]
        if EdgeE.START in data and isinstance(data[EdgeE.START], (list, np.ndarray)):
            startCol = data[EdgeE.START]
        if EdgeE.END in data and isinstance(data[EdgeE.END], (list, np.ndarray)):
            endCol = data[EdgeE.END]
        if EdgeE.START in data and EdgeE.END in data:
            startEndPoints = True
        if EdgeE.STARTRAD in data:
            startRad = data[EdgeE.STARTRAD]
        if EdgeE.ENDRAD in data:
            endRad = data[EdgeE.ENDRAD]
        if EdgeE.TEXT in data:
            if isinstance(data[EdgeE.TEXT], str):
                writeText = data[EdgeE.TEXT]
            elif data[EdgeE.TEXT] == False:
                writeText = None
        if EdgeE.BEZIER in data:
            bezier = data[EdgeE.BEZIER]
            assert(isinstance(bezier, list))
        if EdgeE.BEZIER_SIMPLIFY in data:
            bezier_simp = True
        if EdgeE.SAMPLE in data:
            sampleDescr = data[EdgeE.SAMPLE]

        #Get Start and end points
        v1, v2 = self.getVertices()
        if v1 is None or v2 is None:
            #early exit if line is not completed
            return
        centre = get_midpoint(v1.toArray(), v2.toArray())
        logging.debug("Drawing HalfEdge {} : {}, {} - {}, {}".format(self.index,
                                                                     v1.loc[0],
                                                                     v1.loc[1],
                                                                     v2.loc[0],
                                                                     v2.loc[1]))
        sample_data = None
        if sampleDescr is not None:
            #draw as a sampled line
            sampleDescr(ctx, self)

        if EdgeE.NULL in data:
            return 

        ctx.set_line_width(width)
        ctx.set_source_rgba(*colour)
        
        #draw as a line/curve
        #todo: allow beziers to be simplified to straight lines
        if bool(bezier):
            logging.debug("Drawing Bezier: {}".format(bezier))
            ctx.new_path()
            for b in bezier:
                ctx.move_to(*b[0])
                if bezier_simp:
                    ctx.line_to(*b[-1])
                    continue
                if len(b) == 3:
                    ctx.curve_to(*b[0], *b[1], *b[2])
                else:
                    assert(len(b) == 4)
                    ctx.curve_to(*b[1], *b[2], *b[3])

        else:
            logging.debug("Drawing Straight Line")
            ctx.move_to(*v1.loc)
            ctx.line_to(*v2.loc)

        ctx.stroke()
    
        if startEndPoints:
            ctx.set_source_rgba(*startCol)
            drawCircle(ctx, *v1.loc, startRad)
            ctx.set_source_rgba(*endCol)
            drawCircle(ctx, *v2.loc, endRad)

        if text and writeText is not None:
            drawText(ctx, *centre, writeText)

    
    #------------------------------
    # def Math
    #------------------------------

    def cross(self):
        """ Cross product of the halfedge """
        assert(self.origin is not None)
        assert(self.twin is not None)
        assert(self.twin.origin is not None)
        a = self.origin.toArray()
        b = self.twin.origin.toArray()
        return np.cross(a,b)
    
    def getLength_sq(self, force=False):
        """ Gets the calculated length, or calculate it. returns as a np.ndarray"""
        if not force and self.length_sq is not -1:
            return self.length_sq
        #otherwise calculate
        asArray = self.toArray()
        self.length_sq = get_distance_raw(asArray[0], asArray[1])
        return self.length_sq

    #------------------------------
    # def Modifiers
    #------------------------------
    
    def split(self, loc, copy_data=True, face_update=True):
        """ Take an s -> e, and make it now two edges s -> (x,y) -> e 
        returns (firstHalf, newPoint, secondHalf)"""
        assert(isinstance(loc, (np.ndarray,Vertex)))
        start = self.origin
        end = self.twin.origin
        if isinstance(loc,Vertex):
            newPoint = loc
        else:
            newPoint = self.dcel.newVertex(loc)
        if copy_data:
            newPoint.data.update(start.data)
        newEdge = self.dcel.newEdge(newPoint, end)
        if copy_data:
            newEdge.data.update(self.data)
        #update the twin
        self.twin.origin = newPoint
        #update registrations:
        end.unregisterHalfEdge(self)
        newPoint.registerHalfEdge(self)
        newPoint.registerHalfEdge(self.twin)
        end.unregisterHalfEdge(self.twin)
        end.registerHalfEdge(newEdge.twin)
        #recalculate length
        self.getLength_sq(force=True)
        self.twin.getLength_sq(force=True)
        #insert into next/prev ordering
        newEdge.addNext(self.next, force=True)
        newEdge.twin.addPrev(self.twin.prev, force=True)
        self.addNext(newEdge, force=True)
        newEdge.twin.addNext(self.twin, force=True)
        #update faces
        if face_update and self.face is not None:
            self.face.add_edge(newEdge)
        if face_update and self.twin.face is not None:
            self.twin.face.add_edge(newEdge.twin)
        return (newPoint, newEdge)

    def split_by_ratio(self, r=0.5, face_update=True):
        """ Split an edge by a ratio of 0.0 - 1.0 : start - end.
        defaults to 0.5, the middle """
        point = sampleAlongLine((self.toArray().flatten()), np.array([r]))[0]
        return self.split(point[0], face_update=face_update)

    def translate(self, dir, d=1, abs=False, candidates=None, force=False):
        """ Move the edge by a vector and distance, or to an absolute location """
        assert(isinstance(dir, np.ndarray))
        if not abs:
            target = self.toArray() + (dir * d)
        else:
            assert(dir.shape == (2,2))
            target = dir

        if not force and self.has_constraints(candidates):
            return (self.dcel.createEdge(target[0],
                                      target[1],
                                      edata=self.data,
                                      vdata=self.origin.data), EditE.NEW)
        else:
            vert1, edit1 = self.origin.translate(target[0], abs=True, force=True)
            vert2, edit2 = self.twin.origin.translate(target[1], abs=True, force=True)
            assert(edit1 == edit2)
            assert(edit1 == EditE.MODIFIED)
            return (self, EditE.MODIFIED)

        
    def extend(self, target=None, direction=None, rotate=None, d=1, inSequence=True):
        """ Extend the line with a new line in the direction of 'target',
        or in the normalized direction 'direction', by distance d. 
        if no target or direction is passed in, it extends in the line direction """
        start = self.origin.toArray()
        end = self.twin.origin.toArray()
        newEnd = None
        if sum([1 for x in [target, direction, rotate] if x is not None]) > 1:
            raise Exception("HalfEdge.extend: Specify only one of target, direction, rotate")
        if target is not None:
            assert(isinstance(target, np.ndarray))
            assert(len(target) == 2)
            if d is not None:
                newEnd = extend_line(end, target, d, fromStart=False)
            else:
                newEnd = target
        elif direction is not None:
            #use the direction raw
            assert(hasattr(direction, "__len__"))
            assert(len(direction) == 2)
            assert(d is not None)
            newEnd = extend_line(end, end + direction, d)
        elif rotate is not None:
            #rotate the vector of the existing line and extend by that
            unit_vector = get_unit_vector(start, end)
            rotated = rotatePoint(unit_vector, np.array([0,0]), rads=rotate)
            newEnd = extend_line(end, end + rotated, d)
        else:
            assert(d is not None)
            #get the normalized direction of self.origin -> self.twin.origin
            newEnd = extend_line(start, end, fromStart=False)
        #Then create a point at (dir * d), create a new edge to it
        newVert = self.dcel.newVertex(newEnd)

            #todo: twinNext is the next ccw edge for the correct face
            
        newEdge = self.dcel.newEdge(self.twin.origin, newVert, edata=self.data, vdata=self.origin.data)
        newEdge.fix_faces(self)

        return newEdge

    def rotate(self, c=None, r=0, candidates=None, force=False):
        """ return Rotated coordinates as if the edge was rotated around a point by rads """
        assert(isinstance(c, np.ndarray))
        assert(c.shape == (2,))
        assert(-TWOPI <= r <= TWOPI)
        asArray = self.toArray()
        rotatedCoords = rotatePoint(asArray, cen=c, rads=r)
        
        if not force and self.has_constraints(candidates):
            return (self.dcel.createEdge(rotatedCoords[0],
                                         rotatedCoords[1],
                                         edata=self.data,
                                         vdata=self.origin.data), EditE.NEW)
        else:
            vert1, edit1 = self.origin.translate(rotatedCoords[0], abs=True, force=True)
            vert2, edit2 = self.twin.origin.translate(rotatedCoords[1], abs=True, force=True)
            assert(edit1 == edit2)
            assert(edit1 == EditE.MODIFIED)
            return (self, EditE.MODIFIED)

    def constrain_to_circle(self, centre, radius, candidates=None, force=False):
        """ Modify or create a new edge that is constrained to within a circle,
        while also marking the original edge for cleanup if necessary """
        #todo: handle sequences
        assert(isinstance(centre, np.ndarray))
        assert(centre.shape == (2,))
        assert(0 <= radius)
        results = self.within_circle(centre, radius)
        logging.debug("HE: within_circle? {}".format(results))
        if all(results):
            #nothing needs to be done
            logging.debug("HE: fine")
            return (self, EditE.MODIFIED)
        if not any(results):
            logging.debug("HE: to remove")
            self.markForCleanup()
            return (self, EditE.MODIFIED)

        closer, further = self.getCloserAndFurther(centre)
        asLine = Line.newLine(np.array([closer.toArray(), further.toArray()]))
        intersections = asLine.intersect_with_circle(centre, radius)

        distances = get_distance_raw(further.toArray(), intersections)
        closest = intersections[np.argmin(distances)]
        vertTarget = None
        
        if not force and self.has_constraints(candidates):
            edit_e = EditE.NEW
            vertTarget = self.dcel.newVertex(closest)
            target = self.copy()
            self.markForCleanup()
        else:
            edit_e = EditE.MODIFIED
            target = self

        if further == self.origin:
            if vertTarget is not None:
                target.replaceVertex(vertTarget)
            else:
                target.origin.loc = closest
        else:
            if vertTarget is not None:
                target.twin.replaceVertex(vertTarget)
            else:
                target.twin.origin.loc = closest

                
        return (target, edit_e)

    def constrain_to_bbox(self, bbox, candidates=None, force=False):
        if not force and self.has_constraints(candidates):
            edgePrime, edit_e = self.copy().constrain_to_bbox(bbox, force=True)
            return (edgePrime, EditE.NEW)
        
        #get intersections with bbox
        intersections = self.intersects_bbox(bbox)
        verts = self.getVertices()
        vertCoords = self.toArray()

        if self.within(bbox):
            logging.debug("Ignoring halfedge: is within bbox")
        elif self.outside(bbox):
            self.markForCleanup()        
        elif len(intersections) == 0:
            raise Exception("Edge Constraining: Part in and out, with no intersection")
        elif len(intersections) == 1:
            logging.debug("One intersection, moving outside vertex")
            intersect_coords, intersectE = intersections[0]
            outsideVerts = [x for x in verts if not x.within(bbox)]
            assert(len(outsideVerts) == 1)
            if outsideVerts[0] == self.origin:
                d = self.origin.data
                target = self
            else:
                d = self.twin.origin.data
                target = self.twin
            newVert = self.dcel.newVertex(intersect_coords, data=d)
            target.replaceVertex(newVert)

        elif len(intersections) == 2:
            logging.debug("Two intersections, moving both vertices")
            for i_c, i_e in intersections:
                vertToMove = verts[np.argmin(get_distance_raw(vertCoords, i_c))]
                if vertToMove == self.origin:
                    d = self.origin.data
                    target = self
                else:
                    d = self.twin.origin.data
                    target = self.twin
                newVert = self.dcel.newVertex(intersect_coords, data=d)
                target.replaceVertex(newVert)
        

        return (self, EditE.MODIFIED)

        
    
    
    #------------------------------
    # def Comparison
    #------------------------------
    
    def intersect(self, otherEdge):
        """ Intersect two edges mathematically,
        returns intersection point or None """
        assert(isinstance(otherEdge, HalfEdge))
        lineSegment1 = self.toArray()
        lineSegment2 = otherEdge.toArray()
        return intersect(lineSegment1, lineSegment2)

    def intersects_bbox(self, bbox, tolerance=TOLERANCE):
        """ Return an enum of the edges of a bbox the line intersects
        returns a cairo_utils.constants.IntersectEnum
        returns a list. empty list is no intersections
        
            bbox is [min_x, min_y, max_x, max_y]
        """
        #calculate intersection points for each of the 4 edges of the bbox,
        #return as tuple of tuples: [( IntersectEnum, np.array(coordinates) )]
        
        assert(isinstance(bbox, np.ndarray))
        assert(len(bbox) == 4)
        if self.origin is None or self.twin.origin is None:
            raise Exception("Invalid line boundary test ")
        #adjust the bbox by an epsilon? not sure why. TODO: test this
        bbox_lines = bbox_to_lines(bbox)
        selfLineSegment = self.toArray()
        start, end = self.toArray()

        logging.debug("Checking edge intersection:\n {}\n {}\n->{}\n----".format(start,
                                                                                 end,
                                                                                 bbox))
        result = []
        #run the 4 intersections
        for (curr_line, enumValue) in bbox_lines:
            intersected = intersect(selfLineSegment, curr_line, tolerance=tolerance)
            if intersected is not None:
                result.append((intersected, enumValue))

        assert(len(result) < 3)
        return result


    def point_is_on_line(self, point):
        """ Test to see if a particular x,y coord is on a line """
        assert(isinstance(point, np.ndarray))
        assert(point.shape == (2,))
        coords = self.toArray()
        return is_point_on_line(point, coords)


    def __call__(self, x=None, y=None):
        """ Pass in a value and calculate the other """
        assert(any([a is not None for a in [x,y]]))
        assert(not all([a is not None for a in [x,y]]))
        theLine = Line.newLine(self.toArray())
        return theLine(x=x, y=y)

    def getRanges(self):
        arr = getRanges(self.toArray())
        return arr
    
    @staticmethod
    def compareEdges(center, a, b):
        """ Compare two halfedges against a centre point, returning whether a is CCW, equal, or CW from b 
        """
        assert(isinstance(center, np.ndarray))
        assert(isinstance(a, HalfEdge))
        assert(isinstance(b, HalfEdge))

        offset_a = a.origin.toArray() - center
        offset_b = b.origin.toArray() - center

        deg_a = (degrees(atan2(offset_a[1], offset_a[0])) + 360) % 360
        deg_b = (degrees(atan2(offset_b[1], offset_b[0])) + 360) % 360

        return deg_a <= deg_b

    def degrees(self, centre):
        offset = self.origin.toArray() - centre
        deg = (degrees(atan2(offset[1], offset[0])) + 360) % 360
        return deg
    
    @staticmethod
    def ccw(a, b, c):
        """ Test for left-turn on three points of a triangle """
        assert(all([isinstance(x, np.ndarray) for x in [a,b,c]]))
        offset_b = b - a
        offset_c = c - a
        crossed = np.cross(offset_b, offset_c)
        return crossed >= 0

    @staticmethod
    def ccw_e(a, b, c):
        """ Test a centre point and two halfedges for ccw ordering """
        assert(isinstance(a, np.ndarray))
        assert(isinstance(b, HalfEdge))
        assert(isinstance(c, HalfEdge))
        firstOrigin = b.origin.toArray()
        secondOrigin = c.origin.toArray()
        offset_b = firstOrigin - a
        offset_c = secondOrigin - a
        crossed = np.cross(offset_b, offset_c)
        return crossed

    def __lt__(self, other):
        return HalfEdge.compareEdges(self.face.getCentroid(), self, other)

    
    def he_ccw(self, centre):
        """ Verify the halfedge is ccw ordered """
        assert(isinstance(centre, np.ndarray))
        return HalfEdge.ccw(centre, self.origin.toArray(), self.twin.origin.toArray())

    def isUpper(self):
        verts = self.getVertices()
        return verts[0] < verts[1]

    def isFlat(self):
        arr = self.toArray()
        return arr[0,1] == arr[1,1]
    
    def contains_vertex(self, vert, tolerance=D_EPSILON):
        assert(isinstance(vert, Vertex))
        verts = self.toArray()
        if vert in verts:
            return True
        l = self.toArray()
        p = vert.toArray()
        return is_point_on_line(p, l)
        # l = Line.newLine(verts)
        # xprime = l(y=vert.loc[1])[0]
        # diff = abs(vert.loc[0]) - abs(xprime)
        # return -(tolerance) <= diff <= tolerance
        

    #------------------------------
    # def Utilities
    #------------------------------

    @staticmethod
    def avg_direction(edges):
        """ Get the average normalised direction vector of each component of the 
        total line segment """
        assert(isinstance(edges, list))
        assert(all([isinstance(x, HalfEdge) for x in edges]))
        allLines = [Line.newLine(x.toArray()) for x in edges]
        allDirections = np.array([x.direction for x in allLines])
        direction = allDirections.sum(axis=0) / len(edges)
        return direction

    def vertex_intersections(self, e=EPSILON):
        """ Create a bbox for the total line segment, and intersect check that with the
        dcel quadtree """
        raise Exception("Unimplemented")

    def follow_sequence(self, backwards=False, guard=EDGE_FOLLOW_GUARD):
        """ Follow the .next or .prev chain to completion or loop """
        count = 1
        edges = [self]
        getter = lambda x: x.next
        if backwards:
            getter = lambda x: x.prev
        current = getter(self)
        #todo: possibly use a set and stop on any loop
        while count < guard and current is not None and current is not self:
            edges.append(current)
            current = getter(current)
            count += 1

        return edges

        

    
    #------------------------------
    # def Verification
    #------------------------------

    def fix_faces(self, originator):
        """ Infer faces by side on a vertex,
        leftmost means to fix on the right instead """
        extended_from = originator
        allTwins = [x.twin.origin for x in self.origin.halfEdges]
        edgeLookup = {x.twin.origin : x.twin for x in self.origin.halfEdges}
        assert(extended_from.origin in allTwins)
        ordered = self.dcel.orderVertices(self.origin.loc, allTwins)
        extended_index = ordered.index(extended_from.origin)
        zipped = zip(islice(cycle(ordered), extended_index, len(ordered) + extended_index),
                     islice(cycle(ordered), extended_index+1, len(ordered) + extended_index + 1))
                       

        for a,b in zipped:
            a_edge = edgeLookup[a]
            b_edge = edgeLookup[b]
            a_edge.twin.addPrev(b_edge, force=True)

        if self.prev.face is None:
            new_face = self.dcel.newFace()
            new_face.add_edge(self.prev)
        if originator.twin.face is None:
            orig_twin_face = self.dcel.newFace()
            orig_twin_face.add_edge(originator.twin)

            
        self.prev.face.add_edge(self)
        f2_sequence = self.twin.follow_sequence()
        if originator.twin in f2_sequence:
            originator.twin.face.add_edge(self.twin)
        else:
            twin_face = self.dcel.newFace()
            for e in f2_sequence:
                self.prev.face.remove_edge(e)
                twin_face.add_edge(e)

            

        
    
    def has_constraints(self, candidateSet=None):
        """ Tests whether the halfedge, and its vertices, are used by things other than the
        faces, halfedges, and vertices passed in as the candidate set """
        if candidateSet is None:
            candidateSet = set()
        assert(isinstance(candidateSet, set))
        if self.twin is not None:
            candidatesPlusSelf = candidateSet.union([self, self.twin])
        else:
            candidatesPlusSelf = candidateSet.union([self])
        isConstrained = self.face is not None and self.face not in candidatesPlusSelf
        if self.origin is not None:
            isConstrained = isConstrained \
                            or self.origin.has_constraints(candidatesPlusSelf)
        if self.twin is not None:
            if self.twin.face is not None:
                isConstrained = isConstrained or self.twin.face not in candidatesPlusSelf
            if self.twin.origin is not None:
                isConstrained = isConstrained \
                                or self.twin.origin.has_constraints(candidatesPlusSelf)
        return isConstrained

    def isInfinite(self):
        """ If a halfedge has only one defined point, it stretches
            off into infinity """
        return self.origin is None or self.twin is None or self.twin.origin is None
    
    def connections_align(self, other):
        """ Verify that this and another halfedge's together form a full edge """
        assert(isinstance(other, HalfEdge))
        if self.twin.origin is None or other.origin is None:
            raise Exception("Invalid connection test")
        
        return self.twin.origin == other.origin
        
    def isConstrained(self):
        """ Check whether the edge has been forced within a bbox or circle"""
        return self.constrained or self.twin.constrained

    def setConstrained(self):
        """ Mark the full edge as forced within a bbox or circle """
        self.constrained = True
        self.twin.constrained = True

    def within(self, bbox):
        """ Check that both points in an edge are within the bbox """
        assert(isinstance(bbox, np.ndarray))
        assert(len(bbox) == 4)
        return self.origin.within(bbox) and self.twin.origin.within(bbox)

    def within_circle(self, centre, radius):
        points = self.toArray()
        return inCircle(centre, radius, points)
    
    def outside(self, bbox):
        verts = [x for x in self.getVertices() if x is not None]
        return all([x.outside(bbox) for x in verts])

    
    def to_constrained(self, bbox):
        """ get the coords of the half-edge to within the
            bounding box of [min_x, min_y, max_x, max_y]
        """
        assert(self.origin is not None)
        assert(self.twin is not None)
        assert(self.twin.origin is not None)

        #Convert to an actual line representation, for intersection
        logging.debug("Constraining {} - {}".format(self.index, self.twin.index))
        asLine = Line.newLine(self.toArray())
        return asLine.constrain(*bbox)

    def swapFaces(self):
        """ Swap the registered face between the halfedges, to keep the halfedge
        as the external boundary of the face, and ordered ccw  """
        assert(self.face is not None)
        assert(self.twin is not None)
        #assert(self.twin.face is not None)
        originFace = self.face
        twinFace = self.twin.face
        originFace.remove_edge(self)
        if twinFace is not None:
            twinFace.remove_edge(self.twin)
            twinFace.add_edge(self)
        originFace.add_edge(self.twin)


    #------------------------------
    # def Vertex Access
    #------------------------------
    
    def addVertex(self, vertex):
        """ Place a vertex into the first available slot of the full edge """
        assert(isinstance(vertex, Vertex))
        if self.origin is None:
            self.origin = vertex
            self.origin.registerHalfEdge(self)
        elif self.twin.origin is None:
            self.twin.origin = vertex
            self.twin.origin.registerHalfEdge(self.twin)
        else:
            raise Exception("trying to add a vertex to a full edge")

    def clearVertices(self):
        """ remove vertices from the edge, clearing the vertex->edge references as well   """
        v1 = self.origin
        v2 = None
        self.origin = None
        if self.twin is not None:
            v2 = self.twin.origin
            self.twin.origin = None

        if v1 is not None:
            logging.debug("Clearing vertex {} from edge {}".format(v1.index, self.index))
            v1.unregisterHalfEdge(self)
        if v2 is not None:
            logging.debug("Clearing vertex {} from edge {}".format(v2.index, self.twin.index))
            v2.unregisterHalfEdge(self.twin)
        

    def replaceVertex(self, newVert):
        """ Replace the vertex of this halfedge with a new one, unregistering the old """
        assert(isinstance(newVert, Vertex))
        self.origin.unregisterHalfEdge(self)
        self.origin = newVert
        self.origin.registerHalfEdge(self)
               
            
    def getVertices(self):
        """ Get a tuple of the vertices of this halfedge """
        if self.twin is None:
            return (self.origin, None)
        return (self.origin, self.twin.origin)

    def toArray(self):
        """ Get an ndarray of the bounds of the edge """
        return np.row_stack((self.origin.toArray(), self.twin.origin.toArray()))

    def getCloserAndFurther(self, centre):
        """ Return the edge vertices ordered to be [nearer, further] from a point,
        with a flag of whether the points have been switched from the edge ordering """
        assert(isinstance(centre, np.ndarray))
        distances = get_distance_raw(centre, self.toArray())
        if distances[0] < distances[1]:
            return (self.origin, self.twin.origin)
        else:
            return (self.twin.origin, self.origin)

    
    #------------------------------
    # def Edge Sequencing
    #------------------------------
    
    def addNext(self, nextEdge, force=False):
        assert(nextEdge is None or isinstance(nextEdge, HalfEdge))
        if not force:
            assert(self.next is None)
            assert(nextEdge is None or nextEdge.prev is None)
        if self.next is not None:
            self.next.prev = None
        self.next = nextEdge
        if self.next is not None:
            self.next.prev = self

    def addPrev(self, prevEdge, force=False):
        """ Set the half edge prior to this one in the CCW ordering """
        assert(prevEdge is None or isinstance(prevEdge, HalfEdge))
        if not force:
            assert(self.prev is None)
            assert(prevEdge is None or prevEdge.next is None)
        if self.prev is not None:
            self.prev.next = None
        self.prev = prevEdge
        if self.prev is not None:
            self.prev.next = self

    def connectNextToPrev(self):
        """ Removes this Halfedge from the ordering """
        hprev = self.prev
        hnext = self.next
        if hprev is not None:
            hprev.next = hnext
        if hnext is not None:
            hnext.prev = hprev

    #------------------------------
    # def Cleanup
    #------------------------------
                
    def markForCleanup(self):
        """ Marks this halfedge for cleanup. NOT for the twin, due to degenerate cases of hedges at boundaries """
        self.markedForCleanup = True


    #------------------------------
    # def deprecated
    #------------------------------
    
    def fixup(self):
        """ Fix the clockwise/counter-clockwise property of the edge """
        raise Exception("Deprecated: HalfEdge.fixup. Use methods in Face instead")

    def atan(self, centre=None):
        """ Get the radian to the half edge origin, from the centroid
        of the face it is part of, used to ensure clockwise ordering """
        assert(self.face is not None)
        assert(self.origin is not None)
        raise Exception("deprecated")
        if centre is None:
            assert(hasattr(self.face, 'getCentroid'))
            centre = self.face.getCentroid()
        a = self.origin.toArray()
        #multiplying to... deal with inversion of cairo? TODO: check this
        centre *= [1, -1]
        a *= [1, -1]
        centre += [0, 1]
        a += [0, 1]
        o_a = a - centre
        a1 = atan2(o_a[1], o_a[0])
        return a1

    def intersects_edge(self,bbox):
        raise Exception("Deprecated, use intersects_bbox")
    
