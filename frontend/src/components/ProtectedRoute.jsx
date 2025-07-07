import React from 'react';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Indlæser...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-required">
        <h2>Adgang krævet</h2>
        <p>Du skal være logget ind for at bruge chat systemet.</p>
        <div className="auth-links">
          <a href="/login" className="auth-button">Log ind</a>
          <a href="/register" className="auth-button secondary">Opret konto</a>
        </div>
      </div>
    );
  }

  return children;
};

export default ProtectedRoute;
