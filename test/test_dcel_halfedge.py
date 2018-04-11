import unittest
import logging
import IPython
import numpy as np
from test_context import cairo_utils as utils
from cairo_utils import dcel
from cairo_utils.dcel.constants import EditE
from math import radians


class DCEL_HALFEDGE_Tests(unittest.TestCase):
    def setUp(self):
        self.dc = dcel.DCEL()
        self.v1 = dcel.Vertex(np.array([0,0]))
        self.he = dcel.HalfEdge(origin=self.v1)
        self.e = self.dc.createEdge(np.array([0,0]), np.array([1,0]))
        return 1

    def tearDown(self):
        self.dc = None
        return 1

    #----------
    def test_halfedge_creation(self):
        """ Check Basic Halfedge construction """
        self.assertIsNotNone(self.he)
        self.assertIsNotNone(self.e)
        self.assertIsInstance(self.he, dcel.HalfEdge)
        self.assertIsInstance(self.e, dcel.HalfEdge)

    
    def test_export_import(self):
        """ Check the exported fieldnames """
        exported = self.e._export()
        self.assertTrue(all([x in exported for x in ["i","origin","twin","face","next","prev","data"]]))

    def test_split(self):
        """ Check an edge can be split at a point """
        originalEnd = self.e.twin.origin
        otherEnd = self.e.twin
        (newPoint, newEdge) = self.e.split(np.array([0.5, 0]))
        self.assertTrue(all(self.e.twin.origin.toArray() == np.array([0.5,0])))
        self.assertTrue(all(newEdge.origin.toArray() == np.array([0.5,0])))
        self.assertTrue(all(newEdge.twin.origin.toArray() == np.array([1,0])))

        self.assertTrue(newEdge.twin.origin == originalEnd)
        self.assertTrue(otherEnd.origin == newPoint)
        self.assertTrue(otherEnd.twin.origin == self.e.origin)

    #todo: test splitting on a point that isn't on the line
        
    def test_split_by_ratio(self):
        """ Test splitting by a fraction of the edge instead of a defined point """
        (newPoint, newEdge) = self.e.split_by_ratio(r=0.5)
        self.assertTrue(all(self.e.twin.origin.toArray() == np.array([0.5,0])))
        self.assertTrue(all(newEdge.origin.toArray() == np.array([0.5,0])))
        self.assertTrue(all(newEdge.twin.origin.toArray() == np.array([1,0])))

    def test_intersect(self):
        """ Test the intersection of two edges """
        #create an intersecting edge
        e2 = self.dc.createEdge(np.array([0.5, 0.5]), np.array([0.5, -0.5]))
        intersection = self.e.intersect(e2)
        #check
        self.assertIsNotNone(intersection)
        self.assertIsInstance(intersection, np.ndarray)
        self.assertTrue(all(intersection == np.array([0.5, 0])))
        #check a none-intersection
        e3 = self.dc.createEdge(np.array([2,4]),np.array([3,4]))
        self.assertIsNone(self.e.intersect(e3))

    def test_intersects_bbox(self):
        """ Test how the edge itersects with a bbox """
        #check intersection, non-intersection, and double intersection?
        #edge: 0,0 -> 1,0
        e = self.dc.createEdge(np.array([0,0]), np.array([1,0]))
        result = e.intersects_bbox(np.array([-0.5,-0.5,0.5,0.5]))
        self.assertEqual(len(result), 1)
        (coords, edgeI) = result[0]
        self.assertIsInstance(edgeI, utils.constants.IntersectEnum)
        self.assertEqual(edgeI, utils.constants.IntersectEnum.VRIGHT)

    #todo: add in a double edge bbox intersection test, and a null test

    def test_within(self):
        """ Test whether edges are inside or outside bboxs """
        self.assertTrue(self.e.within(np.array([-0.5, -0.5, 1.5, 1.5])))
        self.assertTrue(self.e.outside(np.array([1.5, 1.5, 2,2])))
        self.assertFalse(self.e.outside(np.array([-0.5, -0.5, 1.5, 1.5])))
        self.assertFalse(self.e.within(np.array([1.5, .5, 2, 2])))
        
    def test_within_circle(self):
        """ Test whether the edge is within the radius of a circle """
        self.assertTrue(np.all(self.e.within_circle(np.array([0,0]), 2) == np.array([True,True])))
        self.assertTrue(np.all(self.e.within_circle(np.array([0,0]), 0.2) == np.array([True, False])))
        self.assertTrue(np.all(self.e.within_circle(np.array([1,0]), 0.2) == np.array([False, True])))
                         
    def test_constrain(self):
        """ Test the calculation of a line adjust to be constrained within
        a bbox """
        #edge is [[0,0], [1,0]]
        result = self.e.to_constrained(np.array([0,0,0.5,1]))
        self.assertIsNotNone(result)
        self.assertIsInstance(result, np.ndarray)
        #check constraint is correct
        self.assertTrue(all(result.flatten() == np.array([0,0,0.5,0])))
        #check the original line is unmodified:
        self.assertFalse(all(self.e.toArray().flatten() == np.array([0,0,0.5,0])))

    def test_constrain_unaffected(self):
        """ Test that a line totally within a bbox is unaffected by constraining """
        #create an edge within the bbox
        edgeAsArray = self.e.toArray().flatten()
        result = self.e.to_constrained(np.array([0,0,1,1]))
        self.assertIsNotNone(result)
        #check it is unmodified
        self.assertTrue(all(self.e.toArray().flatten() == edgeAsArray))
        self.assertTrue(all(self.e.toArray().flatten() == result.flatten()))
        
    def test_connections_align_succeed(self):
        """ Test that a halfedge is coherent """ 
        self.assertTrue(self.e.connections_align(self.e.twin))
        with self.assertRaises(Exception):
            self.e.connections_align(self.he)

    def test_vertices(self):
        """ Test the addition and removal of vertices from a halfedge """
        #add vertex, clear vertices
        he = dcel.HalfEdge()
        e = dcel.HalfEdge(twin=he)
        v1 = dcel.Vertex(np.array([0,0]))
        v2 = dcel.Vertex(np.array([1,1]))
        self.assertIsNotNone(e.twin)
        self.assertIsNone(e.origin)
        self.assertIsNone(e.twin.origin)

        e.addVertex(v1)
        self.assertIsNotNone(e.origin)
        e.addVertex(v2)
        self.assertIsNotNone(e.twin.origin)
        with self.assertRaises(Exception):
            e.addVertex(v1)

        #check getVertices:
        tv1, tv2 = e.getVertices()
        self.assertTrue(tv1 == v1)
        self.assertTrue(tv2 == v2)        
            
        #check the vertices have registered the halfedges:
        self.assertTrue(e in v1.halfEdges)
        self.assertTrue(he in v2.halfEdges)
        #then clear and check the deregistration:
        e.clearVertices()
        self.assertIsNone(e.origin)
        self.assertIsNone(e.twin.origin)
        self.assertTrue(e not in v1.halfEdges)
        self.assertTrue(he not in v2.halfEdges)


    def test_faceSwap(self):
        """ Test the swapping of faces on two halfedges """
        #assign faces to each he, swap them
        f1 = dcel.Face()
        f2 = dcel.Face(site=np.array([1,1]))
        he = dcel.HalfEdge()
        e = dcel.HalfEdge(twin=he)
        e.face = f1
        he.face = f2
        self.assertEqual(e.face, f1)
        self.assertEqual(e.twin.face, f2)

        e.swapFaces()

        self.assertEqual(e.face, f2)
        self.assertEqual(e.twin.face, f1)
        

    def test_ordering(self):
        """ Test counter clockwise ordering of 3 points """
        #test left turn
        centre = np.array([0,0])
        a = np.array([1,0])
        b = np.array([0,1])
        self.assertTrue(dcel.HalfEdge.ccw(centre, a, b))
        

    def test_vertex_retrieval(self):
        """ Test vertices can be retrieved from a halfedge """
        #get vertices as a tuple, and the raw coordinates as an array
        e = self.dc.createEdge(np.array([1,0]), np.array([0,1]))
        vs = e.getVertices()
        self.assertIsInstance(vs, tuple)
        self.assertTrue(all([isinstance(x, dcel.Vertex) for x in vs]))
        
        asArray = e.toArray()
        self.assertIsInstance(asArray, np.ndarray)
        self.assertEqual(asArray.shape, (2,2))

    def test_mark_for_cleanup(self):
        """ Test a halfedge can be marked for cleanup """
        #Cleanup when marked test
        e = self.dc.createEdge(np.array([0,0]), np.array([1,1]))
        self.assertFalse(e.markedForCleanup)
        e.markForCleanup()
        self.assertTrue(e.markedForCleanup)
        self.assertFalse(e.twin.markedForCleanup)

    def test_is_infinite(self):
        """ Test halfedge infinite designations """
        self.assertTrue(self.he.isInfinite())
        self.assertFalse(self.e.isInfinite())

    def test_get_closer_and_further(self):
        """ Test getting the two points of an edge ordered by their
        distance to a third point """
        e1 = self.dc.createEdge(np.array([1,0]), np.array([2,0]))
        closer, further = e1.getCloserAndFurther(np.array([0,0]))
        self.assertIsInstance(closer, dcel.Vertex)
        self.assertIsInstance(further, dcel.Vertex)
        self.assertEqual(closer, e1.origin)
        self.assertEqual(further, e1.twin.origin)

        
    def test_closer_and_further_switched(self):
        """ Test that getCloserAndFurther will order correctly """
        e1 = self.dc.createEdge(np.array([2,0]), np.array([1,0]))
        closer, further = e1.getCloserAndFurther(np.array([0,0]))
        self.assertIsInstance(closer, dcel.Vertex)
        self.assertIsInstance(further, dcel.Vertex)
        self.assertEqual(closer, e1.twin.origin)
        self.assertEqual(further, e1.origin)


    def test_closer_and_further2(self):
        """ Check the ordering works when you move the target point """
        e1 = self.dc.createEdge(np.array([1,0]), np.array([2,0]))
        closer, further = e1.getCloserAndFurther(np.array([3,0]))
        self.assertIsInstance(closer, dcel.Vertex)
        self.assertIsInstance(further, dcel.Vertex)
        self.assertEqual(closer, e1.twin.origin)
        self.assertEqual(further, e1.origin)

    def test_closer_and_further_larger_scale(self):
        """ Check ordering works even on larger scales """
        e1 = self.dc.createEdge(np.array([100,50]), np.array([200,50]))
        closer, further = e1.getCloserAndFurther(np.array([155,50]))
        self.assertIsInstance(closer, dcel.Vertex)
        self.assertIsInstance(further, dcel.Vertex)
        self.assertEqual(closer, e1.twin.origin)
        self.assertEqual(further, e1.origin)


    def test_rotate_modified(self):
        """ Test rotating by modification of a line """
        e = self.dc.createEdge(np.array([2,0]), np.array([3,0]))
        e2, edit_e = e.rotate(np.array([2,0]), radians(90))
        self.assertEqual(edit_e, EditE.MODIFIED)
        self.assertIsInstance(e2, dcel.HalfEdge)
        self.assertEqual(e, e2)
        e2_coords = e2.toArray()
        self.assertTrue(np.allclose(e2_coords, np.array([[2,0], [2,1]])))

    def test_rotate_new(self):
        """ Test rotating by creating a new line """
        #rotate the edge around a point
        e = self.dc.createEdge(np.array([2,0]), np.array([3,0]))
        e2 = e.extend(direction=np.array([1,0]))
        e3, edit_e = e.rotate(np.array([2,0]), radians(90))
        self.assertEqual(edit_e, EditE.NEW)
        self.assertIsInstance(e3, dcel.HalfEdge)
        self.assertNotEqual(e3, e)
        e3_coords = e3.toArray()
        self.assertTrue(np.allclose(e3_coords, np.array([[2,0], [2,1]])))
        self.assertTrue(np.allclose(e2.toArray(), np.array([[3,0], [4,0]])))
        
    def test_rotate_modified_force(self):
        """ Test rotating by forcing modifcation over creating a new line """
        #rotate the edge around a point
        e = self.dc.createEdge(np.array([2,0]), np.array([3,0]))
        e2 = e.extend(direction=np.array([1,0]))
        e3, edit_e = e.rotate(np.array([2,0]), radians(90), force=True)
        self.assertEqual(edit_e, EditE.MODIFIED)
        self.assertIsInstance(e3, dcel.HalfEdge)
        self.assertEqual(e3, e)
        e3_coords = e3.toArray()
        self.assertTrue(np.allclose(e3_coords, np.array([[2,0], [2,1]])))
        self.assertTrue(np.allclose(e2.toArray(), np.array([[2,1], [4,0]])))
        
    def test_rotate_modified_by_candidates(self):
        """ Test rotating by passing in a set of connections that don't constrain """
        #rotate the edge around a point
        e = self.dc.createEdge(np.array([2,0]), np.array([3,0]))
        e2 = e.extend(direction=np.array([1,0]))
        e3, edit_e = e.rotate(np.array([2,0]), radians(90), candidates=set([e, e.twin, e2, e2.twin]))
        self.assertEqual(edit_e, EditE.MODIFIED)
        self.assertIsInstance(e3, dcel.HalfEdge)
        self.assertEqual(e3, e)
        e3_coords = e3.toArray()
        self.assertTrue(np.allclose(e3_coords, np.array([[2,0], [2,1]])))
        self.assertTrue(np.allclose(e2.toArray(), np.array([[2,1], [4,0]])))

    def test_extend(self):
        """ Test extending a line to a target """
        e = self.dc.createEdge(np.array([0,0]), np.array([1,0]))
        e2 = e.extend(target=np.array([2,0]))
        self.assertTrue(e2.prev == e)
        self.assertTrue(e.next == e2)


    def test_avg_direction(self):
        """ Test getting the average direction of a sequence of lines """
        raise Exception("Untested")

    def test_bboxes(self):
        """ Test the calculation of a bbox's 4 edges """
        raise Exception("untested")

    def test_point_is_on_line(self):
        """ Test whether a point lies on a line or not """
        self.assertTrue(self.e.point_is_on_line(np.array([0.5,0])))

    def test_point_is_on_line_fail(self):
        """ A point that doesn't lie on a line fails the test """
        self.assertFalse(self.e.point_is_on_line(np.array([2,0])))

    def test_ccw(self):
        """ Check counter clock wise test """
        a = np.array([0,0])
        b = np.array([1,0])
        c = np.array([0,1])
        self.assertTrue(dcel.HalfEdge.ccw(a,b,c))

    def test_ccw_fail(self):
        """ Check a right turn fails ccw designation """
        a = np.array([0,0])
        b = np.array([0,1])
        c = np.array([1,0])
        self.assertFalse(dcel.HalfEdge.ccw(a,b,c))
        
    def test_fix_faces(self):
        """ Test the Automatic assignment of two faces to two halfedges """
        #create the halfedge
        #attach faces with dummy centroids
        #fix faces

        raise Exception("Untested")
        
    def test_halfedge_has_constraints_false(self):
        """ A Halfedge isn't constrained by default """
        he = dcel.HalfEdge()
        self.assertFalse(he.has_constraints())

    def test_halfedge_has_constraints_arbitrary_false(self):
        """ A halfedge isn't constrainted with unrelated candidates """
        he = dcel.HalfEdge()
        self.assertFalse(he.has_constraints(set(["a"])))

    def test_halfedge_has_constraints_false_full(self):
        """ a halfedge isn't constrainted by its vertices or twin """
        v1 = self.dc.newVertex(np.array([5,5]))
        v2 = self.dc.newVertex(np.array([10,10]))
        e = self.dc.newEdge(v1,v2)
        self.assertFalse(e.has_constraints())


    def test_halfedge_has_constraints_true_dualEdge(self):
        """ a halfedge is constrained by a shared halfedge on a vertex """
        v1 = self.dc.newVertex(np.array([5,5]))
        v2 = self.dc.newVertex(np.array([10,10]))
        e = self.dc.newEdge(v1,v2)
        e2 = self.dc.newEdge(v1,v2)
        self.assertTrue(e.has_constraints())

    def test_halfedge_has_constraints_false_dualEdge(self):
        """ a halfedge isn't constrained by passed in candidate halfedges """
        v1 = self.dc.newVertex(np.array([5,5]))
        v2 = self.dc.newVertex(np.array([10,10]))
        e = self.dc.newEdge(v1,v2)
        e2 = self.dc.newEdge(v1,v2)
        self.assertFalse(e.has_constraints(set([e2, e2.twin])))


    def test_halfedge_constrain_to_circle(self):
        e = self.dc.createEdge(np.array([5,0]), np.array([7,0]))
        originalTwinVert = e.twin.origin
        ePrime, edit_e = e.constrain_to_circle(np.array([5,0]), 1)
        self.assertEqual(edit_e, EditE.MODIFIED)
        self.assertTrue(np.allclose(e.twin.origin.toArray(), np.array([6,0])))

    def test_halfedge_constrain_to_circle_no_op(self):
        e = self.dc.createEdge(np.array([5,0]), np.array([6,0]))
        originalTwinVert = e.twin.origin
        ePrime, edit_e = e.constrain_to_circle(np.array([5,0]), 1)
        self.assertEqual(edit_e, EditE.MODIFIED)
        self.assertTrue(np.allclose(e.twin.origin.toArray(), np.array([6,0])))
        self.assertEqual(originalTwinVert, e.twin.origin)

        
        
    
    
if __name__ == "__main__":
      #use python $filename to use this logging setup
      LOGLEVEL = logging.INFO
      logFileName = "log.DCEL_HALFEDGE_Tests"
      logging.basicConfig(filename=logFileName, level=LOGLEVEL, filemode='w')
      console = logging.StreamHandler()
      console.setLevel(logging.WARN)
      logging.getLogger().addHandler(console)
      unittest.main()
      #reminder: user logging.getLogger().setLevel(logging.NOTSET) for log control
