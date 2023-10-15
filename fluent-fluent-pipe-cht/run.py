import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc

#===

# launch Fluent session and read in mesh file
pipe_fluid_session = pyfluent.launch_fluent(product_version="24.1.0", start_transcript=False)
pipe_fluid_mesh_file = "pipe_fluid.msh.h5"
pipe_fluid_session.file.read(file_type="mesh", file_name=pipe_fluid_mesh_file)

# turn on energy model
pipe_fluid_session.setup.models.energy.enabled = True

# add water material
pipe_fluid_session.setup.materials.database.copy_by_name(type="fluid", name="water-liquid")

# set up cell zone conditions
pipe_fluid_session.setup.cell_zone_conditions.fluid["fluid"].material = "water-liquid"

# set up boundary conditions
pipe_fluid_session.setup.boundary_conditions.velocity_inlet["inlet"].momentum.velocity = 0.1
pipe_fluid_session.setup.boundary_conditions.wall["wall"].thermal.thermal_bc = "via System Coupling"

# set up solver settings - 1 fluent iteration per 1 coupling iteration
pipe_fluid_session.solution.run_calculation.iter_count = 1

#===

# launch another Fluent session and read in mesh file
pipe_solid_session = pyfluent.launch_fluent(product_version="24.1.0", start_transcript=False)
pipe_solid_mesh_file = "pipe_solid.msh.h5"
pipe_solid_session.file.read(file_type="mesh", file_name=pipe_solid_mesh_file)

# turn on energy model
pipe_solid_session.setup.models.energy.enabled = True

# add copper material
pipe_solid_session.setup.materials.database.copy_by_name(type="solid", name="copper")

# set up cell zone conditions
pipe_solid_session.setup.cell_zone_conditions.solid["solid"].material = "copper"

# set up boundary conditions
pipe_solid_session.setup.boundary_conditions.wall["outer_wall"].thermal.thermal_bc = "Temperature"
pipe_solid_session.setup.boundary_conditions.wall["outer_wall"].thermal.t.value = 350

pipe_solid_session.setup.boundary_conditions.wall["inner_wall"].thermal.thermal_bc = "via System Coupling"

pipe_solid_session.setup.boundary_conditions.wall["insulated1"].thermal.thermal_bc = "Heat Flux"
pipe_solid_session.setup.boundary_conditions.wall["insulated1"].thermal.q.value = 0

pipe_solid_session.setup.boundary_conditions.wall["insulated2"].thermal.thermal_bc = "Heat Flux"
pipe_solid_session.setup.boundary_conditions.wall["insulated2"].thermal.q.value = 0

# set up solver settings - 1 fluent iteration per 1 coupling iteration
pipe_solid_session.solution.run_calculation.iter_count = 1

#===

# launch System Coupling session
syc = pysyc.launch(version = "24.1")
syc.start_output()

# add two Fluent sessions above as participants
fluid_name = syc.setup.add_participant(participant_session = pipe_fluid_session)
solid_name = syc.setup.add_participant(participant_session = pipe_solid_session)
syc.setup.coupling_participant[fluid_name].display_name = "Fluid"
syc.setup.coupling_participant[solid_name].display_name = "Solid"

# add a coupling interface
interface = syc.setup.add_interface(
  side_one_participant = fluid_name, side_one_regions = ["wall"],
  side_two_participant = solid_name, side_two_regions = ["inner_wall"])

# set up 2-way coupling - add temperature and heat flow data transfers
syc.setup.add_thermal_data_transfers(interface = interface)

# set up coupled analysis settings
# it should take about 80 iterations to converge
syc.setup.solution_control.maximum_iterations = 100

#===

# solve the coupled analysis
syc.solution.solve()

#===

# clean up at the end
syc.end_output()
pipe_fluid_session.exit()
pipe_solid_session.exit()
syc.exit()
