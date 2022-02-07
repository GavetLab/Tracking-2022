# Fiji modules
from ij import IJ
from ij.gui import ShapeRoi
from ij.plugin.filter import GaussianBlur

# Python modules
from operator import itemgetter
import math

# Custom modules
import Tracking.Cells as Cells
import Tracking.WatershedSplit as W_Split

'''
Author: Vicente Lebrec (vicente.lebrec@gustaveroussy.fr)

Tracking algorithm based on a Gale-Shapley matching between each pair of
frames, with individual preferences based on the overlap area with either
the prev or the next frame.

Any remaining ROI in the current frame is tested for potential undersegmentation.
Any remaining ROI in the next frame is tested for potential oversegmentation.

Any detected undersegmentation is split using marker-controlled watershed.
Any detected oversegmentation is fused back into a single ROI
'''

##################

class Node:
    '''
    All ROI in each frames are represented internally as 'Nodes'
      - Each Node is connected to all overlapping nodes in next and prev frames.
      - Each Node's list of prev overlap and next overlap are sorted according to overlap area.
      - Those (prev and next frames) sorted lists of overlapping nodes are
      used in the Gale-Shapley matching algorithm.
    '''
    def __init__(self, Roi, Frame):
        self.Roi = Roi
        self.Frame = Frame
        self.shapeRoi = ShapeRoi(Roi)
        # Info about ROI
        RoiStats = Roi.getStatistics()
        self.area = RoiStats.area
        self.x = RoiStats.xCentroid
        self.y = RoiStats.yCentroid
        self.majorEllipse = RoiStats.major
        # List of potential matches in prev and next frames
        self.sorted_overlap = False
        self.sorted_dist = False
        self.prevNodes = []
        self.nextNodes = []
        # The best next/prev nodes found by Gale-Shapley matching algorithm
        self.BestPrev = False
        self.BestPrevRank = None
        self.BestNext = False
        # Matches on distance (not overlap)
        self.prevNodes_noOL = []
        self.nextNodes_noOL = []
        self.BestPrev_dist = False
        self.BestPrevRank_dist = None
        self.BestNext_dist = False
        # If undersegmented cluster:
        self.Cluster = []  #List of all parent nodes to the currently undersegmented cluster
        # If cytokinesis:
        self.mother = None
        # Associated to cell (name of cell)
        self.cell = None

    # Functions to generate map of nodes
    def addPrevNode(self, prevNode, OverlapArea):
        Weight = OverlapArea
        self.prevNodes.append((Weight, prevNode))

    def addNextNode(self, nextNode, OverlapArea):
        Weight = OverlapArea
        self.nextNodes.append((Weight, nextNode))

    def addPrevNode_noOL(self, prevNode, distance): # near but no overlap
        Weight = distance
        self.prevNodes_noOL.append((Weight, prevNode))

    def addNextNode_noOL(self, nextNode, distance): # near but no overlap
        Weight = distance
        self.nextNodes_noOL.append((Weight, nextNode))

    def testOverlap(self, prevNode):
        prevShape = ShapeRoi(prevNode.Roi)
        overlap = prevShape.and(self.shapeRoi)
        if overlap.getLength() > 0:
            overlapArea = overlap.getStatistics().area
            prevNode.addNextNode(self, overlapArea)
            self.addPrevNode(prevNode, overlapArea)

    def testDist(self, prevNode, dist):
        #dist = distance(self, prevNode)
        prevNode.addNextNode_noOL(self, distance)
        self.addPrevNode_noOL(prevNode, distance)

    # Functions to find best match among potential matches
    def sort_overlap(self, ForceSort=False):
        if not self.sorted_overlap or ForceSort==True:
            # Rank prevNodes and nextNodes by weight (= OverlapArea/Area of current node)
            self.prevNodes.sort(reverse=True, key=itemgetter(0))
            self.nextNodes.sort(reverse=True, key=itemgetter(0))
            self.sorted_overlap = True

    def sort_dist(self, ForceSort=False):
        if not self.sorted_dist or ForceSort==True:
            # Rank prevNodes and nextNodes by weight (= OverlapArea/Area of current node)
            self.prevNodes_noOL.sort(reverse=False, key=itemgetter(0))
            self.nextNodes_noOL.sort(reverse=False, key=itemgetter(0))
            self.sorted_dist = True

    def Rank(self, Match):
        # return rank of prevNode
        i = 0
        for weight, prevNode in self.prevNodes:
            if Match is prevNode:
                return i
            i += 1

    def Rank_dist(self, Match):
        # return rank of prevNode
        i = 0
        for weight, prevNode in self.prevNodes_noOL:
            if Match is prevNode:
                return i
            i += 1

    def findMatch(self, RemainingNodes, MatchingNextNodes):
        '''
        Gale-Shapley algorithm to find best match of node:
            - If potential matching node is alone: mark self as this potential match's partner
            - Else, if it already have a partner, take its place if self is better ranked in
            potential match preferences
        '''
        #self.sort_overlap()
        for nextNode in self.nextNodes:
            PotentialMatch = nextNode[1]
            if not PotentialMatch.BestPrev: # If PotentialMatch doesn't have any partner yet
                #PotentialMatch.sort_overlap()
                PotentialMatch.BestPrev = self           # 1. Define self as PotentialMatch's best prev
                PotentialMatch.BestPrevRank = PotentialMatch.Rank(self)
                #PotentialMatch.Cluster = [Node for Node in self.Cluster] # if self is a cluster, it will be saved
                self.BestNext = PotentialMatch           # 2. Define PotentialMatch as self's best next
                MatchingNextNodes.append(PotentialMatch) # 3. Say a match was found for PotentialMatch
                return True
            else: # If PotentialMatch already have a partner
                RivalNode = PotentialMatch.BestPrev
                myRank = PotentialMatch.Rank(self)
                # If self is of higher rank than rival node, take its place:
                if myRank < PotentialMatch.BestPrevRank:
                    PotentialMatch.BestPrev.BestNext = False # 1. Rival Node's best next is reset
                    RivalNode = PotentialMatch.BestPrev
                    RemainingNodes.append(RivalNode)         # 2. Rival Node is sent back to the list of Nodes without partner
                    PotentialMatch.BestPrev = self           # 3. Self is defined as PotentialMatch's new Best Prev
                    PotentialMatch.BestPrevRank = myRank
                    #PotentialMatch.Cluster = [Node for Node in self.Cluster] # if self is a cluster, it will be saved
                    self.BestNext = PotentialMatch           # 4. PotentialMatch is defined as self's best next
                    return True
        # If no match found, return False
        return False

    def findMatch_dist(self, RemainingNodes, MatchingNextNodes):
        '''
        Gale-Shapley algorithm to find best match of node:
            - If potential matching node is alone: mark self as this potential match's partner
            - Else, if it already have a partner, take its place if self is better ranked in
            potential match preferences
        '''
        #self.sort_overlap()
        for nextNode in self.nextNodes_noOL:
            PotentialMatch = nextNode[1]
            if not PotentialMatch.BestPrev_dist: # If PotentialMatch doesn't have any partner yet
                #PotentialMatch.sort_overlap()
                PotentialMatch.BestPrev_dist = self           # 1. Define self as PotentialMatch's best prev
                PotentialMatch.BestPrevRank_dist = PotentialMatch.Rank_dist(self)
                #PotentialMatch.Cluster = [Node for Node in self.Cluster] # if self is a cluster, it will be saved
                self.BestNext_dist = PotentialMatch           # 2. Define PotentialMatch as self's best next
                MatchingNextNodes.append(PotentialMatch) # 3. Say a match was found for PotentialMatch
                # Also set them as (general, not only dist) BestPrev or BestNext
                PotentialMatch.BestPrev = self           # 1. Define self as PotentialMatch's best prev
                self.BestNext = PotentialMatch           # 2. Define PotentialMatch as self's best next
                return True
            else: # If PotentialMatch already have a partner
                RivalNode = PotentialMatch.BestPrev_dist
                myRank = PotentialMatch.Rank_dist(self)
                # If self is of higher rank than rival node, take its place:
                if myRank < PotentialMatch.BestPrevRank_dist:
                    PotentialMatch.BestPrev_dist.BestNext_dist = False # 1. Rival Node's best next is reset
                    RivalNode = PotentialMatch.BestPrev_dist
                    RemainingNodes.append(RivalNode)         # 2. Rival Node is sent back to the list of Nodes without partner
                    PotentialMatch.BestPrev_dist = self           # 3. Self is defined as PotentialMatch's new Best Prev
                    PotentialMatch.BestPrevRank_dist = myRank
                    #PotentialMatch.Cluster = [Node for Node in self.Cluster] # if self is a cluster, it will be saved
                    self.BestNext_dist = PotentialMatch           # 4. PotentialMatch is defined as self's best next
                    # Also set them as (general, not only dist) BestPrev or BestNext
                    PotentialMatch.BestPrev = self           # 1. Define self as PotentialMatch's best prev
                    self.BestNext = PotentialMatch           # 2. Define PotentialMatch as self's best next
                    return True
        # If no match found, return False
        return False

    # To mark as a cluster:
    def cluster_of(self, NodeList):
        self.Cluster.extend(NodeList)
        self.Cluster = list(set(self.Cluster))

    # To fuse/split nodes (correcting segment. errors)
    def remove_prevNode(self, DelNode):
        for i, (weight, Node) in enumerate(self.prevNodes):
            if Node is DelNode:
                del self.prevNodes[i]
                break

    def remove_nextNode(self, DelNode):
        for i, (weight, Node) in enumerate(self.nextNodes):
            if Node is DelNode:
                del self.nextNodes[i]
                break

