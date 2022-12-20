import ansys.systemcoupling.core as pysyc

syc = pysyc.launch()

# make sure connection is established successfully
assert syc.ping()

setup = syc.setup # datamodel setup
case = syc.case # case-related operations (open/save/open_snapshot)
solution = syc.solution # solve-related operations
api = syc.native_api

api.ActivateHidden.BetaFeatures = True
api.ActivateHidden.AlphaFeatures = True
api.ActivateHidden.LenientValidation = True
api.AnalysisControl.AnalysisType = "Steady"
syc.start_output()
solution.solve()
syc.end_output()
syc.exit()
