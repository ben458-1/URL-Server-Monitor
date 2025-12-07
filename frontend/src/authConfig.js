// Microsoft Authentication Library (MSAL) Configuration
// Get Client ID and Tenant ID from Azure Portal > App Registrations

export const msalConfig = {
  auth: {
    clientId: "c36ab69c-4b1a-4824-b2d2-c52a6ac5853b", // Replace with your Azure App Client ID
    authority: "https://login.microsoftonline.com/facb74c5-4332-46a0-ba5f-ba96e47aa26e", // Replace with your Tenant ID
    redirectUri: window.location.origin, // Will be http://localhost:3000 in development
  },
  cache: {
    cacheLocation: "sessionStorage", // Store tokens in sessionStorage (expires when browser closes)
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return;
        console.log(message);
      }
    }
  }
};

// Scopes for backend API authentication
// TEMPORARY: Using User.Read until Azure AD API scope is configured
// TODO: Change to api://${clientId}/access_as_user once Azure AD is properly configured
export const loginRequest = {
  scopes: ["User.Read"],  // Temporary: Microsoft Graph token
  prompt: "select_account"  // Always show account picker, but won't ask password if already logged in
};

// Fallback scopes if the API scope is not configured in Azure AD
export const loginRequestFallback = {
  scopes: ["User.Read"]  // Fallback to Graph token
};

