"""
Nile SIEM schema definitions for event validation.
"""

# Nile SIEM schema definitions
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

def validate_schema(event, event_type):
    """
    Validate an event against the schema for its event type.
    
    Args:
        event (dict): The event to validate
        event_type (str): The type of event (audit_trail, end_user_device_events, nile_alerts)
        
    Returns:
        tuple: (is_valid, missing_fields)
    """
    if event_type not in SCHEMA:
        return False, ["Unknown event type"]
    
    missing_fields = [f for f in SCHEMA[event_type] if f not in event]
    
    return len(missing_fields) == 0, missing_fields

def get_summary(event, event_type):
    """
    Create a summary of the event based on its type.
    
    Args:
        event (dict): The event to summarize
        event_type (str): The type of event
        
    Returns:
        dict: A summary of the event with key fields
    """
    summary = {}
    
    if event_type == 'audit_trail':
        summary = {
            'id': event.get('id'),
            'user': event.get('user'),
            'action': event.get('action'),
            'description': event.get('auditDescription')
        }
    elif event_type == 'nile_alerts':
        summary = {
            'id': event.get('id'),
            'type': event.get('alertType'),
            'subject': event.get('alertSubject'),
            'severity': event.get('alertSeverity')
        }
    elif event_type == 'end_user_device_events':
        summary = {
            'mac': event.get('macAddress'),
            'desc': event.get('clientEventDescription'),
            'status': event.get('clientEventStatus')
        }
    
    return summary
