import ansys.fluent.core as pyfluent
import ansys.systemcoupling.core as pysyc

#===

pipe_fluid_meshing = pyfluent.launch_fluent(product_version="24.1.0", mode="meshing", start_transcript=False)
pipe_fluid_meshing.workflow.InitializeWorkflow(WorkflowType="Watertight Geometry")

pipe_fluid_meshing.workflow.TaskObject["Import Geometry"].Arguments = {
    "FileName": "pipe_fluid.scdoc",
    "LengthUnit": "m",
}

pipe_fluid_meshing.workflow.TaskObject["Import Geometry"].Execute()

pipe_fluid_meshing.workflow.TaskObject["Add Local Sizing"].AddChildToTask()
pipe_fluid_meshing.workflow.TaskObject["Add Local Sizing"].Execute()

pipe_fluid_meshing.workflow.TaskObject["Generate the Surface Mesh"].Arguments = {
    "CFDSurfaceMeshControls": {"MaxSize": 0.025}
}

pipe_fluid_meshing.workflow.TaskObject["Generate the Surface Mesh"].Execute()

pipe_fluid_meshing.workflow.TaskObject["Describe Geometry"].UpdateChildTasks(
    SetupTypeChanged=False
)

pipe_fluid_meshing.workflow.TaskObject["Describe Geometry"].Arguments = {
    "SetupType": "The geometry consists of only fluid regions with no voids"
}

pipe_fluid_meshing.workflow.TaskObject["Describe Geometry"].UpdateChildTasks(SetupTypeChanged=True)
pipe_fluid_meshing.workflow.TaskObject["Describe Geometry"].Execute()

pipe_fluid_meshing.workflow.TaskObject["Update Boundaries"].Arguments = {
    "BoundaryLabelList": ["inlet", "outlet", "wall"],
    "BoundaryLabelTypeList": ["velocity-inlet", "pressure-outlet", "wall"],
    "OldBoundaryLabelList": ["inlet", "outlet", "wall"],
    "OldBoundaryLabelTypeList": ["velocity-inlet", "pressure outlet", "wall"],
}
pipe_fluid_meshing.workflow.TaskObject["Update Boundaries"].Execute()

pipe_fluid_meshing.workflow.TaskObject["Update Regions"].Execute()

pipe_fluid_meshing.workflow.TaskObject["Add Boundary Layers"].AddChildToTask()
pipe_fluid_meshing.workflow.TaskObject["Add Boundary Layers"].InsertCompoundChildTask()
pipe_fluid_meshing.workflow.TaskObject["smooth-transition_1"].Arguments = {
    "BLControlName": "smooth-transition_1",
}
pipe_fluid_meshing.workflow.TaskObject["Add Boundary Layers"].Arguments = {}
pipe_fluid_meshing.workflow.TaskObject["smooth-transition_1"].Execute()

pipe_fluid_meshing.workflow.TaskObject["Generate the Volume Mesh"].Arguments = {
    "VolumeFill": "poly-hexcore",
    "VolumeFillControls": {
        "HexMaxCellLength": 0.025,
    },
}
pipe_fluid_meshing.workflow.TaskObject["Generate the Volume Mesh"].Execute()

pipe_fluid_session = pipe_fluid_meshing.switch_to_solver()

#===

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

pipe_solid_meshing = pyfluent.launch_fluent(product_version="24.1.0", mode="meshing", start_transcript=False)
pipe_solid_meshing.workflow.InitializeWorkflow(WorkflowType="Watertight Geometry")

pipe_solid_meshing.workflow.TaskObject["Import Geometry"].Arguments = {
    "FileName": "pipe_solid.scdoc",
    "LengthUnit": "m",
}

pipe_solid_meshing.workflow.TaskObject["Import Geometry"].Execute()

pipe_solid_meshing.workflow.TaskObject["Add Local Sizing"].AddChildToTask()
pipe_solid_meshing.workflow.TaskObject["Add Local Sizing"].Execute()

pipe_solid_meshing.workflow.TaskObject["Generate the Surface Mesh"].Arguments = {
    "CFDSurfaceMeshControls": {"MaxSize": 0.01}
}

pipe_solid_meshing.workflow.TaskObject["Generate the Surface Mesh"].Execute()

pipe_solid_meshing.workflow.TaskObject["Describe Geometry"].UpdateChildTasks(
    SetupTypeChanged=False
)

pipe_solid_meshing.workflow.TaskObject["Describe Geometry"].Arguments = {
    "SetupType": "The geometry consists of only solid regions"
}

pipe_solid_meshing.workflow.TaskObject["Describe Geometry"].UpdateChildTasks(SetupTypeChanged=True)
pipe_solid_meshing.workflow.TaskObject["Describe Geometry"].Execute()

pipe_solid_meshing.workflow.TaskObject["Update Boundaries"].Execute()

pipe_solid_meshing.workflow.TaskObject["Update Regions"].Execute()

pipe_solid_meshing.workflow.TaskObject["Generate the Volume Mesh"].Arguments = {
    "VolumeFill": "tetrahedral",
}
pipe_solid_meshing.workflow.TaskObject["Generate the Volume Mesh"].Execute()

pipe_solid_meshing.tui.mesh.check_mesh()

pipe_solid_session = pipe_solid_meshing.switch_to_solver()

#===

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
# the coupled analysis takes about 80 iterations to converge
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
