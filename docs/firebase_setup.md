# Firebase Authentication Setup

This document provides instructions for setting up Firebase Authentication with your Resume Builder application.

## Prerequisites

1. A Google account
2. Firebase project (free tier is sufficient)

## Step 1: Create a Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" and follow the setup wizard
3. Enter a name for your project
4. Decide whether to enable Google Analytics (recommended)
5. Click "Create project"

## Step 2: Enable Authentication Methods

1. In your Firebase project, navigate to "Authentication" in the left sidebar
2. Click "Get started"
3. Enable the authentication methods you want to use:
   - Email/Password (required)
   - Google (recommended)
   - Other providers as needed (Facebook, Twitter, GitHub, etc.)

## Step 3: Create a Firebase Web App

1. In your Firebase project, click the gear icon next to "Project Overview" and select "Project settings"
2. Scroll down to "Your apps" section and click the web icon (</>)
3. Register your app with a nickname (e.g., "Resume Builder Web")
4. Click "Register app"
5. Firebase will provide a configuration object for your app - save this for later use in your frontend client

## Step 4: Generate Service Account Credentials

1. In Firebase Project settings, go to the "Service accounts" tab
2. Click "Generate new private key" button
3. Save the JSON file securely - this contains sensitive information!

## Step 5: Configure the Application

### Option 1: Using Individual FIREBASE_ Environment Variables (Recommended)

1. Open your Firebase service account JSON file
2. Set each field as an environment variable with the FIREBASE_ prefix:

```bash
# Required Environment Variables
USE_FIREBASE_AUTH=true
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour-Private-Key-With-Newlines\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...
FIREBASE_UNIVERSE_DOMAIN=googleapis.com

# API configuration
API_BASE_URL=https://your-api-domain.com
EMAIL_VERIFICATION_PATH=/auth/verify-email
PASSWORD_RESET_PATH=/auth/reset-password
```

Benefits of this approach:
- Each field is a separate environment variable, making it easier to manage
- Works well with environment variable management in platforms like Digital Ocean
- The application will detect these variables and construct the credentials automatically

### Option 2: Using a Full JSON String (Alternative)

If you prefer to keep all credentials together:

```bash
# Required
USE_FIREBASE_AUTH=true
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project","private_key":"-----BEGIN PRIVATE KEY-----\nYour-Key-Here\n-----END PRIVATE KEY-----\n","client_email":"your-email@example.com",...}

# API configuration
API_BASE_URL=https://your-api-domain.com
EMAIL_VERIFICATION_PATH=/auth/verify-email
PASSWORD_RESET_PATH=/auth/reset-password
```

This approach has the benefit of keeping all credentials together but may be more challenging to handle in some environments due to the length and special characters.

### Option 3: Using a Credentials File (Development Only)

1. Rename the downloaded JSON file to `firebase_credentials.json`
2. Place it in the `config/` directory of your application
3. Ensure the file is added to `.gitignore` to avoid committing credentials to version control
4. Set the following environment variables in your `.env` file:
   ```
   USE_FIREBASE_AUTH=true
   FIREBASE_CREDENTIALS_PATH=./config/firebase_credentials.json
   API_BASE_URL=http://localhost:8000
   EMAIL_VERIFICATION_PATH=/auth/verify-email
   PASSWORD_RESET_PATH=/auth/reset-password
   ```
   Adjust the `API_BASE_URL` based on your environment (local, dev, production).

## Step 6: Test the Integration

1. Start your application
2. Check the logs to ensure Firebase is initialized successfully
3. Try registering a user and logging in with Firebase

## Security Considerations

- Never expose your Firebase credentials in client-side code
- Use environment variables or secure storage for credentials in production
- Implement proper security rules in Firebase to restrict database and storage access
- Regularly rotate service account keys
- For `FIREBASE_PRIVATE_KEY`, ensure all newlines are preserved (use literal newlines in environment variables)
- Restrict the permissions of your service account to only what's needed

## Troubleshooting

- If Firebase initialization fails, check that the credentials are correctly formatted
- When using environment variables, verify that the private key includes all necessary newlines
- For private key formatting issues in environment variables, try:
  ```
  FIREBASE_PRIVATE_KEY="$(cat path/to/private-key.pem)"
  ```
- Ensure the service account has sufficient permissions in Firebase
- Check the application logs for detailed error messages

## Frontend Integration

For frontend applications, you'll need to use the Firebase JavaScript SDK. See the [Firebase documentation](https://firebase.google.com/docs/web/setup) for more details.
