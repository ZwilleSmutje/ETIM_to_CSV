import os
import csv
import xml.etree.ElementTree as ET

# Remove namespace from tag
def clean_tag(tag):
    return tag.split('}')[-1]

# Create a key from tag & attributes
def create_key(tag, attributes):
    if attributes:
        attr_parts = [f"@{k}:{v}" for k, v in attributes.items()]
        return f"{tag} {' '.join(attr_parts)}"
    return tag

# Recursive XML Parsing
def parse_element(element, logger):
    if element is None:
        logger.warning("Element not found (None).")
        return None

    parsed_data = {}
    # Process a single child element.
    for child in element:
        tag = clean_tag(child.tag)
        combined_key = create_key(tag, child.attrib)
        # Recursively parse child elements
        child_data = parse_element(child, logger) if len(child) else (child.text.strip() if child.text else None)
        # Handle multiple occurrences of the same key
        if combined_key in parsed_data:
            if not isinstance(parsed_data[combined_key], list):
                parsed_data[combined_key] = [parsed_data[combined_key]]
            parsed_data[combined_key].append(child_data)
        else:
            parsed_data[combined_key] = child_data
            
    return parsed_data

# Flatten nested dictionary
def flatten_dict(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items()) if isinstance(item, dict) else items.append((f"{new_key}_{i}", item))
        else:
            items.append((new_key, v))
    return dict(items)



