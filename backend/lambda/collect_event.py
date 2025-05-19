"""
Lambda function for collecting and processing Splunk HEC events.
"""

import json
import uuid
import time
import os
import boto3
import hmac
import base64 # For decoding base64 encoded body from API Gateway
from typing import Optional # Added for type hinting
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser # Renamed to avoid conflict if user has a local 'parser' module
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2

# Import schema validation functions and definitions
# Changed from relative to direct import for Lambda compatibility
from schema import SCHEMA, validate_schema, get_summary

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE', 'NileEvents'))
config_table = dynamodb.Table(os.environ.get('CONFIG_TABLE', 'NileConfig')) # Initialized for use

# Initialize utilities
logger = Logger()
tracer = Tracer()
app = APIGatewayHttpResolver()

# Global configurations like ALLOW_ANYTHING and SUMMARY_MODE will now be sourced
# from the user's specific configuration retrieved via their HEC token,
# rather than Lambda environment variables.

# verify_splunk_hec_token now queries DynamoDB directly using the received token
# and does not rely on a global HEC token or SPLUNK_GLOBAL_CONFIG_KEY.

def verify_splunk_hec_token(event_headers):
    """
    Verify Splunk HEC token from Authorization header by looking it up in NileConfigTable GSI.
    Expected format: "Splunk <token>"
    Returns a tuple: (is_valid, message, user_config_item)
    user_config_item is the item from NileConfigTable if token is valid, else None.
    """
    auth_header = event_headers.get('Authorization', event_headers.get('authorization', ''))
    if not auth_header.startswith("Splunk "):
        logger.warning(f"Invalid auth scheme for Splunk HEC. Expected 'Splunk '. Got: {auth_header[:20]}")
        return False, "Invalid authorization scheme. Expected 'Splunk <token>'.", None

    # Extract the part after "Splunk "
    token_value_from_header = auth_header.split(' ', 1)[1]
    
    # Defensively check if this extracted part itself starts with "Splunk " (due to client double-prefixing)
    final_token_to_check = token_value_from_header
    if token_value_from_header.lower().startswith("splunk "):
        parts = token_value_from_header.split(" ", 1)
        if len(parts) > 1:
            final_token_to_check = parts[1]
            logger.info("Detected and stripped an additional 'Splunk ' prefix from the token value part of the Authorization header.")
        else: # Header was "Splunk Splunk " with no actual token after the second Splunk
            final_token_to_check = "" 

    if not final_token_to_check:
        logger.warning("Received effectively empty Splunk HEC token after processing Authorization header.")
        return False, "Empty HEC token received after processing.", None

    try:
        query_response = config_table.query(
            IndexName='SplunkHecTokenIndex', # GSI on splunk_hec_token
            KeyConditionExpression='splunk_hec_token = :token_val',
            ExpressionAttributeValues={':token_val': final_token_to_check}, # Use the cleaned token
            Limit=1 # HEC tokens should be unique, so expect 0 or 1 item
        )
        
        items = query_response.get('Items')
        if items and len(items) > 0:
            user_config_item = items[0]
            # Log the raw token that was successfully found for clarity
            logger.info(f"Valid HEC token received (raw: '{final_token_to_check}'), maps to user_id: {user_config_item.get('user_id')}")
            return True, "Authentication successful.", user_config_item
        else:
            # Log the raw token that was attempted
            logger.warning(f"Received Splunk HEC token (raw attempt: '{final_token_to_check}') not found in any user configuration.")
            return False, "Invalid HEC token (not found in configuration).", None
            
    except Exception as e:
        # Log the raw token that was attempted
        logger.exception(f"Error querying SplunkHecTokenIndex for HEC token validation (raw attempt: '{final_token_to_check}').")
        return False, "Error during HEC token validation.", None


