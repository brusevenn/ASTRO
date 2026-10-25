import json

from filter.missing_zero_address_validation import *

Filter_json = {}

def set_protected(function):
    protected_dict = Filter_json.get(function.full_name, {})
    if function._is_protected:
        protected_dict["is_protected"] = function._is_protected
    else:
        protected_dict["is_protected"] = function.is_protected()
    Filter_json[function.full_name] = protected_dict
    
def set_missing_zero_check(contract):
    missing_zero_address_validation_case = MissingZeroAddressValidation()
    missing_zero_address_validation = missing_zero_address_validation_case._detect_missing_zero_address_validation(contract=contract)
    for (function, var_nodes) in missing_zero_address_validation:
        missing_zero_address_dict = Filter_json.get(function.full_name, {})
        missing_zero_address_dict["missing_zero_check"] = True
        Filter_json[function.full_name] = missing_zero_address_dict

def writer_filer_json(json_file):
    json.dump(Filter_json, json_file, indent=4)
    
    