# Generic CSV Writing Function
def save_to_csv(file_name, data, logger):
    if not data:
        logger.warning(f"No Data to Save: {file_name}.csv")
        return
    
    os.makedirs("output", exist_ok=True)
    csv_file = f'output/{file_name}.csv'
    
    # Collect column headers dynamically
    fieldnames = sorted({key for row in data for key in row.keys()})
    if 'SUPPLIER_PID' in fieldnames:
        fieldnames.remove('SUPPLIER_PID')  # Remove it temporarily
        fieldnames = ['SUPPLIER_PID'] + fieldnames  # Add it as the first column
    
    with open(csv_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    logger.info(f"File saved: {csv_file}")

# Parse HEADER
def parse_BME_header(root, file_name, logger):
    header = next(root.iterfind(".//HEADER"), None)
    if not header:
        logger.warning("HEADER in XML-Data not found.")
        return
    
    logger.info("Analysing HEADER dat.")
    parsed_header = parse_element(header, logger)
    lang_def = parsed_header.get("CATALOG", {}).get("LANGUAGE @default:true", parsed_header.get("CATALOG", {}).get("LANGUAGE", ''))
    logger.info(f"Default language:: {lang_def}")
    logger.debug("Header data: %s", parsed_header)
    flat_header = flatten_dict(parsed_header)
    save_to_csv(f"{file_name}_header", [flat_header], logger)

def parse_BME_products(root, file_name, logger):
    all_product_entries, all_mime_entries, all_keyword_entries = [], [], []
    all_packing_entries, all_udx_logistics_entries = [], []

    logger.info("PRODUCT data analysis")

    for product in root.iterfind(".//PRODUCT"):
        product_data = parse_element(product, logger)
        supplier_pid = next((product_data[key] for key in product_data if key.startswith("SUPPLIER_PID")), "N/A")
        product_details = product_data.get("PRODUCT_DETAILS", {})
        logger.debug(f"I am processing the product:{supplier_pid}")

        # EAN parse
        product_details_lower = {key.lower(): value for key, value in product_details.items()}
        ean_keys = ["ean", "international_pid @type:ean", "international_pid @type:gtin"]
        inter_pid_ean = next((product_details_lower[key] for key in ean_keys if key in product_details_lower), None)
        logger.debug(f"EAN: {inter_pid_ean}")
        if not inter_pid_ean:
            logger.warning(f"EAN not found for product {supplier_pid}")

        # Parse product details
        product_entries = parse_BME_product(product_data, logger)
        for entry in product_entries:
            entry["SUPPLIER_PID"] = supplier_pid
            all_product_entries.append(entry)

        # Parse MIME data
        mime_data = parse_BME_mime(product_data, logger)
        for entry in mime_data:
            entry["SUPPLIER_PID"] = supplier_pid
            entry["EAN"] = inter_pid_ean
            all_mime_entries.append(entry)

        # Parse Keywords
        keyword_entries = parse_BME_keyword(product_data, logger)
        all_keyword_entries.extend(keyword_entries)

        # ---- NEW: Parse UDX packing + logistics ----
        packing_units, udx_logistics = parse_udx_packing_and_logistics(product_data, logger)

        # packing_units is a list
        for pu in packing_units:
            pu["SUPPLIER_PID"] = supplier_pid
            pu["EAN"] = inter_pid_ean
            all_packing_entries.append(pu)

        # udx_logistics is a dict (single record)
        if udx_logistics:
            udx_logistics["SUPPLIER_PID"] = supplier_pid
            udx_logistics["EAN"] = inter_pid_ean
            all_udx_logistics_entries.append(udx_logistics)

    save_to_csv(f"{file_name}_products", all_product_entries, logger)
    save_to_csv(f"{file_name}_files", all_mime_entries, logger)
    save_to_csv(f"{file_name}_keywords", all_keyword_entries, logger)

    # NEW: packing units and logistics
    save_to_csv(f"{file_name}_packing_units", all_packing_entries, logger)
    save_to_csv(f"{file_name}_udx_logistics", all_udx_logistics_entries, logger)








# Parse MIME    
def parse_BME_mime(data, logger):
    mime_entries = []
    valid_mime_codes = {
        "MD01": "Product picture",
        "MD02": "Similar figure",
        "MD03": "Safety data sheet",
        "MD04": "Deeplink product page",
        "MD05": "Deeplink REACH",
        "MD06": "Energy label",
        "MD07": "Product data sheet for energy label",
        "MD08": "Calibration certificate",
        "MD09": "Certificate",
        "MD10": "Circuit diagram",
        "MD11": "Construction Products Regulation",
        "MD12": "Dimensioned drawing",
        "MD13": "Environmental label",
        "MD14": "Instructions for use",
        "MD15": "Light cone diagram",
        "MD16": "Light Distribution Curve",
        "MD17": "Logo 1c",
        "MD18": "Logo 4c",
        "MD19": "Luminaire data",
        "MD20": "Ambient picture",
        "MD21": "Mounting instruction",
        "MD22": "Product data sheet",
        "MD23": "Product picture – back view",
        "MD24": "Product picture – bottom view",
        "MD25": "Product picture – detailed view",
        "MD26": "Product picture – front view",
        "MD27": "Product picture – angled view",
        "MD28": "Product picture – top view",
        "MD29": "Product picture – left side view",
        "MD30": "Product picture – right side view",
        "MD31": "Seal of approval",
        "MD32": "Technical manual",
        "MD32_DE": "Technical manual_DE",
        "MD33": "Test approval",
        "MD34": "Wiring diagram",
        "MD35": "Supplier’s declaration for products having preferential origin status",
        "MD36": "Declaration",
        "MD37": "3D / BIM object",
        "MD38": "Management, operation and maintenance document",
        "MD39": "Instructional video",
        "MD40": "Spare parts list",
        "MD41": "Sales brochure",
        "MD42": "AVCP certificate (Assessment and Verification of Constancy of Performance)",
        "MD43": "CLP (Classification, Labelling and Packaging)",
        "MD44": "ECOP (Environmental Code of Practice)",
        "MD45": "Product video",
        "MD46": "360° view",
        "MD47": "Thumbnail of product picture (MD01)",
        "MD48": "Pictogram/Icon",
        "MD49": "Declaration RoHS",
        "MD50": "Declaration CoC (Certificate of Conformity, requested for CPR)",
        "MD51": "Declaration DOP (Declaration of Performance)",
        "MD52": "Declaration DOC CE (Declaration of Conformity CE)",
        "MD53": "Declaration BREEAM (Building Research Establishment Environmental Assessment Method)",
        "MD54": "Declaration EPD (Environmental Product Declaration)",
        "MD55": "Declaration ETA (European Technical Assessment)",
        "MD56": "Declaration warranty (Warranty statement)",
        "MD57": "Application video",
        "MD58": "Question and Answer (Q&A video)",
        "MD59": "Product picture – square format",
        "MD60": "Exploded view drawing",
        "MD61": "Flowchart",
        "MD62": "Product presentation",
        "MD63": "Specification text",
        "MD64": "Line drawing",
        "MD65": "Product family view",
        "MD99": "Others"
    }




    user_defined_extensions = data.get("USER_DEFINED_EXTENSIONS", {})
    if user_defined_extensions:
        mime_info = user_defined_extensions.get("UDX.EDXF.MIME_INFO", {})
        if mime_info:
            mime_data = mime_info.get("UDX.EDXF.MIME", [])
            if isinstance(mime_data, dict):
                mime_entries.append(mime_data)
            elif isinstance(mime_data, list):
                mime_entries.extend(mime_data)
    
    # Extract from MIME_INFO (fallback)
    logger.debug("Searching for MIME_INFO in the main structure.")
    mime_info = data.get("MIME_INFO", {})
    if mime_info:
        mime_data = mime_info.get("MIME", [])    
        if isinstance(mime_data, dict):
            mime_entries.append(mime_data)
        elif isinstance(mime_data, list):
            mime_entries.extend(mime_data)
    

    # Process MIME attributes
    for entry in mime_entries:
        if isinstance(entry, dict):
            mime_code = entry.get("MIME_CODE") or entry.get("UDX.EDXF.MIME_CODE")
            if not mime_code:
                logger.debug(f"MIME_CODE nenalezem, hledám v MIME_DESCR ")
                mime_code = entry.get("MIME_DESCR")
            if mime_code:
                if mime_code not in valid_mime_codes:
                    logger.debug(f"Neplatný MIME_CODE: {mime_code}")
                else:
                    entry["MIME_CODE_NAME"] = valid_mime_codes[mime_code]
            
            mime_source = entry.get("UDX.EDXF.MIME_SOURCE")
            if isinstance(mime_source, list) and len(mime_source) == 2 and mime_source[0] == mime_source[1]:
                entry["UDX.EDXF.MIME_SOURCE"] = mime_source[0]
            
            for key, value in list(entry.items()):
                if isinstance(value, dict) and '@lang' in value:
                    entry[f"{key} @lang:{value['@lang']}"] = value['#text']
                    del entry[key]
    
    return mime_entries


# Parse Product Details
def parse_BME_product(product_data, logger):
    # Sanitize new-line in value
    def sanitize_value(value):
        if isinstance(value, str):
            return value.replace('\n', ' ').replace('\r', ' ').strip()
        return value
        
    product_entry  = {}
    product_details = product_data.get("PRODUCT_DETAILS", {})
    product_logistic_details = product_data.get("PRODUCT_LOGISTIC_DETAILS", {})
    
    # Parse Product Logistic Details
    if product_logistic_details:
        custom_tariff_number = product_logistic_details.get("CUSTOMS_TARIFF_NUMBER", {})
        country_of_origin = product_logistic_details.get("COUNTRY_OF_ORIGIN", {})
        if custom_tariff_number:
            custom_number = custom_tariff_number.get("CUSTOMS_NUMBER", {})
            if custom_number:
                product_entry["CUSTOMS_TARIFF_NUMBER"] = custom_number
        if country_of_origin:
            product_entry["COUNTRY_OF_ORIGIN"] = country_of_origin
    
    for tag, value in product_details.items():
        if isinstance(value, list):  # Convert lists to comma-separated strings
            value = ", ".join(map(str, value))
        product_entry[tag] = sanitize_value(value)

    return [product_entry]

# Parse Keywords
def parse_BME_keyword(product_data, logger):
    supplier_pid = next((product_data[key] for key in product_data if key.startswith("SUPPLIER_PID")), "N/A")
    product_details = product_data.get("PRODUCT_DETAILS", {})

    return [{"SUPPLIER_PID": supplier_pid, "keyword_tag": tag, "keyword_value": value}
            for tag, value in product_details.items() if tag.startswith("KEYWORD") and value]


# UDX 
def strip_udx_prefix(s: str) -> str:
    if isinstance(s, str) and s.startswith("UDX.EDXF."):
        return s.split("UDX.EDXF.", 1)[1]
    return s



def normalize_lang_nodes(d: dict):
    # gleiche Logik wie bei MIME: {'@lang': 'de', '#text': '...'} -> 'key @lang:de': '...'
    for key, value in list(d.items()):
        if isinstance(value, dict) and '@lang' in value and '#text' in value:
            d[f"{key} @lang:{value['@lang']}"] = value['#text']
            del d[key]

def flatten_udx_dict(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        nk = strip_udx_prefix(k)
        if isinstance(v, dict) and '#text' in v:
            out[nk] = v.get('#text')
            if '@lang' in v:
                out[f"{nk} @lang:{v.get('@lang')}"] = v.get('#text')
        elif isinstance(v, (str, int, float, bool)) or v is None:
            out[nk] = v
        else:
            # nested dict/list: bei Bedarf raw behalten oder ignorieren
            out[nk] = v
    normalize_lang_nodes(out)
    return out

def parse_udx_packing_and_logistics(data, logger):
    packing_units = []
    udx_logistics = {}

    user_defined_extensions = data.get("USER_DEFINED_EXTENSIONS", {})
    if user_defined_extensions:
        # PACKING_UNITS
        pu_container = user_defined_extensions.get("UDX.EDXF.PACKING_UNITS", {})
        if isinstance(pu_container, dict):
            pu = pu_container.get("UDX.EDXF.PACKING_UNIT", [])
            if isinstance(pu, dict):
                packing_units.append(flatten_udx_dict(pu))
            elif isinstance(pu, list):
                for item in pu:
                    if isinstance(item, dict):
                        packing_units.append(flatten_udx_dict(item))

        # PRODUCT_LOGISTIC_DETAILS
        pld = user_defined_extensions.get("UDX.EDXF.PRODUCT_LOGISTIC_DETAILS", {})
        if isinstance(pld, dict) and pld:
            udx_logistics = flatten_udx_dict(pld)

    return packing_units, udx_logistics