def parse_event_payload(request_body_str: str, content_type: Optional[str]) -> list:
    """
    Parse the incoming request body, supporting JSON, NDJSON, and specific HEC structures.
    """
    events_to_process = []
    raw_events_data = [] # This will hold dicts that are HEC event structures

    if content_type and 'application/json' in content_type.lower():
        try:
            payload = json.loads(request_body_str)
            if isinstance(payload, list): # A list of HEC event objects
                raw_events_data.extend(payload)
            elif isinstance(payload, dict): # A single HEC event object or a wrapper
                # Check for Splunk HEC wrapper like {"event": ..., "fields": ..., "time": ...}
                # Or it could be a list of events under a key like {"events": [...]}
                if 'event' in payload and ('time' in payload or 'sourcetype' in payload): # Looks like a single HEC event
                    raw_events_data.append(payload)
                elif 'events' in payload and isinstance(payload['events'], list): # A wrapper with an "events" key
                     raw_events_data.extend(payload['events'])
                else: # Assume it's a single event object if not a known wrapper
                    raw_events_data.append(payload)
            else:
                logger.warning(f"Unexpected payload type after JSON parsing: {type(payload)}")
                # Potentially treat as a single event if it's a simple type, or error out
                # For now, if it's not list/dict, we won't process further from here.
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON payload: {e}. Will attempt NDJSON parsing.")
            # Fall through to NDJSON parsing
    
    # Attempt NDJSON parsing if not successfully parsed as a single JSON blob or if content_type suggests it
    if not raw_events_data or (content_type and 'application/x-ndjson' in content_type.lower()):
        if not raw_events_data: # Only log if we haven't already parsed something
             logger.info("Attempting to parse payload as newline-delimited JSON (NDJSON).")
        for line in request_body_str.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Similar logic as above for single HEC event or wrapper
                if isinstance(obj, dict):
                    if 'event' in obj and ('time' in obj or 'sourcetype' in obj):
                         raw_events_data.append(obj)
                    elif 'events' in obj and isinstance(obj['events'], list):
                         raw_events_data.extend(obj['events'])
                    else:
                         raw_events_data.append(obj)
                elif isinstance(obj, list): # A line itself could be an array of events
                    raw_events_data.extend(obj)
                else:
                    logger.warning(f"Skipping non-dict/list object in NDJSON line: {type(obj)}")
            except json.JSONDecodeError:
                logger.warning(f"Skipping invalid JSON line in NDJSON: {line[:100]}")
                continue
    
    # Extract the actual 'event' data from each HEC structure
    for hec_event_obj in raw_events_data:
        if isinstance(hec_event_obj, dict):
            # The 'event' field contains the actual data to be processed/validated
            # Other fields like 'time', 'sourcetype', 'host', 'index', 'fields' are metadata for HEC
            actual_event_data = hec_event_obj.get('event', hec_event_obj)
            
            # Carry over HEC metadata to the event data itself if not already present,
            # as schema validation might expect them or they are useful.
            if isinstance(actual_event_data, dict):
                for meta_key in ['time', 'sourcetype', 'host', 'index']:
                    if meta_key in hec_event_obj and meta_key not in actual_event_data:
                        actual_event_data[meta_key] = hec_event_obj[meta_key]
                if 'fields' in hec_event_obj and isinstance(hec_event_obj['fields'], dict):
                    for field_key, field_val in hec_event_obj['fields'].items():
                        if field_key not in actual_event_data: # Don't overwrite existing event data
                            actual_event_data[field_key] = field_val
            
            events_to_process.append(actual_event_data)
        else:
            # If it's not a dict, it's likely a raw event (e.g. string) sent to HEC.
            # Our schema validation expects dicts, so we might wrap it or log a warning.
            logger.info(f"Received non-dict event from HEC structure: {type(hec_event_obj)}. Storing as is.")
            events_to_process.append(hec_event_obj)
            
    return events_to_process


