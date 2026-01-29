import os
import xml.etree.ElementTree as ET
import re
import traceback
import csv

# local imports
import bme_parser


# Main Process XML data.
def xml_parse(file_path, logger):
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    logger.info(f"Starting a new job")
    logger.info(f"Processing file: {file_name}")
    # Get encoding
    encoding = get_encoding_prolog(file_path, logger)
    logger.debug(f"XML file encoding: {encoding}")
    # Check doctype and bmecat tags
    if check_bmecat_and_doctype(file_path, logger, encoding):
        try:
            # Get ElementTree root
            ET_root = get_xml_root(file_path, logger)
            if ET_root is None:
                logger.error("xml_parse XML ET_root is none, return.")
                return
            #logger.info(f"Zpracovávání dat")
            bme_parser.parse_BME_header(ET_root, file_name, logger)
            bme_parser.parse_BME_products(ET_root, file_name, logger)

        except Exception as e:
            logger.error(f"Error in function xml_parse: {e}")  
            logger.error(traceback.format_exc())
    else:
        logger.warning(f"Attempting as a generic xml file")
        ET_root = get_xml_root(file_path, logger)
        save_generic_xml(ET_root, file_name, logger)

# Check if the specified file has an XML prolog.
def get_encoding_prolog(file_path, logger):
    ENCODINGS_TO_TRY = ['utf-8', 'utf-16', 'windows-1252', 'latin-1']
    for encoding in ENCODINGS_TO_TRY:
        try:
            logger.info(f"Trying to open file using encoding: {encoding}")
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read(1024).strip()  # Read first 1024 characters
                # Regular expression to match XML prolog with encoding attribute
                prolog_pattern = r'<\?xml\s+version=["\']1\.[0-9]["\']\s*(encoding=["\']([^"\']+)["\'])?\s*(standalone=["\'](yes|no)["\'])?\s*\?>'
                prolog_match = re.search(prolog_pattern, content)
                if prolog_match:
                    prolog = prolog_match.group(0).strip()
                    declared_encoding = prolog_match.group(2)  # Capture the encoding if present
                    standalone = prolog_match.group(4)  # Capture the standalone attribute if present
                    logger.info(f"XML prolog is valid, prolog encoding is: {declared_encoding}")
                    logger.debug(f"XML prolog: {prolog}")
                    if standalone:
                        logger.debug(f"Standalone attribute in prolog: {standalone}")
                    if declared_encoding is None:
                        logger.warning(f"Prolog encoding not found. Default encoding: {encoding}")
                        return encoding
                    return declared_encoding
                else:
                    logger.error(f"XML prolog not found. Using encoding: {encoding}")
                    return encoding
        except Exception as e:
            logger.error(f"Error in function check_xml_prolog: {e}")

# Check DOCTYPE & BMECAT tags
def check_bmecat_and_doctype(file_path, logger, encoding='utf-8'):
    # Helper Extract tag for check DOCTYPE & BMEСAT
    def extract_tag(content, tag_name, logger):
        tag_start = content.find(tag_name)
        if tag_start != -1:
            tag_end = content.find('>', tag_start) + 1  # Include the closing '>'
            tag_content = content[tag_start:tag_end]
            logger.debug(f"{tag_name} found: {tag_content}")
            return tag_content
        logger.info(f"{tag_name} not found")
      
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            # Read the first 512 characters
            content = file.read(512)
            doctype_content = extract_tag(content, '<!DOCTYPE', logger)
            BMECAT_content = extract_tag(content, '<BMECAT', logger)
            if BMECAT_content is not None:
                if "version=\"2005\"" in BMECAT_content:
                    logger.info("BMEcatalog version: 2005")
                return True
            else:
                logger.error("File is not in ETIM format")
                return False
    except Exception as e:
        logger.error(f"Error in function validate_BMEcat: {e}")
        return False

# Validate XML
def get_xml_root(file_path, logger):
    try:
        # Parse the XML file
        tree = ET.parse(file_path)
        root = tree.getroot()
        logger.info("XML file is valid.")
        # Check if there is a namespace        
        if '}' in root.tag:
            namespace = root.tag.split('}')[0].strip('{')  # Get the namespace URI
            logger.info(f"Namespace: {namespace}")
        else:
            namespace = None
            logger.info("Namespace not found.")
        # Strip namespace
        for elem in root.iter():
            elem.tag = elem.tag.split("}")[-1]  # Strip namespace from each tag
        return root
    except ET.ParseError as e:
        logger.error(f"Error in XML file: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in function validate_xml: {e}")
        return None
        

def save_generic_xml(xml_root, output_csv, logger):
    output_csv = "output/"+output_csv+".csv"
    # Detect all product tags
    product_tags = {"item", "SHOPITEM", "PRODUCT"}
    products = []
    
    # Iterate over matching elements
    for product in xml_root.findall(".//*"):
        if product.tag in product_tags:
            product_data = {}
            for element in product:
                product_data[element.tag] = element.text.strip() if element.text else ""
            products.append(product_data)
    
    # Determine all possible column names
    all_columns = set()
    for product in products:
        all_columns.update(product.keys())
    all_columns = sorted(all_columns)  # Sort for consistency
    
    if products:
        # Write to CSV
        with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_columns)
            writer.writeheader()
            writer.writerows(products)
        logger.info(f"Saved file: {output_csv}")
    else:
        logger.error(f"No data to save: {output_csv}")