#########################################################################################

# General functions
def distance(Node1, Node2):
    # Compute distance between the two nodes' centroids
    return math.sqrt((Node1.x - Node2.x)**2 + (Node1.y - Node2.y)**2)

def remove_node(DelNode, Nodes):
    i = 0
    while i < len(Nodes):
        if Nodes[i] is DelNode:
            del Nodes[i]
            break
        else:
            i += 1

# Generate map of all nodes and their matches between frames
# Return a list of all nodes, ordered by the frame they are in
def roi_to_nodes(RoiPerFrames, TrackParam):
    maxDistance = TrackParam['Max Distance']
    IJ.log("Mapping all frame-to-frame ROI overlaps...")
    NodesPerFrame = []
    Frame = 0
    MaxFrame = len(RoiPerFrames)
    while Frame < MaxFrame:
        #IJ.log("> Frame " + str(Frame + 1) + "/" + str(MaxFrame))
        IJ.showStatus("Frame " + str(Frame) + "/" + str(MaxFrame))
        IJ.showProgress(Frame, MaxFrame)
        NodesInFrame = []
        for Roi in RoiPerFrames[Frame]:
            myNode = Node(Roi, Frame + 1)
            if Frame != 0:
                for prevNode in NodesPerFrame[Frame - 1]:
                    if distance(myNode, prevNode) < maxDistance:
                        myNode.testOverlap(prevNode)
            NodesInFrame.append(myNode)
        NodesPerFrame.append(NodesInFrame)
        Frame += 1
    return NodesPerFrame

