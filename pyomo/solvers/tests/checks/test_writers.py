#  _________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright (c) 2014 Sandia Corporation.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  This software is distributed under the BSD License.
#  _________________________________________________________________________

import os
from os.path import join, dirname, abspath
import warnings
import types
try:
    import new
    new_available=True
except:
    new_available=False

import pyutilib.th as unittest
from pyomo.solvers.tests.models.base import test_models
from pyomo.solvers.tests.testcases import test_scenarios


# The test directory
thisDir = dirname(abspath( __file__ ))

# Cleanup Expected Failure Results Files
_cleanup_expected_failures = True


#
# A function that function that returns a function that gets
# added to a test class.
#
def create_test_method(model, solver, io,
                     test_case,
                     symbolic_labels):

    is_expected_failure = test_case.status == 'expected failure'

    #
    # Create a function that executes the test
    #
    def writer_test(self):

        model_class = test_case.model
        save_filename = join(thisDir, ("%s.soln.json" % model_class.description))

        # cleanup possibly existing old test files
        if os.path.exists(save_filename):
            os.remove(save_filename)

        # Create the model instance
        model_class.generate_model(test_case.testcase.import_suffixes)
        model_class.warmstart_model()

        # solve
        opt, results = model_class.solve(solver, io, test_case.testcase.io_options, symbolic_labels)

        # validate the solution returned by the solver
        model_class.post_solve_test_validation(self, results)
        model_class.model.solutions.load_from(results, default_variable_value=opt.default_variable_value())
        model_class.save_current_solution(save_filename, suffixes=model_class.test_suffixes)
        rc = model_class.validate_current_solution(suffixes=model_class.test_suffixes)

        if is_expected_failure:
            if rc[0] is True:
                warnings.warn("\nTest model '%s' was marked as an expected "
                              "failure but no failure occured. The "
                              "reason given for the expected failure "
                              "is:\n\n****\n%s\n****\n\n"
                              "Please remove this case as an expected "
                              "failure if the above issue has been "
                              "corrected in the latest version of the "
                              "solver." % (model_class.description, failure_msg))
            if _cleanup_expected_failures:
                os.remove(save_filename)

        if not rc[0]:
            try:
                model_class.model.solutions.store_to(results)
            except ValueError:
                pass
            self.fail("Solution mismatch for plugin "+name
                      +', '+io+
                      " interface and problem type "
                      +model_class.description+"\n"+rc[1]+"\n"
                      +(str(results.Solution(0)) if len(results.solution) else "No Solution"))

        # cleanup if the test passed
        try:
            os.remove(save_filename)
        except OSError:
            pass

    # Skip this test if the status is 'skip'
    if test_case.status == 'skip':
        def skipping_test(self):
            return self.skipTest(test_case.msg)
        return skipping_test

    if is_expected_failure:
        #print "FAILURE", model, solver, io
        @unittest.expectedFailure
        def failing_writer_test(self):
            return writer_test(self)
        # Return a test that is expected to fail
        return failing_writer_test

    #print "OK", model, solver, io
    # Return a normal test
    return writer_test


#
# Create test driver classes for each test model
#
driver = {}
for model in test_models():
    # Get the test case for the model 
    case = test_models(model)()
 
    # Create the test class
    name = "Test_%s" % model
    if new_available:
        cls = new.classobj(name, (unittest.TestCase,), {})
    else:
        cls = types.new_class(name, (unittest.TestCase,))
    cls = unittest.category(*case.level)(cls)
    driver[model] = cls
    globals()[name] = cls
#
# Iterate through all test scenarios and add test methods
#
for key, value in test_scenarios():
    model, solver, io = key
    cls = driver[model]
    # Symbolic labels
    test_name = "test_"+solver+"_"+io +"_symbolic_labels"
    test_method = create_test_method(model, solver, io, value, True)
    if test_method is not None:
        setattr(cls, test_name, test_method)
    # Non-symbolic labels
    test_name = "test_"+name+"_"+io +"_nonsymbolic_labels"
    test_method = create_test_method(model, solver, io, value, False)
    if test_method is not None:
        setattr(cls, test_name, test_method)


# A "solver should fail" test, which I am archiving for now
"""
            # If the solver is not capable of handling this
            # model class then we better get a failure here
            try:
                model.load(opt.solve(model))
                model_class.saveCurrentSolution(save_filename,
                                        suffixes=test_case.import_suffixes)
            except:
                pass
            else:
                # Okay so we may get to this point if we are using a
                # plugin like ASL which must advertise having all capabilities
                # since it supports many solvers. And its possible that
                # sending something like a discrete model to ipopt can slip
                # through the cracks without error or warning. Hopefully the test
                # case was set up so that the solution check will turn up bad.
                if model_class.validateCurrentSolution() is True:
                    warnings.warn("Plugin "+test_case.name+' ('+test_case.io+") is not capable of handling model class "+test_model_name+" "\
                                  "but no exception was thrown and solution matched baseline.")
"""

if __name__ == "__main__":
    unittest.main()