@app.post("/services/collector/event")
@tracer.capture_method
def receive_splunk_events():
    # verify_splunk_hec_token now returns (is_valid, message, user_config_item)
    is_valid_token, auth_message, user_config = verify_splunk_hec_token(app.current_event.headers)
    
    if not is_valid_token:
        # auth_message already contains details from verify_splunk_hec_token
        return {"text": auth_message, "code": 2}, 401 # Code 2: Token is required/invalid

    # If token is valid, user_config contains the DynamoDB item for the user owning this HEC token.
    # If token is valid, user_config contains the DynamoDB item for the user owning this HEC token.
    # Use allow_anything and summary_mode from this user's specific configuration.
    # Default to False if not found in their config (should always be there due to manage_config.py defaults).
    user_allow_anything = False
    user_summary_mode = False

    if user_config:
        logger.info(f"Processing HEC event for user_id: {user_config.get('user_id')}, HEC token: {user_config.get('splunk_hec_token')}")
        user_allow_anything = user_config.get('allow_anything', False)
        user_summary_mode = user_config.get('summary_mode', False)
        logger.info(f"User-specific settings: allow_anything={user_allow_anything}, summary_mode={user_summary_mode}")
    else:
        # This case should ideally not happen if token was valid, as user_config should be populated.
        # If it does, it's an internal error or unexpected state.
        logger.error("User config not found after successful HEC token validation. This is unexpected.")
        # Fallback to restrictive defaults or error out. For now, restrictive defaults.
        # However, verify_splunk_hec_token should not return (True, ..., None)
        # Let's assume user_config is always present if is_valid_token is True.
        pass # Handled by is_valid_token check already.

    request_body_str = app.current_event.body
    
    if app.current_event.is_base64_encoded:
        logger.info("Request body is base64 encoded. Decoding...")
        try:
            request_body_str = base64.b64decode(request_body_str).decode('utf-8')
        except Exception as e:
            logger.exception("Failed to decode base64 request body.")
            return {"text": "Invalid base64 encoded payload.", "code": 6}, 400 # Code 6: Invalid data format

    if not request_body_str:
        logger.warning("Received empty or undecodable request body for Splunk event.")
        return {"text": "No data", "code": 5}, 400 # Code 5: No data

    content_type = app.current_event.headers.get('content-type', app.current_event.headers.get('Content-Type'))
    logger.info(f"Processing HEC event with Content-Type: {content_type}")
    
    parsed_events = parse_event_payload(request_body_str, content_type)

    if not parsed_events:
        logger.info("No processable events found in the payload after parsing.")
        return {"text": "Success (No processable events)", "code": 0}, 200

    processed_db_items = []
    failed_events_info = [] # To track events that fail validation
    current_ingest_time_iso = datetime.now(timezone.utc).isoformat()
    ingestion_epoch = int(time.time())

    for idx, event_content in enumerate(parsed_events, 1):
        if not isinstance(event_content, dict):
            logger.warning(f"Event {idx} is not a dictionary, skipping validation/remapping: {str(event_content)[:100]}")
            # Store as-is if it's not a dict, or decide on an error strategy
            db_timestamp = ingestion_epoch
            event_type_for_db = "raw_non_json_event"
        else:
            # Apply transformations and validation if it's a dictionary
            event_type_from_content = event_content.get('eventType', event_content.get('sourcetype', 'unknown'))

            # Perform type-specific field remapping BEFORE schema validation
            if event_type_from_content == 'end_user_device_events':
                logger.debug(f"Attempting to remap fields for end_user_device_events. Original event_content: {event_content}")
                # Check for original fields before popping
                if 'clientMac' in event_content:
                    event_content['macAddress'] = event_content.pop('clientMac')
                if 'clientEventTimestamp' in event_content:
                    # The schema expects 'clientEventTime'. We'll use this for timestamp parsing later.
                    event_content['clientEventTime'] = event_content.pop('clientEventTimestamp')
                if 'clientEventAdditionalDetails' in event_content: # Assuming this is a generic details field
                    event_content['additionalDetails'] = event_content.pop('clientEventAdditionalDetails')
                
                # Use .get for fields that might not be present in all source variants, defaulting to empty or a specific value
                event_content['ssid'] = event_content.pop('connectedSsid', event_content.get('ssid', '')) 
                event_content['bssid'] = event_content.pop('connectedBssid', event_content.get('bssid', ''))
                
                # Map clientEventSeverity to clientEventStatus if clientEventStatus is not already present
                # The schema requires clientEventStatus.
                if 'clientEventStatus' not in event_content and 'clientEventSeverity' in event_content:
                    event_content['clientEventStatus'] = event_content.get('clientEventSeverity')
                    logger.info(f"Mapped clientEventSeverity ('{event_content.get('clientEventSeverity')}') to clientEventStatus.")
                
                # clientEventDescription is also required by schema. Ensure it's handled or present.
                # clientEventSuppressionStatus is not in schema, can be kept if desired or removed.
                # event_content.pop('clientEventSuppressionStatus', None) 

                logger.info(f"Remapped fields for end_user_device_events. New event_content: {event_content}")

            # Log event_content immediately before schema validation
            logger.debug({"message": "Event content before schema validation", "event_type": event_type_from_content, "content": json.dumps(event_content)})

            if not user_allow_anything: # Use user-specific setting for allow_anything
                is_valid_schema, missing_or_error_fields = validate_schema(event_content, event_type_from_content)
                if not is_valid_schema:
                    msg = f"Event {idx} failed schema validation for type '{event_type_from_content}'. Reason/Missing fields: {missing_or_error_fields}. Event (from validation failure log): {str(event_content)[:200]}"
                    logger.warning(msg)
                    failed_events_info.append({"reason": msg, "event_snippet": str(event_content)[:100]})
                    continue 
                else:
                    logger.info(f"Event {idx} passed schema validation for type '{event_type_from_content}'.")
                
                # UUID validation for 'id' field if present in the event content itself
                if 'id' in event_content:
                    try:
                        uuid.UUID(str(event_content['id']))
                    except ValueError:
                        msg = f"Event {idx} has invalid UUID in 'id' field: {event_content['id']}. Event: {str(event_content)[:200]}"
                        logger.warning(msg)
                        failed_events_info.append({"reason": msg, "event_snippet": str(event_content)[:100]})
                        continue # Skip this event
            
            # Timestamp parsing and conversion
            db_timestamp = ingestion_epoch # Default to ingestion time
            
            # Determine the correct timestamp field based on event_type, after remapping
            # This prioritizes schema-defined fields, then generic 'time'.
            ts_key_to_try = None
            if event_type_from_content == 'audit_trail':
                ts_key_to_try = 'auditTime'
            elif event_type_from_content == 'nile_alerts':
                ts_key_to_try = 'alertTime'
            elif event_type_from_content == 'end_user_device_events':
                ts_key_to_try = 'clientEventTime' # This was remapped from clientEventTimestamp
            
            if ts_key_to_try and ts_key_to_try in event_content:
                timestamp_source_key = ts_key_to_try
            elif 'time' in event_content: # Fallback to generic HEC 'time' field
                timestamp_source_key = 'time'
            else:
                timestamp_source_key = None # No specific or generic time field found

            if timestamp_source_key:
                ts_val = event_content[timestamp_source_key]
                try:
                    if isinstance(ts_val, (int, float)): # Already epoch or close enough
                        db_timestamp = int(float(ts_val))
                    elif isinstance(ts_val, str):
                        if ts_val.isdigit(): # String representation of epoch
                            db_timestamp = int(ts_val)
                        else: # Parse date string
                            # dateutil_parser is generally good. For HEC, 'time' can be float epoch.
                            # If it's a HEC 'time' field, it might be float seconds.microseconds.
                            if timestamp_source_key == 'time' and '.' in ts_val:
                                try:
                                    db_timestamp = int(float(ts_val)) # Attempt direct float conversion for epoch.micro
                                except ValueError:
                                    dt_obj = dateutil_parser.parse(ts_val)
                                    db_timestamp = int(dt_obj.timestamp())
                            else:
                                dt_obj = dateutil_parser.parse(ts_val)
                                db_timestamp = int(dt_obj.timestamp())
                    # HEC 'time' field can have millisecond/microsecond precision as float.
                    # DynamoDB Number type can store this. We convert to int for consistency with original code.
                    # If ms precision is needed, store as float or string.
                except Exception as e:
                    logger.warning(f"Event {idx} timestamp parsing error for key '{timestamp_source_key}' value '{ts_val}': {e}. Using ingestion time.")
            
            event_type_for_db = event_type_from_content

        # Logging (using get_summary from schema.py if user_summary_mode)
        if user_summary_mode: # Use user-specific setting
            if isinstance(event_content, dict):
                log_output = get_summary(event_content, event_type_for_db)
                logger.info(f"Summary Event [{idx}] (Type: {event_type_for_db}): {json.dumps(log_output)}")
            else: # Non-dict event
                 logger.info(f"Summary Event [{idx}] (Type: {event_type_for_db}): {str(event_content)[:100]}")
        else:
            logger.debug(f"Detailed Event [{idx}] (Type: {event_type_for_db}): {json.dumps(event_content)}")

        # Prepare item for DynamoDB with new PK/SK structure:
        # PK: user_id, SK: timestamp
        # 'id' (UUID) is now a regular attribute.
        
        event_uuid = str(uuid.uuid4()) # Generate the unique event ID (still useful)

        item_to_save = {
            'user_id': None,           # Placeholder for PK, will be set from user_config
            'timestamp': db_timestamp, # This is the SK
            'id': event_uuid,          # Store the original UUID as an attribute
            'event_type': event_type_for_db,
            'event_data': json.dumps(event_content),
            'created_at': current_ingest_time_iso
        }
        
        if user_config and 'user_id' in user_config:
            item_to_save['user_id'] = user_config['user_id'] # Set the PK
        else:
            logger.error(f"Event {idx} (UUID: {event_uuid}) processed with valid HEC token but no user_id found in user_config. This is unexpected. Event cannot be stored without a user_id PK.")
            failed_events_info.append({
                "reason": "Missing user_id for primary key after HEC token validation.",
                "event_uuid": event_uuid,
                "event_snippet": str(event_content)[:100]
            })
            continue # Skip this event as it's missing the PK

        processed_db_items.append(item_to_save)

    if processed_db_items:
        with events_table.batch_writer() as batch:
            for item in processed_db_items:
                batch.put_item(Item=item)
        logger.info(f"Successfully processed and stored {len(processed_db_items)} events.")
    
    if failed_events_info:
        logger.warning(f"{len(failed_events_info)} events failed processing due to validation errors.")
        # Depending on requirements, could return a 207 Multi-Status or include errors in response.
        # For HEC, a general success/failure for the batch is common.
        # Returning success for processed items, but logging failures.
        return {"text": "Success with some errors", "code": 0, "details": f"{len(processed_db_items)} stored, {len(failed_events_info)} failed validation.", "errors": failed_events_info[:10]}, 200 # Or 207

    return {"text": "Success", "code": 0}, 200


