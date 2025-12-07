import React from 'react';
import { useMsal } from '@azure/msal-react';
import { loginRequest } from '../authConfig';
import '../styles/components/Login.css';

function Login() {
  const { instance } = useMsal();

  const handleLogin = async () => {
    try {
      console.log('🔐 User clicked login button - starting login flow...');
      // Using loginPopup which will automatically use SSO if user is already logged into Microsoft
      // No password prompt will appear if they're already authenticated with Microsoft
      await instance.loginPopup(loginRequest);
      console.log('✅ Login successful!');
    } catch (e) {
      console.error('❌ Login failed:', e);
      if (e.errorCode !== 'user_cancelled') {
        alert('Login failed: ' + (e.message || 'Unknown error'));
      }
    }
  };

  return (
    <div className="login-container">
      <div className="login-left">
        <img
          src="/EurolandLogo_Blue.webp"
          alt="EUROLAND IR"
          className="company-logo"
        />
        <h2 className="welcome-title">Welcome to Server Monitoring Tool</h2>
        <p className="login-subtitle">
          Securely login with your Microsoft account to continue.
        </p>
      </div>
      
      <div className="login-right">
        <div className="login-card">
          <h3 className="login-heading">Login</h3>
          <button className="microsoft-login-btn" onClick={handleLogin}>
            <svg className="microsoft-icon" width="21" height="21" viewBox="0 0 21 21" fill="none">
              <rect width="10" height="10" fill="#f25022"/>
              <rect x="11" width="10" height="10" fill="#7fba00"/>
              <rect y="11" width="10" height="10" fill="#00a4ef"/>
              <rect x="11" y="11" width="10" height="10" fill="#ffb900"/>
            </svg>
            Login with Microsoft
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;

