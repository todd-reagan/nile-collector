"""
Nile SIEM schema definitions for event validation.
"""

# Nile SIEM schema definitions
# Required fields for validation
SCHEMA = {
    'audit_trail': [
        'version', 'id', 'auditTime', 'user', 'sourceIP', 'agent', 
        'auditDescription', 'entity', 'action', 'result'
    ],
    'end_user_device_events': [
        'eventType', 'macAddress', 'ssid', 'bssid', 'clientEventDescription', 
        'clientEventTime', 'clientEventStatus'
    ],
    'nile_alerts': [
        'version', 'id', 'alertSubscriptionCategory', 'alertType', 'alertStatus', 
        'alertSubject', 'alertDescription', 'alertTime', 'alertSeverity'
    ],
    'test': [ # Added schema for eventType 'test' based on observed event
        'test-message', 
        'eventType', 
        'time', 
        'sourcetype'
    ]
}

# Complete schema definitions based on observed events
COMPLETE_SCHEMA = {
    'audit_trail': {
        'required': [
            'version', 'id', 'auditTime', 'user', 'sourceIP', 'agent', 
            'auditDescription', 'entity', 'action', 'result'
        ],
        'optional': [
            'additionalDetails',  # Contains nested JSON with detailed information
            'eventType'           # Identifies the event type
        ],
        'example': {
            "version": "1.0",
            "id": "076096cf-93d8-41c7-92a1-0d7d0a4bda84",
            "auditTime": "2025-04-09T04:53:59+00:00",
            "user": "cl.hit.test@gmail.com",
            "sourceIP": "14.99.4.110",
            "agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Safari/537.36",
            "auditDescription": "Created SSID 'PIPELINE_SSID_BUILDING_PSK'",
            "entity": "SSID",
            "action": "Create",
            "additionalDetails": {
                "newValue": {
                    "name": "PIPELINE_SSID_BUILDING_PSK",
                    "ssid": {
                        "security": "WPA2 Personal",
                        "segmentNames": [
                            "PL_SEGMENT-BUILDING-WO-RADIUS-CLHIT"
                        ]
                    },
                    "tags": [
                        "all"
                    ]
                }
            },
            "eventType": "audit_trail"
        }
    },
    'end_user_device_events': {
        'required': [
            'eventType', 'macAddress', 'ssid', 'bssid', 'clientEventDescription', 
            'clientEventTime', 'clientEventStatus'
        ],
        'optional': [
            'version', 'id',
            'connectedPort', 'connectedSwitch', 'clientUsername', 
            'clientLastKnownIpAddress', 'additionalDetails'
        ],
        'field_mapping': {
            'clientMac': 'macAddress',
            'clientEventTimestamp': 'clientEventTime',
            'clientEventAdditionalDetails': 'additionalDetails',
            'connectedSsid': 'ssid',
            'connectedBssid': 'bssid'
        },
        'example': {
            "version": "1.0",
            "id": "8e2fc3b9-dbad-46f2-9a69-3fea72a7108d",
            "clientMac": "58:47:ca:73:cb:e6",
            "clientEventSeverity": "INFO",
            "clientEventTimestamp": "2025-04-30T09:33:52+00:00",
            "clientEventDescription": "DHCP Renew Request Success",
            "connectedSsid": "",
            "connectedBssid": "",
            "connectedPort": "0/11",
            "connectedSwitch": "0b:15:10:20:05:49",
            "clientUsername": "CLHIT_MINIS1",
            "clientLastKnownIpAddress": "10.151.82.63",
            "clientEventAdditionalDetails": {
                "server_ip": "10.132.14.2",
                "sourceSerialNum": "E00A00064648",
                "ip_address": "10.151.82.63"
            },
            "eventType": "end_user_device_events"
        }
    },
    'nile_alerts': {
        'required': [
            'version', 'id', 'alertSubscriptionCategory', 'alertType', 'alertStatus', 
            'alertSubject', 'alertDescription', 'alertTime', 'alertSeverity'
        ],
        'optional': [
            'alertSummary', 'impact', 'customer', 'startTime', 'duration',
            'site', 'building', 'floor', 'additionalInformation', 'eventType'
        ],
        'field_mapping': {
            'startTime': 'alertTime',  # startTime in example maps to alertTime in schema
            'alertSummary': 'alertDescription'  # alertSummary might serve as alertDescription
        },
        'example': {
            "version": "1.0",
            "id": "ee0452ca-fd53-4034-a3cf-eb0a13287567",
            "alertSubscriptionCategory": "Security Alerts",
            "alertType": "Security",
            "alertStatus": "Resolved",
            "alertSubject": "Nile Alert Resolved [Security]",
            "alertSummary": "Impersonation Attack: Honeypot AP (BSSID : 26:15:10:21:13:dc) spoofing a valid Nile AP SSID PIPELINE_SSID_BUILDING_PSK has been detected in the air.",
            "impact": "This AP is not authorized to advertise network WiFi service with the same SSID as Nile Service. User devices may accidentally connect to the impersonating AP that is attempting a man-in-the-middle intrusion. This is a security issue.",
            "customer": "BLR_R2I_HW-CL-HIT-HW",
            "startTime": "2025-04-09T05:06:11+00:00",
            "duration": "12 minutes",
            "site": "BLR-R2I-HW-CL-HIT-S2",
            "building": "BLR-R2I-HW-CL-HIT-S2-B1",
            "floor": "CLHIT-TESTHW-S2-B1-F1",
            "additionalInformation": "https://docs.nilesecure.com/nile-security-alerts",
            "eventType": "nile_alerts"
        }
    },
    'test': {
        'required': [
            'test-message', 
            'eventType', 
            'time', 
            'sourcetype'
        ],
        'optional': []
    }
}

