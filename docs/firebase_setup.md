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

## Troubleshooting

- If Firebase initialization fails, check that the credentials file is in the correct location and formatted properly
- Ensure the service account has sufficient permissions in Firebase
- Check the application logs for detailed error messages

## Frontend Integration

For frontend applications, you'll need to use the Firebase JavaScript SDK. See the [Firebase documentation](https://firebase.google.com/docs/web/setup) for more details.
