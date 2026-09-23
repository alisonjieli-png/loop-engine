"""Step execution: the step edge, the step attempt envelope and its engines.

One step's assignment crosses one versioned edge into one step executor
engine, a separately started harness instance; completion is never
acceptance. Engines of this component live here, one module each.
"""