def validate_schema(event, event_type, use_complete_schema=False):
    """
    Validate an event against the schema for its event type.
    
    Args:
        event (dict): The event to validate
        event_type (str): The type of event (audit_trail, end_user_device_events, nile_alerts)
        use_complete_schema (bool): Whether to use the complete schema for validation
        
    Returns:
        tuple: (is_valid, missing_fields)
    """
    if use_complete_schema:
        if event_type not in COMPLETE_SCHEMA:
            return False, ["Unknown event type"]
        
        # Check required fields from complete schema
        required_fields = COMPLETE_SCHEMA[event_type]['required']
        missing_fields = [f for f in required_fields if f not in event]
        
        # If field mapping exists, check for original field names too
        if 'field_mapping' in COMPLETE_SCHEMA[event_type]:
            field_mapping = COMPLETE_SCHEMA[event_type]['field_mapping']
            for orig_field, mapped_field in field_mapping.items():
                # If the mapped field is missing but the original field exists, it's not actually missing
                if mapped_field in missing_fields and orig_field in event:
                    missing_fields.remove(mapped_field)
        
        return len(missing_fields) == 0, missing_fields
    else:
        # Use original minimal schema validation
        if event_type not in SCHEMA:
            return False, ["Unknown event type"]
        
        missing_fields = [f for f in SCHEMA[event_type] if f not in event]
        
        return len(missing_fields) == 0, missing_fields

def get_summary(event, event_type, detailed=False):
    """
    Create a summary of the event based on its type.
    
    Args:
        event (dict): The event to summarize
        event_type (str): The type of event
        detailed (bool): Whether to include more details in the summary
        
    Returns:
        dict: A summary of the event with key fields
    """
    summary = {}
    
    if event_type == 'audit_trail':
        # Basic summary
        summary = {
            'id': event.get('id'),
            'user': event.get('user'),
            'action': event.get('action'),
            'description': event.get('auditDescription')
        }
        
        # Add more details if requested
        if detailed:
            summary.update({
                'time': event.get('auditTime'),
                'sourceIP': event.get('sourceIP'),
                'entity': event.get('entity')
            })
            
            # Include a simplified version of additionalDetails if available
            if 'additionalDetails' in event and isinstance(event['additionalDetails'], dict):
                if 'newValue' in event['additionalDetails']:
                    summary['changes'] = event['additionalDetails'].get('newValue')
    
    elif event_type == 'nile_alerts':
        # Basic summary
        summary = {
            'id': event.get('id'),
            'type': event.get('alertType'),
            'subject': event.get('alertSubject'),
            'severity': event.get('alertSeverity')
        }
        
        # Add more details if requested
        if detailed:
            # Use alertSummary if available, otherwise use alertDescription
            summary['description'] = event.get('alertSummary', event.get('alertDescription', ''))
            
            # Include additional contextual information
            summary.update({
                'status': event.get('alertStatus'),
                'time': event.get('startTime', event.get('alertTime')),
                'duration': event.get('duration'),
                'impact': event.get('impact'),
                'location': {
                    'site': event.get('site'),
                    'building': event.get('building'),
                    'floor': event.get('floor')
                }
            })
    
    elif event_type == 'end_user_device_events':
        # Check for field mappings and use the appropriate field names
        mac_address = event.get('macAddress', event.get('clientMac', ''))
        event_time = event.get('clientEventTime', event.get('clientEventTimestamp', ''))
        event_status = event.get('clientEventStatus', event.get('clientEventSeverity', ''))
        
        # Basic summary
        summary = {
            'mac': mac_address,
            'desc': event.get('clientEventDescription'),
            'status': event_status
        }
        
        # Add more details if requested
        if detailed:
            summary.update({
                'time': event_time,
                'ssid': event.get('ssid', event.get('connectedSsid', '')),
                'bssid': event.get('bssid', event.get('connectedBssid', '')),
                'username': event.get('clientUsername', ''),
                'ip': event.get('clientLastKnownIpAddress', '')
            })
            
            # Include connection details if available
            if event.get('connectedPort') or event.get('connectedSwitch'):
                summary['connection'] = {
                    'port': event.get('connectedPort', ''),
                    'switch': event.get('connectedSwitch', '')
                }
            
            # Include additional details if available
            additional_details = event.get('additionalDetails', event.get('clientEventAdditionalDetails', {}))
            if additional_details and isinstance(additional_details, dict):
                summary['details'] = additional_details
    
    return summary