def find_best_matches(NodesPerFrame, TrackParam, imp):
    ## Tracking parameters
    maxDistance = TrackParam['Max Distance']
    w_sigma = TrackParam['Watershed sigma']
    w_input = TrackParam['Watershed input']
    DistanceBackup = TrackParam['BackupDistance']

    IJ.log("Finding best matches among overlaps...")
    MaxFrame = len(NodesPerFrame) - 1
    CurrentFrame = 0
    SeedNodes = NodesPerFrame[0] # All of the nodes in the first frame are necessarily Seed Nodes
    while CurrentFrame < MaxFrame:
        # Find best matches for Nodes on current frame
        RemainingNodes = [Node for Node in NodesPerFrame[CurrentFrame]]
        AllNextNodes = [Node for Node in NodesPerFrame[CurrentFrame + 1]]
        MatchingNextNodes = [] # List of all nextNodes that matched
        RejectedNodes = []
        
        for Node in RemainingNodes:
            Node.sort_overlap(ForceSort=True)
        for Node in AllNextNodes:
            Node.sort_overlap(ForceSort=True)
        i = 0
        while RemainingNodes: # Won't loop if there are no detected nodes in the frame
            Node = RemainingNodes[i]
            # Try to find a match among potential nextNodes
            if Node.findMatch(RemainingNodes, MatchingNextNodes): # True if a match is found, False if rejected by all potential matches
                del RemainingNodes[i] # Remove Node from RemainingNodes
            else: # If no match is found or rejected by all next Nodes
                RejectedNodes.append(RemainingNodes.pop(i))
            # If end of RemainingNodes list is reached, then return to beginning
            if i == len(RemainingNodes): # What's the point of those two lines??!
                i = 0                    # i is not incremented anyway, it will only trigger if len(RemainingNodes) is 0...
            # If no Nodes remain or if no matches are found anymore (ie: all remaining nodes are rejected), exit the loop
            if len(RemainingNodes) == 0:
                break

        # If any Node remains in Frame n, test if undersegmentation occured in next frame
        UndersegmentedNodes = set()
        for Node in RejectedNodes:
            Node.sort_overlap(ForceSort=True) #TODO necessary?
            if len(Node.nextNodes) != 0:
                myMatch = Node.nextNodes[0][1] # Best potential match in next frame
                RivalNode = myMatch.BestPrev # Best match of myMatch
                # If sum of Node and Rival area is nearer to myMatch area than RivalNode area, then it's an undersegmentation
                SumArea = Node.area + RivalNode.area
                if abs(myMatch.area - SumArea) < abs(myMatch.area - RivalNode.area):
                    myMatch.cluster_of([Node, RivalNode])
                    UndersegmentedNodes.add(myMatch)
                    remove_node(Node, RejectedNodes)
        UndersegmentedNodes = list(UndersegmentedNodes)
        W_input = None
        for ClusterNode in UndersegmentedNodes:
            splitNodes, W_input = split_node(ClusterNode, imp, W_input, w_sigma)
            remove_node(ClusterNode, NodesPerFrame[CurrentFrame+1])
            NodesPerFrame[CurrentFrame + 1].extend(splitNodes)

        # If any Node from frame n+1 wasn't matched with frame n, test if oversegmentation
        RemainingNextNodes = list(set(AllNextNodes) - set(MatchingNextNodes))
        LoneNextNodes = []
        for Node in RemainingNextNodes:
            Node.sort_overlap(ForceSort=True) #TODO necessary?
            if len(Node.prevNodes) != 0 and not Node.prevNodes[0][1].BestNext == False:
                myMatch = Node.prevNodes[0][1]
                RivalNode = myMatch.BestNext
                # Use area to identify a potential oversegmentation
                SumArea = Node.area + RivalNode.area
                #if abs(myMatch.area - SumArea) < abs(myMatch.area - RivalNode.area):
                if abs(myMatch.area - SumArea) < myMatch.area*0.1:
                    if abs(RivalNode.area - Node.area) < RivalNode.area*0.1:
                        distNodes = distance(Node, RivalNode)
                        if distNodes > 55 and distNodes > 1.2*min(Node.majorEllipse, RivalNode.majorEllipse):  #Cytokinesis:
                            is_cytok = True
                        else:
                            is_cytok = False
                    else:
                        is_cytok = False
                    if is_cytok: # Cytokinesis
                        myMatch.BestNext = False
                        Node.mother = myMatch
                        RivalNode.mother = myMatch
                        SeedNodes.extend([Node, RivalNode])
                    else: # Genuine oversegmentation:
                        FusedNode = fuse_nodes(Node, RivalNode) # Fuse Node and RivalNode into a single Node
                        myMatch.BestNext = FusedNode # Set the fused node as myMatch bestNext
                        FusedNode.BestPrev = myMatch # Set myMatch as FusedNode bestPrev
                        if CurrentFrame + 1 < len(NodesPerFrame): # If not last frame
                            # Remove Node and RivalNode from the list of Nodes in the next frame
                            remove_node(Node, NodesPerFrame[CurrentFrame+1])
                            remove_node(RivalNode, NodesPerFrame[CurrentFrame+1])
                            # Add the fused Node to the list of Nodes in the next frame
                            NodesPerFrame[CurrentFrame + 1].append(FusedNode)
                else:
                    # Add Node to the list of SeedNodes
                    #SeedNodes.append(Node)
                    LoneNextNodes.append(Node)
            else:
                # Add Node to the list of SeedNodes
                #SeedNodes.append(Node)
                LoneNextNodes.append(Node)

        # Among remaining nodes, test if same node using distance
        # Remaining Nodes should be all Nodes in current frame with no match in next frame
        RemainingNodes = RejectedNodes
        # AllNextNodes should be all Nodes in next frame with no match in current frame
        AllNextNodes = LoneNextNodes
        if DistanceBackup:
            # Then I need to test distance between those Nodes in current and next frame
            for nextNode in AllNextNodes:
                for prevNode in RemainingNodes:
                    dist = distance(prevNode, nextNode)
                    if dist < maxDistance:
                        nextNode.testDist(prevNode, dist)

            MatchingNextNodes = [] # List of all nextNodes that matched
            RejectedNodes = []
            
            for Node in RemainingNodes:
                Node.sort_dist(ForceSort=True)
            for Node in AllNextNodes:
                Node.sort_dist(ForceSort=True)
            i = 0
            while RemainingNodes: # Won't loop if there are no detected nodes in the frame
                Node = RemainingNodes[i]
                # Try to find a match among potential nextNodes
                if Node.findMatch_dist(RemainingNodes, MatchingNextNodes): # True if a match is found, False if rejected by all potential matches
                    del RemainingNodes[i] # Remove Node from RemainingNodes
                else: # If no match is found or rejected by all next Nodes
                    RejectedNodes.append(RemainingNodes.pop(i))
                # If end of RemainingNodes list is reached, then return to beginning
                if i == len(RemainingNodes):
                    i = 0
                # If no Nodes remain or if no matches are found anymore (ie: all remaining nodes are rejected), exit the loop
                if len(RemainingNodes) == 0:
                    break
            RemainingNextNodes = list(set(AllNextNodes) - set(MatchingNextNodes))
            SeedNodes.extend(RemainingNextNodes)
        else:
            SeedNodes.extend(AllNextNodes)

        # Go to next frame
        CurrentFrame += 1
    return SeedNodes

