# -*- coding: utf-8 -*-
#
# license: AGPLv3, see LICENSE for details. In addition we strongly encourage
#          you to buy us beer if we meet and you like the software.
"""Purchases module.

Since there are no hooks or anything everything is just in here.
"""
purchasedomain ={
        'purchases': 
            {
                'item_url': 'regex("[0-9]+")', 
                'description': 
                    {
                        'fields': 
                            {
                                'slot': 'Slot in the machine which was purchased(different items, which may have different prices).'
                            },
                        'general': 'A beer machine or kaffi machine transaction. Users should be able to get beer or kaffi, if their last timestamp is older than one day and they are AMIV members. This resource is used to log their purchases.'
                    },
                'item_lookup_field': '_id',
                'public_item_methods': [], 
                'registered_methods': [], 
                'owner_methods': ['GET'], 
                'datasource': 
                    {
                        'source': 'Purchase', 
                        'projection': 
                            {
                                'slot': 1, 
                                'user_id': 1, 
                                'timestamp': 1, 
                                '_author': 1, 
                                'type': 1, 
                                'id': 1
                            }
                    }, 
                'owner': ['user_id'], 
                'item_lookup': True, 
                'public_methods': [], 
                'schema': 
                    {
                    'slot': 
                        {
                            'required': False, 
                            'unique': False, 
                            'type': 'integer', 
                            'nullable': True
                        }, 
                    'user_id': 
                        {
                            'required': False, 
                            'unique': False, 
                            'type': 'integer', 
                            'nullable': True
                        }, 
                    'timestamp': 
                        {
                            'required': False, 
                            'unique': False, 
                            'type': 'datetime', 
                            'nullable': True
                        }, 
                    '_author': 
                        {
                            'readonly': True, 
                            'unique': False, 
                            'data_relation': 
                                {
                                    'resource': 'users', 
                                    'embeddable': False
                                }, 
                            'nullable': True, 
                            'required': False, 
                            'type': 'objectid'
                        }, 
                    'type': 
                        {
                            'required': False, 
                            'unique': False, 
                            'type': 'string', 
                            'maxlength': 5, 
                            'nullable': True
                        }
                    }
            }
    }

def init_app(app):
    """Register resources and blueprints, add hooks and validation."""
    register_domain(app, purchasedomain)
