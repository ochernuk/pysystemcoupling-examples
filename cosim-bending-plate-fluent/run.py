import ansys.mapdl.core as pymapdl
import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc

from mapdl_proxy import Mapdl_SessionProxy

"""
TODO:
- fix fluent displacement bug: https://github.com/ansys/pyfluent/pull/2145
- pymapdl additional_switches case issue: https://github.com/ansys/pymapdl/discussions/2418
- mapdl.exit() throws exception when connected to System Coupling "The /EXIT command is not permitted in server mode."
- mapdl should (probably) disconnect during mapdl.finish()
- need to add a new mapdl command to connect to System Coupling, something like mapdl.scconn(host, port, name)
- integrate Mapdl_SessionProxy proxy code into the repo
"""

#================================

mapdl = Mapdl_SessionProxy()

mapdl.prep7()

# define material properties
mapdl.mp("DENS", 1, 2550)
mapdl.mp("ALPX", 1, 1.2e-05)
mapdl.mp("C", 1, 434)
mapdl.mp("KXX", 1, 60.5)
mapdl.mp("RSVX", 1, 1.7e-07)
mapdl.mp("EX", 1, 2500000)
mapdl.mp("NUXY", 1, 0.35)
mapdl.mp("MURX", 1, 10000)

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
mapdl.nsel("S", "LOC", "X", 10.0)
mapdl.nsel("A", "LOC", "Y", 1.0)
mapdl.nsel("A", "LOC", "X", 10.06)
mapdl.cm("FSIN_1", "NODE")
mapdl.sf("FSIN_1", "FSIN", 1)

mapdl.allsel()

mapdl.run("/SOLU")

# set analysis type to steady
mapdl.antype(0)

#================================

fluent = pyfluent.launch_fluent(product_version="24.1.0", start_transcript=False)
case_file = "case.cas.gz"
fluent.file.read(file_type="case", file_name="case.cas.h5")
fluent.solution.run_calculation.iter_count = 1

#================================

syc = pysyc.launch(version = "24.1")
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
