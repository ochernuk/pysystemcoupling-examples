import os

import ansys.systemcoupling.core as pysyc

session = pysyc.launch()

m = session.setup.add_participant(input_file = os.path.join("mech", "mech.scp"))
f = session.setup.add_participant(input_file = os.path.join("fluent", "fluent.scp"))

interface = session.setup.add_interface(
    side_one_participant = 'MAPDL-1',
    side_one_regions = ['FSIN_1'],
    side_two_participant = 'FLUENT-2',
    side_two_regions = ['wall1', 'wall3', 'wall2', 'wall4'])

session.setup.add_data_transfer(
    interface = interface,
    target_side = 'Two',
    side_one_variable = 'TEMP',
    side_two_variable = 'temperature')

session.setup.add_data_transfer(
    interface = interface,
    target_side = 'One',
    side_one_variable = 'HFLW',
    side_two_variable = 'heatflow')

session.setup.solution_control.maximum_iterations = 25

session.setup.analysis_control.global_stabilization.option = 'Quasi-Newton'

session.start_output()
session.solve()
session.end_output()

session.exit()
