import sys
import signal
import os
import logging


# local imports
import xml_utils

def handle_keyboard_interrupt(signum, frame):
    logging.info("Received Ctrl+C (KeyboardInterrupt). Aborting.")
    raise SystemExit

def setup_signal_handler():
    signal.signal(signal.SIGINT, handle_keyboard_interrupt)

# Set up logging to both console and a file.
def setup_logging(log_file='BME_parse.log', log_level=logging.DEBUG):
    # Create a logger
    logger = logging.getLogger()
    # Set the logging level
    logger.setLevel(log_level)  # Set the logging level for the logger
    # Create a file handler with UTF-8 encoding
    file_handler_output = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler_output.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    # Create a stream handler to output to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    # Add the handlers to the logger
    logger.addHandler(file_handler_output)
    logger.addHandler(console_handler)
    return logger

# Print help
def print_help():
    help_message = """
    Usage: BME-tool.exe <XML_file>
    
    Arguments:
        <XML_file> : Path to the BMEcat (ETIM) XML file.
    
    If no argument is given or if the provided argument is not a valid XML file, this help will be shown.
    Processing can be interrupted with 'Ctrl + C'.
    """
    print(help_message)

# Main & arg check
def main():
    # Check if debug flag is present
    debug_mode = "-debug" in sys.argv
    # Remove debug argument if present
    args = [arg for arg in sys.argv[1:] if arg != "-debug"]
    
    # Check if a file argument is provided
    if len(args) > 0:
        droppedFile = args[0]
        # Check if the provided file exists
        if os.path.exists(droppedFile):
            # Ensure the output directory exists
            os.makedirs('output', exist_ok=True)
            xml_file = droppedFile
            file_name = os.path.splitext(os.path.basename(xml_file))[0]
            log_level = logging.DEBUG if debug_mode else logging.INFO
            logger = setup_logging(log_file = "output/" + file_name + "_log.txt", log_level=log_level)
            
            # Process the XML file
            xml_utils.xml_parse(xml_file, logger)
            
        else:
            logger = setup_logging(log_file = "error_log.txt")
            logger.error(f"File '{droppedFile}' does not exist.")
            print_help()
            return
        
    else:
        print_help()
        print("Press any key to exit...")
        os.system('pause >nul')
        #input("Press any key to exit...")

if __name__ == "__main__":
    setup_signal_handler()
    main()