@app.get("/services/collector/health")
@tracer.capture_method
def health_check():
    # Health check also uses the same token validation.
    # It doesn't need user_config details beyond validity.
    is_valid, message, _ = verify_splunk_hec_token(app.current_event.headers)
    if not is_valid:
        return {"text": f"Unauthorized: {message}", "code": 3}, 401 # Code 3: Invalid token
    return {"text": "HEC is healthy", "code": 0}, 200


@logger.inject_lambda_context()
@tracer.capture_lambda_handler
def lambda_handler(event: APIGatewayProxyEventV2, context: LambdaContext): # Type hint remains for dev, but 'event' is dict here
    # Log key parts of the incoming event (which is a dict at this point)
    # The conversion to APIGatewayProxyEventV2 happens within app.resolve() for app.current_event
    
    # Safely access potentially nested dictionary keys
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    
    log_event_summary = {
        "message": "Received Splunk HEC event via HTTP API (raw handler event)",
        "rawPath": event.get("rawPath"),
        "httpMethod": http_context.get("method"),
        "headers": event.get("headers", {}),
        "isBase64Encoded": event.get("isBase64Encoded", False),
        "queryStringParameters": event.get("queryStringParameters"),
        "body_type": str(type(event.get("body"))),
        "body_length": len(event.get("body", "")) if event.get("body") else 0,
        "body_snippet": (event.get("body") or "")[:200]
    }
    logger.info(log_event_summary)
    
    try:
        return app.resolve(event, context)
    except Exception as e:
        # Catch-all for errors not handled by app.resolve (e.g., during app init or middleware)
        logger.exception("Unhandled exception in lambda_handler")
        return {"text": f"Internal server error: {str(e)}", "code": 8}, 500
