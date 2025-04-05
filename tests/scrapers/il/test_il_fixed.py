"""
Test script to verify imports are working correctly.
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"Added {project_root} to Python path")

def test_imports():
    """Test that required modules can be imported."""
    errors = []
    
    print("Testing imports...")
    
    try:
        print("Importing base module...")
        from openpuc_scrapers.scrapers.base import GenericScraper
        print("✓ Successfully imported GenericScraper")
    except ImportError as e:
        errors.append(f"Failed to import GenericScraper: {e}")
    
    try:
        print("Importing Illinois scraper and models...")
        from openpuc_scrapers.scrapers.il import (
            IllinoisICC, 
            ILICCServiceListEntry, 
            ILICCScheduleEntry,
            ILICCCaseData,
            ILICCFilingData
        )
        print("✓ Successfully imported IllinoisICC and models")
    except ImportError as e:
        errors.append(f"Failed to import Illinois scraper and models: {e}")
    
    try:
        print("Testing creating scraper instance...")
        from openpuc_scrapers.scrapers.il import IllinoisICC
        scraper = IllinoisICC()
        print("✓ Successfully created scraper instance")
    except Exception as e:
        errors.append(f"Failed to create scraper instance: {e}")
        import traceback
        traceback.print_exc()
    
    if errors:
        print("\nERRORS:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("\nAll imports and basic tests succeeded!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 