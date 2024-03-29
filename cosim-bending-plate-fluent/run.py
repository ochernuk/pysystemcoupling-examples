import ansys.mapdl.core as pymapdl
import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc

#================================

mapdl = pymapdl.launch_mapdl()

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

# open Fluent and read in the pre-created case file
fluent = pyfluent.launch_fluent(start_transcript=False)
fluent.file.read(file_type="case", file_name="case.cas.h5")
fluent.solution.run_calculation.iter_count = 1

#================================

syc = pysyc.launch()
syc.start_output()

# add participants
fluid_name = syc.setup.add_participant(participant_session = fluent)
solid_name = syc.setup.add_participant(participant_session = mapdl)

syc.setup.coupling_participant[fluid_name].display_name = "Fluid"
syc.setup.coupling_participant[solid_name].display_name = "Solid"

# add a coupling interface
interface_name = syc.setup.add_interface(
  side_one_participant = fluid_name, side_one_regions = ["wall_deforming"],
  side_two_participant = solid_name, side_two_regions = ["FSIN_1"])

# set up 2-way FSI coupling - add force & displacement data transfers
syc.setup.add_fsi_data_transfers(interface = interface_name, use_force_density = True)

syc.setup.solution_control.maximum_iterations = 40

# solve the coupled analysis
syc.solution.solve()

# post-process strutural results
mapdl.post1()

mapdl.result.plot_nodal_displacement(
    rnum = 0,
    show_displacement=True,
    show_edges=True,
)

# exit
syc.exit()
fluent.exit()
mapdl.exit()
