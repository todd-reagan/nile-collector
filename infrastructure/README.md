# Nile Collector Infrastructure

This directory contains the AWS SAM (Serverless Application Model) template and configuration files for deploying the Nile Collector application to AWS.

## Prerequisites

- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Python 3.9 or later
- Node.js 16 or later

## Deployment Instructions

### 1. Build and Package the Application

Before deploying, ensure you've installed all dependencies:

```bash
# From the project root
npm run install:all
```

**Important**: If you encounter a "No module named 'pydantic'" error or any other missing module error, make sure to reinstall the backend dependencies:

```bash
# From the project root
npm run install:backend
```

Then build the frontend:

```bash
# From the project root
npm run build:frontend
npm run export:frontend
```

### 2. Deploy the Backend Infrastructure

Before deploying, you need to create an S3 bucket for the deployment artifacts:

```bash
# Create the S3 bucket for deployment artifacts
aws s3 mb s3://nile-collector-deployment-artifacts --region us-west-2
```

Then you can deploy the application to different environments (dev, test, prod) using the following commands:

```bash
# Deploy to development environment
npm run deploy:dev

# Deploy to test environment
npm run deploy:test

# Deploy to production environment
npm run deploy:prod
```

These commands use the AWS SAM CLI to deploy the CloudFormation stack defined in `template.yaml`.

### 3. Upload the Frontend to S3

After the backend infrastructure is deployed, you need to upload the frontend to the S3 bucket created by the SAM template:

```bash
# Get the S3 bucket name from the CloudFormation stack outputs
aws cloudformation describe-stacks --stack-name nile-collector-dev --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" --output text

# Upload the frontend to the S3 bucket
aws s3 sync ../frontend/out/ s3://BUCKET_NAME_FROM_ABOVE/
```

### 4. Update Frontend Environment Variables

After deployment, you'll need to update the frontend environment variables with the actual values from your AWS deployment:

1. Get the API Gateway endpoint URL:
   ```bash
   aws cloudformation describe-stacks --stack-name nile-collector-dev --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text
   ```

2. Get the Cognito User Pool ID:
   ```bash
   aws cloudformation describe-stacks --stack-name nile-collector-dev --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text
   ```

3. Get the Cognito User Pool Client ID:
   ```bash
   aws cloudformation describe-stacks --stack-name nile-collector-dev --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" --output text
   ```

4. Get the CloudFront URL:
   ```bash
   aws cloudformation describe-stacks --stack-name nile-collector-dev --query "Stacks[0].Outputs[?OutputKey=='CloudFrontURL'].OutputValue" --output text
   ```

5. Create a `.env.production` file in the frontend directory with these values:
   ```
   NEXT_PUBLIC_API_URL=<ApiEndpoint>
   NEXT_PUBLIC_REGION=<AWS_REGION>
   NEXT_PUBLIC_USER_POOL_ID=<UserPoolId>
   NEXT_PUBLIC_USER_POOL_CLIENT_ID=<UserPoolClientId>
   ```
   
   **Important**: Make sure to use the full API URL (including https://) for NEXT_PUBLIC_API_URL. The frontend is configured for static export, which doesn't support API rewrites.

6. Rebuild and redeploy the frontend:
   ```bash
   npm run build:frontend
   npm run export:frontend
   aws s3 sync ../frontend/out/ s3://BUCKET_NAME_FROM_ABOVE/
   ```

7. Invalidate the CloudFront cache:
   ```bash
   # Get the CloudFront distribution ID
   aws cloudformation describe-stacks --stack-name nile-collector --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue" --output text
   
   # Invalidate the cache
   aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID_FROM_ABOVE --paths "/*"
   ```

## Customizing the Deployment

You can customize the deployment by modifying the following files:

- `template.yaml`: The AWS SAM template that defines all AWS resources
- `samconfig.toml`: Configuration for the AWS SAM CLI

### Environment-Specific Configuration

The `samconfig.toml` file contains environment-specific configuration for the AWS SAM CLI. You can modify this file to customize the deployment for different environments.

**Important**: The `samconfig.toml` file requires a `version` key at the top of the file. This has been added as `version = 0.1`. If you create a new SAM project, make sure to include this version key to avoid deployment errors.

## Troubleshooting

### Common Issues

1. **Deployment fails with "Unable to upload artifact" error**:
   - The CodeUri paths in template.yaml are set to `../backend/lambda/` which means you need to run the SAM CLI commands from the infrastructure directory, not the project root.
   - Make sure you're in the `/Users/treagan/Projects/nile-collector/infrastructure` directory when running SAM CLI commands.
   - If you see "S3 Bucket does not exist" error, make sure you've created the S3 bucket for deployment artifacts as mentioned in the deployment instructions: `aws s3 mb s3://nile-collector-deployment-artifacts --region us-west-2`

2. **Deployment fails with "Resource already exists" error**:
   - This usually happens when you try to deploy a stack with the same name. Use a different stack name or delete the existing stack.

2. **API Gateway returns 403 Forbidden**:
   - Check the Cognito User Pool and User Pool Client configuration in the AWS Console.
   - Ensure the API Gateway has the correct CORS configuration.

3. **Frontend can't connect to the API**:
   - Check the API Gateway endpoint URL in the frontend environment variables.
   - Ensure the API Gateway has the correct CORS configuration.

4. **NPM dependency issues during installation**:
   - The project uses the `--legacy-peer-deps` flag for npm install to handle dependency conflicts.
   - If you encounter dependency issues, try running `npm install --legacy-peer-deps` in the frontend directory.
   - Note that this flag is only for npm commands, not for Next.js commands like `next build`.
   - For specific component issues, check the compatibility between React 18 and the component libraries.

5. **Lambda function errors with "No module named 'pydantic'" or other missing modules**:
   - This happens when the Lambda function is missing required Python dependencies.
   - Make sure to run `npm run install:backend` to install all the required dependencies.
   - We've added pydantic to the requirements.txt file to fix this specific error.
   - If you encounter other missing module errors, add them to the requirements.txt file and reinstall the backend dependencies.

6. **NPM deprecated package warnings**:
   - You may see warnings about deprecated packages during installation. These are common in npm projects.
   - We've added package overrides in `frontend/package.json` to use newer versions of some packages.
   - These warnings don't affect the functionality of the application but are noted for future maintenance.
   - Key packages updated:
     - Updated `uuid` to v9.0.1 and added it to package overrides to ensure all dependencies use this version
     - Updated `eslint` to v8.56.0
     - Added overrides for `glob`, `rimraf`, and other deprecated packages

### Logs

You can view the logs for the Lambda functions using the AWS CloudWatch console or the AWS CLI:

```bash
# Get the function name from the CloudFormation stack outputs
aws cloudformation describe-stacks --stack-name nile-collector-dev --query "Stacks[0].Outputs[?OutputKey=='CollectEventFunctionName'].OutputValue" --output text

# View the logs
aws logs get-log-events --log-group-name /aws/lambda/FUNCTION_NAME_FROM_ABOVE --log-stream-name $(aws logs describe-log-streams --log-group-name /aws/lambda/FUNCTION_NAME_FROM_ABOVE --order-by LastEventTime --descending --limit 1 --query "logStreams[0].logStreamName" --output text)
