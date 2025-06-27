"""
Simple test script for the Wind Turbine Power Correction Application
"""

import os
import sys
import logging

# Configure logging for testing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all required modules can be imported."""
    try:
        import pandas as pd
        logger.info("✓ pandas imported successfully")
        
        import numpy as np
        logger.info("✓ numpy imported successfully")
        
        import scipy
        logger.info("✓ scipy imported successfully")
        
        # Test local imports
        import input
        logger.info("✓ input module imported successfully")
        
        import blanket
        logger.info("✓ blanket module imported successfully")
        
        import roughness
        logger.info("✓ roughness module imported successfully")
        
        import power_output
        logger.info("✓ power_output module imported successfully")
        
        import write_data
        logger.info("✓ write_data module imported successfully")
       
        return True
        
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False


def test_config():
    """Test configuration loading."""
    try:
        from config import DIRECTORIES, PHYSICAL_CONSTANTS, WIND_SPEEDS, PROCESSING_CONFIG
        logger.info("✓ Configuration loaded successfully")
        
        # Test that required keys exist
        required_dirs = ['input', 'output', 'real', 'supply']
        for dir_key in required_dirs:
            if dir_key in DIRECTORIES:
                logger.info(f"✓ Directory config '{dir_key}' found")
            else:
                logger.error(f"✗ Directory config '{dir_key}' missing")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Configuration error: {e}")
        return False


def test_processor_creation():
    """Test WindTurbineProcessor creation."""
    try:
        from app import WindTurbineProcessor
        
        # Test basic creation
        processor = WindTurbineProcessor()
        logger.info("✓ WindTurbineProcessor created successfully")
        
        # Test that required attributes exist
        required_attrs = ['directories', 'constants', 'processing_config', 'file_patterns']
        for attr in required_attrs:
            if hasattr(processor, attr):
                logger.info(f"✓ Processor attribute '{attr}' exists")
            else:
                logger.error(f"✗ Processor attribute '{attr}' missing")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Processor creation error: {e}")
        return False


def test_directory_creation():
    """Test directory creation functionality."""
    try:
        from app import WindTurbineProcessor
        
        processor = WindTurbineProcessor()
        
        # Test that directories are created
        for dir_name, dir_path in processor.directories.items():
            if os.path.exists(dir_path):
                logger.info(f"✓ Directory '{dir_name}' exists: {dir_path}")
            else:
                logger.warning(f"⚠ Directory '{dir_name}' does not exist: {dir_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Directory creation error: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("Starting application tests...")
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config),
        ("Processor Creation Test", test_processor_creation),
        ("Directory Creation Test", test_directory_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        if test_func():
            passed += 1
            logger.info(f"✓ {test_name} PASSED")
        else:
            logger.error(f"✗ {test_name} FAILED")
    
    logger.info(f"\n--- Test Results ---")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 