import ansys.systemcoupling.core as pysyc

syc = pysyc.launch(version = "24.2")
syc.start_output()

s = syc.setup.add_participant(input_file = "source.scdt")
t = syc.setup.add_participant(input_file = "target.scdt")

i = syc.setup.add_interface(
  side_one_participant = s,
  side_one_regions = ["source"],
  side_two_participant = t,
  side_two_regions = ["target"],
)

syc.setup.add_data_transfer(
  interface = i,
  target_side = "Two",
  source_variable = "variable",
  target_variable = "variable",
)

# this produces target-output.scdt with target data interpolated
# onto the target point cloud
syc.solution.solve()
