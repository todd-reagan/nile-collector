"""
Lambda function for retrieving Nile events from DynamoDB.
"""

import json
import os
import boto3
from datetime import datetime, timedelta
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver # Changed for API Gateway v2
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2 # Changed for API Gateway v2

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('EVENTS_TABLE', 'NileEvents'))

# Initialize utilities
logger = Logger()
tracer = Tracer()
app = APIGatewayHttpResolver() # Changed for API Gateway v2

@app.get("/events")
@tracer.capture_method
def get_events():
    """
    Retrieve events from DynamoDB with optional filtering.
    
    Query parameters:
    - limit: Maximum number of events to return (default: 50)
    - start_time: Start timestamp for filtering (default: 24 hours ago)
    - end_time: End timestamp for filtering (default: now)
    - event_type: Filter by event type
    """
    try:
        # Validate Cognito authentication (HTTP API with JWT Authorizer)
        authorizer = app.current_event.request_context.authorizer
        jwt_claims = None

        if authorizer:
            # Based on logs, API Gateway might be putting claims directly under authorizer.jwt_claim (singular)
            if hasattr(authorizer, 'jwt_claim') and isinstance(authorizer.jwt_claim, dict) and authorizer.jwt_claim:
                logger.info("Found JWT claims via 'authorizer.jwt_claim' (get_events).")
                jwt_claims = authorizer.jwt_claim
            # Fallback to the standard Powertools model structure if jwt_claim is not found/valid
            elif hasattr(authorizer, 'jwt') and authorizer.jwt and hasattr(authorizer.jwt, 'claims') and isinstance(authorizer.jwt.claims, dict) and authorizer.jwt.claims:
                logger.info("Found JWT claims via 'authorizer.jwt.claims' (get_events).")
                jwt_claims = authorizer.jwt.claims
            else:
                logger.warning({
                    "message": "Could not find JWT claims (get_events). Neither 'authorizer.jwt_claim' nor 'authorizer.jwt.claims' yielded a valid claims dictionary.",
                    "authorizer_object_details_str": str(authorizer),
                    "authorizer_has_jwt_claim": hasattr(authorizer, 'jwt_claim'),
                    "authorizer_jwt_claim_is_dict": isinstance(getattr(authorizer, 'jwt_claim', None), dict),
                    "authorizer_has_jwt": hasattr(authorizer, 'jwt'),
                    "authorizer_jwt_has_claims": hasattr(getattr(authorizer, 'jwt', None), 'claims') if getattr(authorizer, 'jwt', None) else False,
                    "authorizer_jwt_claims_is_dict": isinstance(getattr(getattr(authorizer, 'jwt', None), 'claims', None), dict) if getattr(authorizer, 'jwt', None) else False
                })
        else: 
            logger.warning("Authorizer object ('request_context.authorizer') is missing or None (get_events).")
        
        if not jwt_claims: 
            logger.error("Authentication error: Cognito JWT claims not found.") 
            return {"message": "Authentication error: Authorization context missing or invalid."}, 401

        user_id = jwt_claims.get('sub') # 'sub' is the standard claim for user ID
        if not user_id:
            logger.error("Authentication error: 'sub' claim (user ID) not found in Cognito JWT.")
            return {"message": "Authentication error: User identifier not found in token."}, 401
        
        logger.info(f"Authenticated user: {user_id}") # Log the user for audit/debug

        # Get query parameters
        # For APIGatewayProxyEventV2, query string parameters are directly available
        query_params_dict = app.current_event.query_string_parameters or {}

        limit = int(query_params_dict.get("limit", "50"))
        
        # Default to last 24 hours if not specified
        now = int(datetime.utcnow().timestamp())
        yesterday = int((datetime.utcnow() - timedelta(days=1)).timestamp())
        
        start_time = int(query_params_dict.get("start_time", str(yesterday)))
        end_time = int(query_params_dict.get("end_time", str(now)))
        event_type_filter = query_params_dict.get("event_type", None) # Renamed to avoid conflict
        
        # Build query parameters for the base table (PK=user_id, SK=timestamp)
        expression_attribute_names = {
            '#uid': 'user_id',    # Partition Key
            '#ts': 'timestamp'    # Sort Key
        }
        expression_attribute_values = {
            ':uid_val': user_id,
            ':start_time_val': start_time,
            ':end_time_val': end_time
        }
        
        key_condition_expression = '#uid = :uid_val AND #ts BETWEEN :start_time_val AND :end_time_val'

        query_params_for_db = {
            # IndexName is removed, querying base table
            'KeyConditionExpression': key_condition_expression,
            'ExpressionAttributeNames': expression_attribute_names,
            'ExpressionAttributeValues': expression_attribute_values,
            'Limit': limit,
            'ScanIndexForward': False  # Sort by timestamp descending (most recent first)
        }
        
        # Add filter for event_type if provided
        if event_type_filter:
            # 'event_type' is not part of the primary key, so it's a FilterExpression
            query_params_for_db['FilterExpression'] = 'event_type = :type_val'
            query_params_for_db['ExpressionAttributeValues'][':type_val'] = event_type_filter
        
        # Query DynamoDB base table
        logger.info(f"Performing DynamoDB Query on base table (PK=user_id, SK=timestamp) with params: {query_params_for_db}")
        response = table.query(**query_params_for_db)
        
        # Process results
        events = []
        for item in response.get('Items', []):
            # Parse the event_data JSON string back to an object
            if 'event_data' in item:
                try:
                    item['event_data'] = json.loads(item['event_data'])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse event_data for item {item.get('id')}")
            
            events.append(item)
        
        # Return results
        return {
            "events": events,
            "count": len(events),
            "scanned_count": response.get('ScannedCount', 0),
            "last_evaluated_key": response.get('LastEvaluatedKey')
        }, 200
        
    except Exception as e:
        logger.exception("Error retrieving events")
        return {"message": str(e)}, 500

