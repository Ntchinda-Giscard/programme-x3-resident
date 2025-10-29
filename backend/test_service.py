# Save this as test_service_install.py in the same directory as service_manager.py
# Run it directly: python test_service_install.py

import sys
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG for even more detail
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('diagnostic.log')
    ]
)

logger = logging.getLogger(__name__)

def trace_function_calls():
    """Enable tracing to see every line of code that executes"""
    import sys
    
    def trace_calls(frame, event, arg):
        if event != 'line':
            return
        # Only trace service_manager module
        if 'service_manager' in frame.f_code.co_filename:
            line_no = frame.f_lineno
            func_name = frame.f_code.co_name
            filename = frame.f_code.co_filename
            logger.debug(f"TRACE: {filename}:{line_no} in {func_name}")
        return trace_calls
    
    sys.settrace(trace_calls)

def main():
    logger.info("=" * 80)
    logger.info("DIAGNOSTIC TEST - Service Installation")
    logger.info("=" * 80)
    
    # Import service_manager
    try:
        logger.info("Step 1: Importing service_manager module...")
        import service_manager
        logger.info("✓ service_manager imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import service_manager: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check if install_service function exists
    logger.info("\nStep 2: Checking if install_service function exists...")
    if hasattr(service_manager, 'install_service'):
        logger.info("✓ install_service function found")
        
        # Get function details
        import inspect
        func = service_manager.install_service
        source_file = inspect.getfile(func)
        source_lines = inspect.getsourcelines(func)
        line_number = source_lines[1]
        
        logger.info(f"  Function defined in: {source_file}")
        logger.info(f"  Starting at line: {line_number}")
        logger.info(f"  Total lines in function: {len(source_lines[0])}")
        
        # Show first 10 lines of the function
        logger.info("\n  First 10 lines of function:")
        for i, line in enumerate(source_lines[0][:10], start=line_number):
            logger.info(f"    {i}: {line.rstrip()}")
    else:
        logger.error("✗ install_service function NOT found!")
        return
    
    # Enable line-by-line tracing
    logger.info("\nStep 3: Enabling line-by-line execution tracing...")
    trace_function_calls()
    
    # Try to call install_service
    logger.info("\nStep 4: Calling install_service()...")
    logger.info("-" * 80)
    
    try:
        result = service_manager.install_service()
        
        logger.info("-" * 80)
        logger.info(f"\nStep 5: Function returned successfully!")
        logger.info(f"  Return value: {result}")
        logger.info(f"  Return type: {type(result)}")
        
        if result is None:
            logger.error("\n⚠ WARNING: Function returned None!")
            logger.error("This means the function completed but didn't return a value.")
            logger.error("Check the diagnostic.log file to see which lines were executed.")
        else:
            logger.info(f"\n✓ SUCCESS: {result}")
            
    except Exception as e:
        logger.info("-" * 80)
        logger.error(f"\nStep 5: Function raised an exception!")
        logger.error(f"  Exception type: {type(e).__name__}")
        logger.error(f"  Exception message: {str(e)}")
        logger.error("\nFull traceback:")
        import traceback
        traceback.print_exc()
    
    # Disable tracing
    sys.settrace(None)
    
    logger.info("\n" + "=" * 80)
    logger.info("DIAGNOSTIC TEST COMPLETE")
    logger.info("Check 'diagnostic.log' for detailed line-by-line execution trace")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()