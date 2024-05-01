import ansys.systemcoupling.core as pysyc

syc = pysyc.launch()
syc.start_output()

# add FMU participants
fmu1 = syc.setup.add_participant(input_file = 'rootFind.fmu')
fmu2 = syc.setup.add_participant(input_file = 'rootFind.fmu')

# create coupling interface between FMUs
interface_name = syc.setup.add_interface(
    side_one_participant = fmu1,
    side_two_participant = fmu2)

dt_names = syc.setup.add_ordered_data_transfers(interface = interface_name)
for dt_name in dt_names:
    dt = syc.setup.coupling_interface[interface_name].data_transfer[dt_name]
    dt.convergence_target = 1E-12

# setup steady analysis
syc.setup.analysis_control.analysis_type = "Steady"
syc.setup.solution_control.maximum_iterations = 100
syc.setup.output_control.generate_csv_chart_output = True

#solve
syc.solution.solve()

syc.end_output()
syc.exit()