@app.get("/events/{event_id}")
@tracer.capture_method
def get_event(event_id):
    """
    Retrieve a specific event by its 'id' (UUID attribute), for the authenticated user.
    Table PK is user_id, SK is timestamp. 'id' is a regular attribute.
    """
    try:
        # Validate Cognito authentication
        authorizer = app.current_event.request_context.authorizer
        jwt_claims = None
        if authorizer: 
            if hasattr(authorizer, 'jwt_claim') and isinstance(authorizer.jwt_claim, dict) and authorizer.jwt_claim:
                jwt_claims = authorizer.jwt_claim
            elif hasattr(authorizer, 'jwt') and authorizer.jwt and hasattr(authorizer.jwt, 'claims') and isinstance(authorizer.jwt.claims, dict) and authorizer.jwt.claims:
                jwt_claims = authorizer.jwt.claims
        
        if not jwt_claims:
            logger.error("Authentication error: Cognito JWT claims not found for get_event.")
            return {"message": "Authentication error: Authorization context missing or invalid."}, 401

        authenticated_user_id = jwt_claims.get('sub')
        if not authenticated_user_id:
            logger.error("Authentication error: 'sub' claim (user ID) not found for get_event.")
            return {"message": "Authentication error: User identifier not found in token."}, 401
        
        logger.info(f"User {authenticated_user_id} requesting details for event with id_attribute: {event_id}")

        # Query the user's events and filter by the 'id' attribute.
        # This is less efficient than GetItem if 'id' were PK, but avoids a GSI on 'id'.
        # We expect event_id (UUID) to be unique globally, so Limit=1 is appropriate after filtering.
        # A full query for the user might return many items before filtering.
        # To optimize, if a client could provide a narrow time window, that would help.
        # For now, querying all and filtering.
        
        response = table.query(
            KeyConditionExpression='user_id = :uid',
            FilterExpression='#id_attr = :eid_val',
            ExpressionAttributeNames={
                '#uid': 'user_id',
                '#id_attr': 'id' 
            },
            ExpressionAttributeValues={
                ':uid_val': authenticated_user_id,
                ':eid_val': event_id 
            },
            Limit=1 # Since id should be unique, we only need one match.
        )
        
        items = response.get('Items', [])
        if not items:
            logger.warning(f"Event with id_attribute {event_id} not found for user {authenticated_user_id}.")
            return {"message": "Event not found"}, 404
        
        item = items[0]
        # Ownership is confirmed as the query was scoped by authenticated_user_id.

        if 'event_data' in item:
            try:
                item['event_data'] = json.loads(item['event_data'])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse event_data for item {item.get('id')}")
        
        return item, 200
        
    except Exception as e:
        logger.exception(f"Error retrieving event {event_id}")
        return {"message": str(e)}, 500

@logger.inject_lambda_context()
@tracer.capture_lambda_handler
def lambda_handler(event: APIGatewayProxyEventV2, context: LambdaContext): # Updated event type
    """
    Lambda handler for API Gateway HTTP API events.
    """
    logger.info({"message": "Received event for get_events", "path": event.get("rawPath", "N/A")})
    return app.resolve(event, context)