## Nodes fusion
def fuse_nodes(Node1, Node2):
    FusedRoi = ShapeRoi(Node1.Roi)
    ShapeRoi2 = ShapeRoi(Node2.Roi)
    FusedRoi.or(ShapeRoi2)
    FusedRoi.setPosition(Node1.Frame)
    # Create a new, fused, node
    FusedNode = Node(FusedRoi, Node1.Frame)
    # Fuse nextNodes lists:
    CombinedNextNodes = list(set([myNode for weight, myNode in Node1.nextNodes + Node2.nextNodes]))
    for nextNode in CombinedNextNodes:
        nextNode.testOverlap(FusedNode)
        nextNode.remove_prevNode(Node1)
        nextNode.remove_prevNode(Node2)
    CombinedPrevNodes = list(set([myNode for weight, myNode in Node1.prevNodes + Node2.prevNodes]))
    for prevNode in CombinedPrevNodes:
        FusedNode.testOverlap(prevNode)
        prevNode.remove_nextNode(Node1)
        prevNode.remove_nextNode(Node2)
        prevNode.sort_overlap(ForceSort=True)
    FusedNode.sort_overlap(ForceSort=True)
    return FusedNode

## Node split
def w_marker(Roi1, Roi2):
    # return centroid of overlap between two ROIs
    sRoi1 = ShapeRoi(Roi1)
    sRoi2 = ShapeRoi(Roi2)
    overlap = sRoi1.and(sRoi2)
    imgstat = overlap.getStatistics()
    x,y = imgstat.xCentroid, imgstat.yCentroid
    return (int(x),int(y))

