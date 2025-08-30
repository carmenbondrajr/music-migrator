# 🔐 Google OAuth Setup Guide

This guide will help you set up Google OAuth credentials to bypass the "Access blocked" error.

## The "Access blocked" Error

When you see: **"Access blocked: music-migrator has not completed the Google verification process"**

This happens because your OAuth app is in development mode and hasn't been verified by Google. This is normal and expected for personal projects.

## Solution: OAuth Consent Screen Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "New Project" or select existing project
3. Give it a name like "Music Migrator"
4. Click "Create"

### Step 2: Enable YouTube Data API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "YouTube Data API v3"
3. Click on it and click "Enable"

### Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select **"External"** user type (unless you have Google Workspace)
3. Click "Create"

### Step 4: Fill Required Information

**App Information:**
- **App name:** `Music Migrator` (or whatever you prefer)
- **User support email:** Your email address
- **App logo:** (optional, can skip)

**App domain:** (optional, can leave blank)
- **Application home page:** (can leave blank)
- **Application privacy policy link:** (can leave blank)
- **Application terms of service link:** (can leave blank)

**Authorized domains:** (can leave blank for testing)

**Developer contact information:**
- **Email addresses:** Your email address

Click **"Save and Continue"**

### Step 5: Scopes (Skip This)

- Click **"Save and Continue"** (no scopes needed for this step)

### Step 6: Test Users (IMPORTANT!)

1. Click **"Add Users"**
2. Add your email address (the one you use for YouTube Music)
3. Click **"Add"**
4. Click **"Save and Continue"**

### Step 7: Summary

- Review your settings
- Click **"Back to Dashboard"**

## Step 8: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click **"Create Credentials"** → **"OAuth 2.0 Client IDs"**
3. **Application type:** Select **"TVs and Limited Input devices"** 
   - ⚠️ **Important:** Don't select "Web application"
4. **Name:** `Music Migrator Client`
5. Click **"Create"**
6. **Copy your Client ID and Client Secret** and save them

## Step 9: Handle "Access blocked" During OAuth

When you run `ytmusicapi oauth` and get the "Access blocked" message:

1. **Don't panic!** This is expected
2. Look for an **"Advanced"** link or similar
3. Click **"Advanced"**
4. Click **"Go to Music Migrator (unsafe)"** or similar
5. **This is safe** - it's your own app!

## Step 10: Complete OAuth Flow

1. Grant permissions when asked
2. You'll be redirected to a success page
3. `oauth.json` file will be created automatically

## Alternative: Internal App (Google Workspace Only)

If you have a Google Workspace account:
1. Select **"Internal"** instead of "External" in Step 3
2. This skips verification entirely
3. Only users in your organization can use the app

## Verification Status

Your app will show as "Testing" status, which allows:
- ✅ Up to 100 test users
- ✅ No expiration for test users  
- ✅ All necessary scopes for YouTube Music

You don't need to publish or verify the app for personal use!

## Common Issues

### "The developer hasn't given you access to this app"
- Make sure you added your email to "Test users"
- Use the same Google account for OAuth that you added as a test user

### "redirect_uri_mismatch" 
- Make sure you selected "TVs and Limited Input devices" not "Web application"

### "Client ID not found"
- Double-check you copied the Client ID correctly
- Make sure the OAuth client is in the same project where you enabled YouTube Data API

## Security Notes

- Your Client ID can be public (it's in the oauth.json file)
- Your Client Secret should be kept private
- The oauth.json file contains your personal access tokens
- This setup only gives YOU access to YOUR YouTube Music data

## Success!

Once complete, you'll have:
- ✅ A working `oauth.json` file
- ✅ Access to YouTube Music API for your personal account
- ✅ The ability to run the migration tool

Run `python main.py validate` to confirm everything is working!