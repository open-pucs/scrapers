"""
Master test script for Illinois ICC scrapers.
This script runs all individual test scripts to validate each
aspect of the Illinois ICC scraping functionality.
"""
import sys
import os
import importlib.util

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added {project_root} to Python path")

def load_module(module_name, file_path):
    """Load a module from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_test_module(module_path, module_name):
    """Run a test module and report success/failure."""
    print(f"\n{'='*50}")
    print(f"RUNNING TEST: {module_name}")
    print(f"{'='*50}")
    
    try:
        module = load_module(module_name, module_path)
        result = module.main()
        success = result == 0
        
        print(f"\nTEST RESULT: {module_name} {'PASSED' if success else 'FAILED'}")
        print(f"{'='*50}\n")
        return success
    except Exception as e:
        print(f"\nERROR running {module_name}: {e}")
        import traceback
        traceback.print_exc()
        print(f"\nTEST RESULT: {module_name} FAILED")
        print(f"{'='*50}\n")
        return False

def main():
    """Run all IL scraper tests."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define test modules to run in order
    test_modules = [
        ("test_service_list.py", "test_service_list"),
        ("test_schedule.py", "test_schedule"),
        ("test_documents.py", "test_documents"),
        ("test_case_summary.py", "test_case_summary"),
        ("test_docket_sheet.py", "test_docket_sheet")
    ]
    
    results = {}
    
    # Run each test module
    for filename, module_name in test_modules:
        module_path = os.path.join(script_dir, filename)
        
        if not os.path.exists(module_path):
            print(f"WARNING: Test module {module_path} not found, skipping")
            results[module_name] = False
            continue
            
        results[module_name] = run_test_module(module_path, module_name)
    
    # Print summary
    print("\n\n")
    print(f"{'='*50}")
    print("ILLINOIS ICC SCRAPER TEST SUMMARY")
    print(f"{'='*50}")
    
    for module_name, success in results.items():
        print(f"{module_name}: {'PASSED' if success else 'FAILED'}")
    
    # Overall result
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print(f"\nOverall: {success_count}/{total_count} tests passed")
    
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main()) 