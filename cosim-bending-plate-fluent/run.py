"""
For now this requires setting AWP_ROOT env var to AWP_ROOT242, because
24.2 is not yet officially supported by PyAnsys products.

TODO:
- pymapdl additional_switches case issue: https://github.com/ansys/pymapdl/discussions/2418
  - fixed - waiting for a new release
- integrate Mapdl_SessionProxy proxy code into the repo
"""

import ansys.mapdl.core as pymapdl
import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc

from mapdl_proxy import Mapdl_SessionProxy

#================================

mapdl = Mapdl_SessionProxy()

mapdl.prep7()

# define material properties
mapdl.mp("DENS", 1, 2550)
mapdl.mp("ALPX", 1, 1.2e-05)
mapdl.mp("EX", 1, 2500000)
mapdl.mp("NUXY", 1, 0.35)

# set element types to SOLID186
mapdl.et(1, 186)
mapdl.keyopt(1,2,1)

# make geometry
mapdl.block(10.00, 10.06, 0.0, 1.0, 0.0, 0.4)
mapdl.vsweep(1)

# add fixed support at y=0
mapdl.nsel("S", "LOC", "Y", 0)
mapdl.d("all", "all")

# add FSI interface
mapdl.nsel("S", "LOC", "X", 9.99, 10.01)
mapdl.nsel("A", "LOC", "Y", 0.99, 1.01)
mapdl.nsel("A", "LOC", "X", 10.05, 10.07)
mapdl.cm("FSIN_1", "NODE")
mapdl.sf("FSIN_1", "FSIN", 1)

mapdl.allsel()

mapdl.run("/SOLU")

# set analysis type to steady
mapdl.antype(0)

#================================

fluent = pyfluent.launch_fluent(start_transcript=False)
case_file = "case.cas.gz"
fluent.file.read(file_type="case", file_name="case.cas.h5")
fluent.solution.run_calculation.iter_count = 1

#================================

syc = pysyc.launch()
syc.start_output()

fluid_name = syc.setup.add_participant(participant_session = fluent)
solid_name = syc.setup.add_participant(participant_session = mapdl)

syc.setup.coupling_participant[fluid_name].display_name = "Fluid"
syc.setup.coupling_participant[solid_name].display_name = "Solid"

# temporary until bug is fixed
syc.setup.coupling_participant[fluid_name].variable["displacement"].tensor_type = "Vector"

# add a coupling interface
interface = syc.setup.add_interface(
  side_one_participant = fluid_name, side_one_regions = ["wall_deforming"],
  side_two_participant = solid_name, side_two_regions = ["FSIN_1"])

# set up 2-way FSI coupling - add force & displacement data transfers
syc.setup.add_data_transfer(
    interface = interface,
    target_side = "One",
    source_variable = "INCD",
    target_variable = "displacement",
)

syc.setup.add_data_transfer(
    interface = interface,
    target_side = "Two",
    source_variable = "force",
    target_variable = "FDNS",
)

syc.setup.solution_control.maximum_iterations = 20

syc.solution.solve()

# post-process strutural results
mapdl.post1()

mapdl.result.plot_nodal_displacement(
    rnum = 0,
    show_displacement=True,
    show_edges=True,
)

syc.exit()
fluent.exit()
mapdl.exit()
