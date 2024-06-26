import numpy as np
import ansys.systemcoupling.partlib as scp
import argparse
import sys
import math

nodeIds = {"source" : np.array([], dtype=np.int64)}
nodeCoords = {"source" : np.array([], dtype=np.float64)}
solutionData = {"source" : {"force" : np.array([], dtype=np.float64) }}

# generate source data
def generateSourceData():
    forceMag = 5.0
    naxial = 33
    ncirc = 10
    nrad = 20
    radius = 0.025
    nodeid_values = list()
    coords_values = list()
    forces_values = list()
    for xi in range(naxial):
        x = (1.0 - 0.0) * xi / (naxial - 1)
        for ti in range(ncirc):
            theta = 2.0 * math.pi * ti / ncirc
            for ri in range(nrad):
                r = radius * (ri + 1) / nrad
                z = r * math.cos(theta)
                y = r * math.sin(theta)
                fx = 0.0
                fy = forceMag * math.sin(theta + 0.5 * math.pi)
                fz = forceMag * math.cos(theta + 0.5 * math.pi)
                nodeid_values.append(len(nodeid_values))
                coords_values.append([x, y, z])
                forces_values.append([fx, fy, fz])

    nodeIds["source"] = np.array(nodeid_values)
    nodeCoords["source"] = np.array(coords_values)
    solutionData["source"]["force"] = np.array(forces_values)

def getPointCloud(regionName):
    return scp.PointCloud(scp.OutputIntegerData(nodeIds[regionName]), scp.OutputVectorData(nodeCoords[regionName]))

def getOutputVector(regionName, variableName):
    return scp.OutputVectorData(solutionData[regionName][variableName])

parser = argparse.ArgumentParser()
parser.add_argument("--schost", type=str, default="")
parser.add_argument("--scport", type=int, default=0)
parser.add_argument("--scname", type=str, default="")
args, unknown = parser.parse_known_args()

try:
    sc = scp.SystemCoupling(args.schost, args.scport, args.scname, "script")

    sc.registerPointCloudAccess(getPointCloud)
    sc.registerOutputVectorDataAccess(getOutputVector)

    generateSourceData()
    print(nodeIds)
    print(nodeCoords)
    print(solutionData)

    sc.initializeAnalysis()

    while sc.doIteration():
        sc.updateInputs()
        sc.updateOutputs(scp.Complete)

    sc.disconnect()
except Exception as e:
    print(e)
    sys.exit(1)

sys.exit(0)
