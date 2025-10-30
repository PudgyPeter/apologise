import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import DiscordDashboard from './components/DiscordDashboard';
import HospitalityStats from './components/HospitalityStats';
import './App.css';

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved === 'true';
  });

  // Persist dark mode preference
  useEffect(() => {
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  return (
    <Router>
      <Routes>
        {/* Discord Dashboard - Main route */}
        <Route 
          path="/" 
          element={<DiscordDashboard darkMode={darkMode} setDarkMode={setDarkMode} />} 
        />
        
        {/* Hospitality Stats - Separate route */}
        <Route 
          path="/hospitality" 
          element={<HospitalityStats darkMode={darkMode} setDarkMode={setDarkMode} />} 
        />
        
        {/* Redirect any unknown routes to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