def split_node(ClusterNode, imp, W_input, w_sigma):
    frame = ClusterNode.Frame
    markers = []
    # Use centroids of overlaps between roi to split and its parents as markers for watershed
    for myNode in ClusterNode.Cluster:
        markers.append(w_marker(myNode.Roi, ClusterNode.Roi))
    #IJ.log("Frame " + str(frame) + ": Cluster to split into " + str(len(markers)))
    ip = imp.getProcessor()
    imp.setPosition(frame)
    RoiList, W_input = W_Split.split(ip, markers, ClusterNode.Roi, w_sigma, W_input)
    splitNodes = []
    for Roi, parentNode in zip(RoiList, ClusterNode.Cluster):
        if Roi:
            Roi.setPosition(frame)
            splitNode = Node(Roi, frame)
            splitNode.BestPrev = parentNode
            parentNode.BestNext = splitNode
            for weight, nextNode in ClusterNode.nextNodes:
                nextNode.testOverlap(splitNode)
                nextNode.remove_prevNode(ClusterNode)
            splitNodes.append(splitNode)
        else:
            parentNode.BestNext = False
    return splitNodes, W_input

########################################

## Generate list of cells from linked nodes
def seednodes_to_cell(SeedNodes, PosValue):
    myCells = []
    for Seed in SeedNodes:
        myCell = Cells.Cell(Pos=PosValue) # Create a new cell object from SeedNode's Roi
        myCell.addNucleus(Seed.Roi)
        Seed.cell = myCell.name
        CurrentNode = Seed
        while CurrentNode.BestNext: #As long as there are next nodes in the node's daughters
            CurrentNode = CurrentNode.BestNext
            myCell.addNucleus(CurrentNode.Roi) #Add CurrentNode to cell
            CurrentNode.cell = myCell.name
        myCells.append(myCell)
    return myCells

## Main function
def track(RoiPerFrames, TrackParam, imp, PosValue):
    # Convert ROIs to nodes in a graph
    NodesPerFrame = roi_to_nodes(RoiPerFrames, TrackParam)
    # Find best match for each node, and return the first node of each path
    SeedNodes = find_best_matches(NodesPerFrame, TrackParam, imp)
    # Convert the nodes to cells
    myCells = seednodes_to_cell(SeedNodes, PosValue)
    return myCells
