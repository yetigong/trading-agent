import unittest
import sys
import os
import argparse

def run_tests(test_type=None, verbosity=2):
    """
    Run the test suite.
    
    Args:
        test_type (str): Type of tests to run ('unit', 'integration', or None for all)
        verbosity (int): Test output verbosity (1-3)
    """
    # Add the project root to the Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(project_root, 'tests')
    
    if test_type:
        # Run specific test type
        if test_type == 'unit':
            # Run all unit tests
            suite = loader.discover(start_dir, pattern='test_*.py', top_level_dir=start_dir)
        elif test_type == 'integration':
            # Run only integration tests
            suite = loader.discover(os.path.join(start_dir, 'integration'), pattern='test_*.py')
        else:
            print(f"Unknown test type: {test_type}")
            return 1
    else:
        # Run all tests
        suite = loader.discover(start_dir, pattern='test_*.py')

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    # Return non-zero exit code if tests failed
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run trading agent tests')
    parser.add_argument('--type', choices=['unit', 'integration'], help='Type of tests to run')
    parser.add_argument('--verbosity', type=int, choices=[1, 2, 3], default=2, help='Test output verbosity')
    args = parser.parse_args()

    sys.exit(run_tests(args.type, args.verbosity)) 