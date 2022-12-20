import os

def solve_coupled_analysis():
  import ansys.systemcoupling.core as pysyc
  
  with pysyc.launch() as syc:  

    print("Setting up the coupled analysis")

    fluent_name = syc.setup.add_participant(
      input_file = os.path.join("Fluent", "fluent.scp"))

    mapdl_name = syc.setup.add_participant(
      input_file = os.path.join("Mapdl", "mapdl.scp"))

    fsi_name = syc.setup.add_interface(
      side_one_participant = fluent_name, side_one_regions = ['wall_deforming'],
      side_two_participant = mapdl_name, side_two_regions = ['FSIN_1'])

    syc.setup.add_data_transfer(
      interface = fsi_name, target_side = 'One',
      source_variable = 'INCD', target_variable = 'displacement')

    syc.setup.add_data_transfer(
      interface = fsi_name, target_side = 'Two',
      source_variable = 'force', target_variable = 'FORC')

    syc.setup.solution_control.maximum_iterations = 7

    print("Solving the coupled analysis. This may take a while...")

    syc.solve()

    print("...done!")

def set_inlet_velocity(inlet_velocity):
  import ansys.fluent.core as pyfluent
  with pyfluent.launch_fluent(precision="double", processor_count=2) as session:
      case_file = os.path.join("Fluent", "case.cas.gz")
      session.solver.root.file.read(file_type="case", file_name=case_file)
      session.solver.root.setup.boundary_conditions.velocity_inlet["wall_inlet"].vmag = inlet_velocity
      session.solver.tui.file.write_case(case_file)

  print(f"Inlet velocity is set to {inlet_velocity}")

def set_youngs_modulus(youngs_modulus):
  '''
  This function updates Young's Modulus value in existing
  MAPDL input file, ds.dat, located in "Mapdl" sub-folder
  '''
  # read ds.dat and manually insert the Young's modulus value
  # is it possible to use pyMapdl to do this instead?
  replacement = str()
  with open(os.path.join("Mapdl", "ds.dat"), "r") as f:
    for line in f:
      if line.startswith('MP,EX,1,'):
        line = "MP,EX,1," + str(youngs_modulus) + ",	! C^-1\n"
      replacement = replacement + line

  with open(os.path.join("Mapdl", "ds.dat"), "w") as f:
    f.write(replacement)
    
  print(f"Young's Modulus is set to {youngs_modulus}")

def extract_max_displacement_value():
  print("Extracting max displacement value")
  import ansys.dpf.core as pydpf
  model = pydpf.Model(os.path.join(os.getcwd(), "Mapdl", "file.rst"))
  displacements = model.results.displacement()
  fields = displacements.outputs.fields_container()
  value = max([v[0] for v in fields[0].data])
  print("Max displacement value = " + str(value))
  return value

def get_max_displacement(youngs_modulus):
  set_youngs_modulus(youngs_modulus)
  # setting inlet velocity does not work yet
  # due to clash b/w pyFluent and pySystemCoupling
  #set_inlet_velocity(inlet_velocity)
  solve_coupled_analysis()
  return extract_max_displacement_value()

def plot(x, y):
  import matplotlib.pyplot as plt
  fig, ax = plt.subplots()
  ax.plot(x/1e6, y, "-o")
  ax.set(
    xlabel="Young's Modulus [MPa]",
    ylabel='Max Displacement [m]',
    title="Plate max displacement vs. Young's Modulus")
  ax.grid()
  plt.show()

def plot3d(x, y, z):
  import matplotlib.pyplot as plt
  fig = plt.figure()
  ax = fig.add_subplot(111, projection='3d')
  ax.scatter(x, y, z, c='r', marker='o')
  ax.set_xlabel("Young's Modulus [Pa]")
  ax.set_ylabel("Inlet velocity [m/s]")
  ax.set_zlabel("Max Displacement [m]")
  plt.show()

# =====================================================================

import numpy as np

x = np.array([2E6, 3E6, 4E6])
y = np.array([0.0] * len(x))

for index, youngs_modulus in enumerate(x):
  y[index] = get_max_displacement(youngs_modulus)

plot(x, y)

"""
# does not work yet
x = np.array([2E6, 4E6, 6E6])
y = np.array([10.0, 15.0, 20.0])
z = np.array([0.0] * len(x))

for index, (youngs_modulus, inlet_velocity) in enumerate(zip(x, y)):
  z[index] = get_max_displacement(youngs_modulus, inlet velocity)

plot3d(x, y, z)
"""
