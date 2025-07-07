import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const Register = () => {
  const [userData, setUserData] = useState({
    username: '',
    password: '',
    role: 'user',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = await register(userData);
    
    if (result.success) {
      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } else {
      setError(result.error);
    }
    
    setLoading(false);
  };

  const handleChange = (e) => {
    setUserData({
      ...userData,
      [e.target.name]: e.target.value,
    });
  };

  if (success) {
    return (
      <div className="auth-container">
        <div className="auth-form">
          <h2>Konto oprettet!</h2>
          <p>Din konto er blevet oprettet succesfuldt. Du omdirigeres til login siden...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-form">
        <h2>Opret konto</h2>
        <form onSubmit={handleSubmit}>
          {error && <div className="error-message">{error}</div>}
          
          <div className="form-group">
            <label htmlFor="username">Brugernavn:</label>
            <input
              type="text"
              id="username"
              name="username"
              value={userData.username}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Adgangskode:</label>
            <input
              type="password"
              id="password"
              name="password"
              value={userData.password}
              onChange={handleChange}
              required
              minLength={6}
            />
          </div>

          <div className="form-group">
            <label htmlFor="role">Rolle:</label>
            <select
              id="role"
              name="role"
              value={userData.role}
              onChange={handleChange}
            >
              <option value="user">Bruger</option>
              <option value="admin">Administrator</option>
            </select>
          </div>

          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Opretter...' : 'Opret konto'}
          </button>
        </form>

        <p className="auth-link">
          Har du allerede en konto? <Link to="/login">Log ind her</Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
