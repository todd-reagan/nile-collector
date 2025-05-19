# Nile Collector

A serverless HTTP event collector for AWS with Next.js frontend.

## Description

This project is a serverless implementation of the Nile Collector, designed to collect and process HTTP events using AWS services. It transforms the original script-based collector into a scalable, serverless architecture.

## Architecture

- **API Gateway**: Handles HTTP requests and routes them to Lambda functions
- **Lambda Functions**: Process and validate incoming events (Python)
- **DynamoDB**: Stores collected events
- **S3**: Hosts the Next.js frontend
- **Cognito**: Provides user authentication
- **Next.js**: Provides the frontend interface for configuration and monitoring

## Project Structure

```
nile-collector/
├── backend/             # Backend serverless components
│   └── lambda/          # Lambda function code
├── frontend/            # Next.js frontend application
│   ├── src/             # Frontend source code
│   └── public/          # Static assets
├── infrastructure/      # Infrastructure as Code (IaC) files
└── README.md            # This file
```

## Prerequisites

- Node.js (v16+)
- Python 3 (v3.8+)
- AWS CLI configured with appropriate permissions
- AWS SAM CLI

## Getting Started

1. Clone the repository
   ```bash
   git clone https://github.com/[your-username]/nile-collector.git
   cd nile-collector
   ```

2. Install backend dependencies
   ```bash
   cd backend
   pip3 install -r requirements.txt -t lambda/
   cd ..
   ```

3. Install frontend dependencies
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. Deploy to AWS
   ```bash
   # See detailed instructions in the infrastructure/README.md file
   cd infrastructure
   # Follow the deployment instructions in the README.md file
   cd ..
   ```

## Features

- Serverless architecture for unlimited scalability
- Event validation and schema enforcement
- Secure authentication with AWS Cognito
- User configuration through web interface
- Real-time event monitoring
- Compatible with the original Nile event schema

## API Authentication

The collector API requires authentication for event submission. To authenticate your requests:

1. Get your API token from the configuration page in the collector dashboard
2. Add the following header to your API requests:
   ```
   Authorization: Splunk YOUR_API_TOKEN
   ```
3. This token is required for all POST requests to the `/event` or `/events` endpoints

Example using curl:
```bash
curl -X POST https://your-api-endpoint.execute-api.region.amazonaws.com/dev/event \
  -H "Content-Type: application/json" \
  -H "Authorization: Splunk YOUR_API_TOKEN" \
  -d '{"eventType": "audit_trail", "id": "123e4567-e89b-12d3-a456-426614174000", ...}'
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
