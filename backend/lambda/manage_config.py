"""
Lambda function for managing user configuration.
"""

import json
import os
import uuid
import boto3
from datetime import datetime
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver # Changed for API Gateway v2
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2 # Changed for API Gateway v2
from aws_lambda_powertools.utilities.parser import parse, BaseModel # Field not used directly here
from typing import Optional, List

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CONFIG_TABLE', 'NileConfig'))

# Initialize utilities
logger = Logger()
tracer = Tracer()
app = APIGatewayHttpResolver() # Changed for API Gateway v2

# Models for request validation
class EventTypeConfig(BaseModel):
    name: str
    required_fields: List[str]
    description: Optional[str] = None
    enabled: bool = True

class UpdateConfigRequest(BaseModel): # Renamed for clarity, only contains fields updatable via PUT /config
    allow_anything: bool
    summary_mode: bool
    # splunk_hec_token is no longer updated via this request; managed by its own endpoint.
    # token (User API Token) was removed.
    # event_types were removed.

@app.get("/config")
@tracer.capture_method
def get_config():
    """
    Retrieve the current configuration.
    """
    try:
        # Get user ID from Cognito (HTTP API with JWT Authorizer)
        authorizer = app.current_event.request_context.authorizer
        jwt_claims = None

        if authorizer:
            # Based on logs, API Gateway might be putting claims directly under authorizer.jwt_claim (singular)
            if hasattr(authorizer, 'jwt_claim') and isinstance(authorizer.jwt_claim, dict) and authorizer.jwt_claim:
                logger.info("Found JWT claims via 'authorizer.jwt_claim'.")
                jwt_claims = authorizer.jwt_claim
            # Fallback to the standard Powertools model structure if jwt_claim is not found/valid
            elif hasattr(authorizer, 'jwt') and authorizer.jwt and hasattr(authorizer.jwt, 'claims') and isinstance(authorizer.jwt.claims, dict) and authorizer.jwt.claims:
                logger.info("Found JWT claims via 'authorizer.jwt.claims'.")
                jwt_claims = authorizer.jwt.claims
            else:
                logger.warning({
                    "message": "Could not find JWT claims. Neither 'authorizer.jwt_claim' nor 'authorizer.jwt.claims' yielded a valid claims dictionary.",
                    "authorizer_object_details_str": str(authorizer), # Log string representation
                    "authorizer_has_jwt_claim": hasattr(authorizer, 'jwt_claim'),
                    "authorizer_jwt_claim_is_dict": isinstance(getattr(authorizer, 'jwt_claim', None), dict),
                    "authorizer_has_jwt": hasattr(authorizer, 'jwt'),
                    "authorizer_jwt_has_claims": hasattr(getattr(authorizer, 'jwt', None), 'claims') if getattr(authorizer, 'jwt', None) else False,
                    "authorizer_jwt_claims_is_dict": isinstance(getattr(getattr(authorizer, 'jwt', None), 'claims', None), dict) if getattr(authorizer, 'jwt', None) else False
                })
        else: 
            logger.warning("Authorizer object ('request_context.authorizer') is missing or None.")
        
        if not jwt_claims: 
            logger.error("Authentication error: Cognito JWT claims not found.") 
            return {"message": "Authentication error: Authorization context missing or invalid."}, 401

        user_id = jwt_claims.get('sub')
        if not user_id:
            logger.error("Authentication error: 'sub' claim (user ID) not found in Cognito JWT.")
            return {"message": "Authentication error: User identifier not found in token."}, 401
        
        logger.info(f"Authenticated user {user_id} requesting configuration.")
        
        # Get configuration from DynamoDB
        response = table.get_item(Key={'user_id': user_id})
        
        # Return configuration or default
        if 'Item' in response:
            # Ensure Splunk fields exist if loading an older config
            item = response['Item']
            # item.setdefault('splunk_hec_url', "") # No longer storing splunk_hec_url per user
            # Don't set empty string for splunk_hec_token as it's a GSI key
            item.pop('splunk_hec_url', None) # Remove if it exists from older versions
            # Remove old LM fields if they exist from a previous config
            item.pop('lm_access_id', None)
            item.pop('lm_access_key', None)
            return item, 200
        else:
            # Return default configuration for Splunk
            default_config = {
                'user_id': user_id,
                # 'token': str(uuid.uuid4()), # Removed User API Token
                # Don't include splunk_hec_token initially - it can't be an empty string in GSI
                'allow_anything': False,
                'summary_mode': False,
                # 'event_types': [], # Removed user-specific event type config
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Save default configuration
            table.put_item(Item=default_config)
            
            return default_config, 200
            
    except Exception as e:
        logger.exception("Error retrieving configuration")
        return {"message": str(e)}, 500

@app.put("/config")
@tracer.capture_method
def update_config():
    """
    Update the configuration.
    """
    try:
        # Get user ID from Cognito (HTTP API with JWT Authorizer)
        authorizer = app.current_event.request_context.authorizer
        jwt_claims = None

        if authorizer:
            if hasattr(authorizer, 'jwt_claim') and isinstance(authorizer.jwt_claim, dict) and authorizer.jwt_claim:
                logger.info("Found JWT claims via 'authorizer.jwt_claim' (update_config).")
                jwt_claims = authorizer.jwt_claim
            elif hasattr(authorizer, 'jwt') and authorizer.jwt and hasattr(authorizer.jwt, 'claims') and isinstance(authorizer.jwt.claims, dict) and authorizer.jwt.claims:
                logger.info("Found JWT claims via 'authorizer.jwt.claims' (update_config).")
                jwt_claims = authorizer.jwt.claims
            else:
                logger.warning({
                    "message": "Could not find JWT claims (update_config). Neither 'authorizer.jwt_claim' nor 'authorizer.jwt.claims' yielded valid claims.",
                    "authorizer_object_details_str": str(authorizer),
                    "authorizer_has_jwt_claim": hasattr(authorizer, 'jwt_claim'),
                    "authorizer_jwt_claim_is_dict": isinstance(getattr(authorizer, 'jwt_claim', None), dict),
                    "authorizer_has_jwt": hasattr(authorizer, 'jwt'),
                    "authorizer_jwt_has_claims": hasattr(getattr(authorizer, 'jwt', None), 'claims') if getattr(authorizer, 'jwt', None) else False,
                    "authorizer_jwt_claims_is_dict": isinstance(getattr(getattr(authorizer, 'jwt', None), 'claims', None), dict) if getattr(authorizer, 'jwt', None) else False
                })
        else:
            logger.warning("Authorizer object ('request_context.authorizer') is missing or None (update_config).")

        if not jwt_claims:
            logger.error("Authentication error: Cognito JWT claims not found for update.")
            return {"message": "Authentication error: Authorization context missing or invalid."}, 401

        user_id = jwt_claims.get('sub')
        if not user_id:
            logger.error("Authentication error: 'sub' claim (user ID) not found in Cognito JWT for update.")
            return {"message": "Authentication error: User identifier not found in token."}, 401
        
        logger.info(f"Authenticated user {user_id} updating configuration.")

        # Parse request body using Pydantic model
        # For APIGatewayHttpResolver, the body is directly in app.current_event.body (as a string)
        # The `parse` utility from Powertools should handle this.
        config_data: UpdateConfigRequest = parse(event=json.loads(app.current_event.body), model=UpdateConfigRequest)
        
        response = table.get_item(Key={'user_id': user_id})
        item_to_save = response.get('Item', {}) 

        # Ensure basic structure if item is new
        if not item_to_save:
            item_to_save['user_id'] = user_id
            item_to_save['created_at'] = datetime.utcnow().isoformat()
            # Don't initialize splunk_hec_token with empty string - it's a GSI key

        item_to_save['updated_at'] = datetime.utcnow().isoformat()

        # Update only allow_anything and summary_mode from this endpoint
        # Pydantic model UpdateConfigRequest ensures these fields are present.
        item_to_save['allow_anything'] = config_data.allow_anything
        item_to_save['summary_mode'] = config_data.summary_mode
            
        # Ensure other fields that are no longer managed by this PUT are popped or defaulted
        item_to_save.pop('token', None)
        item_to_save.pop('event_types', None) 
        item_to_save.pop('splunk_hec_url', None)
        item_to_save.pop('lm_access_id', None)
        item_to_save.pop('lm_access_key', None)

        # Remove splunk_hec_token if it's an empty string to avoid GSI validation errors
        if 'splunk_hec_token' in item_to_save and item_to_save['splunk_hec_token'] == "":
            item_to_save.pop('splunk_hec_token')
        
        logger.info(f"Saving updated configuration for user {user_id} (settings only): {item_to_save}")
        table.put_item(Item=item_to_save)
        
        return item_to_save, 200
        
    except Exception as e:
        logger.exception("Error updating configuration")
        return {"message": str(e)}, 500

# Regenerate token endpoint is being removed
# @app.post("/config/token/regenerate")
# @tracer.capture_method
# def regenerate_token():
#     """
#     Regenerate the authentication token.
#     """
#     # ... (logic removed) ...

@app.post("/config/splunk-hec-token/regenerate")
@tracer.capture_method
def regenerate_splunk_hec_token():
    """
    Generates a new unique Splunk HEC token for the authenticated user and saves it.
    Returns the new raw HEC token.
    """
    try:
        authorizer = app.current_event.request_context.authorizer
        jwt_claims = None
        if authorizer:
            if hasattr(authorizer, 'jwt_claim') and isinstance(authorizer.jwt_claim, dict) and authorizer.jwt_claim:
                jwt_claims = authorizer.jwt_claim
            elif hasattr(authorizer, 'jwt') and authorizer.jwt and hasattr(authorizer.jwt, 'claims') and isinstance(authorizer.jwt.claims, dict) and authorizer.jwt.claims:
                jwt_claims = authorizer.jwt.claims
        
        if not jwt_claims:
            logger.error("Authentication error: Cognito JWT claims not found for HEC token regeneration.")
            return {"message": "Authentication error: Authorization context missing or invalid."}, 401

        user_id = jwt_claims.get('sub')
        if not user_id:
            logger.error("Authentication error: 'sub' claim (user ID) not found for HEC token regeneration.")
            return {"message": "Authentication error: User identifier not found in token."}, 401

        logger.info(f"User {user_id} requesting new Splunk HEC token generation.")

        MAX_GENERATION_ATTEMPTS = 10
        new_raw_hec_token = ""
        is_unique = False

        for attempt in range(MAX_GENERATION_ATTEMPTS):
            generated_token_candidate = str(uuid.uuid4())
            try:
                query_response = table.query(
                    IndexName='SplunkHecTokenIndex',
                    KeyConditionExpression='splunk_hec_token = :token_val',
                    ExpressionAttributeValues={':token_val': generated_token_candidate},
                    Limit=1
                )
                if not query_response.get('Items'):
                    new_raw_hec_token = generated_token_candidate
                    is_unique = True
                    logger.info(f"Generated unique HEC token candidate for user {user_id} on attempt {attempt + 1}.")
                    break 
            except Exception as e:
                logger.exception(f"Error querying SplunkHecTokenIndex during HEC token generation attempt {attempt + 1} for user {user_id}.")
                # Depending on the error, might break or continue. For now, break on DB error.
                return {"message": "Error during HEC token generation uniqueness check."}, 500
        
        if not is_unique:
            logger.error(f"Failed to generate a unique HEC token for user {user_id} after {MAX_GENERATION_ATTEMPTS} attempts.")
            return {"message": "Failed to generate a unique HEC token. Please try again later."}, 500

        # Fetch current config item to update it
        response = table.get_item(Key={'user_id': user_id})
        item_to_update = response.get('Item', {})

        # Ensure basic structure if item is new (though user should exist if they can call this)
        if not item_to_update:
            item_to_update['user_id'] = user_id
            item_to_update['created_at'] = datetime.utcnow().isoformat()
            # Initialize other fields to defaults if creating a new record,
            # though this endpoint primarily focuses on the token.
            item_to_update.setdefault('allow_anything', False)
            item_to_update.setdefault('summary_mode', False)

        item_to_update['splunk_hec_token'] = new_raw_hec_token
        item_to_update['updated_at'] = datetime.utcnow().isoformat()
        
        # Clean up any old/removed fields
        item_to_update.pop('token', None)
        item_to_update.pop('event_types', None) 
        item_to_update.pop('splunk_hec_url', None)
        item_to_update.pop('lm_access_id', None)
        item_to_update.pop('lm_access_key', None)

        table.put_item(Item=item_to_update)
        logger.info(f"Successfully generated and saved new HEC token for user {user_id}.")
        
        # Return only the new raw HEC token
        return {"splunk_hec_token": new_raw_hec_token}, 200

    except Exception as e:
        logger.exception(f"Error regenerating Splunk HEC token for user {user_id if 'user_id' in locals() else 'unknown'}")
        return {"message": str(e)}, 500

@logger.inject_lambda_context()
@tracer.capture_lambda_handler
def lambda_handler(event: APIGatewayProxyEventV2, context: LambdaContext): # Updated event type
    """
    Lambda handler for API Gateway HTTP API events.
    """
    logger.info({"message": "Received event for manage_config", "path": event.get("rawPath", "N/A")})
    return app.resolve(event, context)
