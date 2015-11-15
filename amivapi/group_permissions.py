# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.

"""
    Contains functions for group permissions
"""

def create_group_permissions_jsonschema(domain):
    """ 
    This is the authentification function called by eve. It will parse
    the send token and determine if it is from a valid user or a know
    apikey.
        
    You should not call this function directly. Use the functions in
    authorization.py instead(have a look at common_authorization()).
        
    :param domain: domain of the api, i.e. a list of endpoints (strings)
        
    :returns: A dictionary which is jsonschema
    """
    
    # Create outer container
    # Properties will be the enpoints
    # additionalProperties has to be false, otherwise all unknown properties
    # are accepted
    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Permission Matrix Schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {}
    }
    
    # Now add endpoints as allowed properties
    # This is the inner container, they are again objects
    for res in domain:
        schema["properties"][res] = {
            "title": "Permissions for '%s' resource" % res,
            "type": "object",
            "additionalProperties": False,
            "properties": {}
        }
        
        subschema = schema["properties"][res]["properties"]
        
        # All basic methods covered, just boolean
        for method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            subschema[method] = {
                "title": 'Permission for %s' % method,
                "type": "boolean"
        }
            
    return schema