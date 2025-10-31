import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  TrendingUp,
  Users,
  DollarSign,
  BarChart3,
  Edit2,
  X,
  Check,
  Trash2,
  Calendar,
  Menu,
  FileText,
  MessageSquare
} from 'lucide-react';
import { format } from 'date-fns';

function HospitalityStats({ darkMode, setDarkMode }) {
  const [hospitalityStats, setHospitalityStats] = useState([]);
  const [hospitalityAnalytics, setHospitalityAnalytics] = useState(null);
  const [mealPeriodFilter, setMealPeriodFilter] = useState('all');
  const [newStat, setNewStat] = useState({
    date: '',
    miv: '',
    average_spend: '',
    staff_member: '',
    meal_period: 'lunch'
  });
  const [editingIndex, setEditingIndex] = useState(null);
  const [editingStat, setEditingStat] = useState(null);
  const [messageInput, setMessageInput] = useState('');
  const [parsedData, setParsedData] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('manual');
  const [managerReports, setManagerReports] = useState([]);

  useEffect(() => {
    fetchHospitalityStats();
    fetchHospitalityAnalytics();
    
    // Load saved manager reports from localStorage
    const savedReports = localStorage.getItem('managerReports');
    if (savedReports) {
      try {
        setManagerReports(JSON.parse(savedReports));
      } catch (error) {
        console.error('Error loading manager reports:', error);
      }
    }
    
    // Update manifest for PWA to use hospitality-specific settings
    const manifestLink = document.querySelector('link[rel="manifest"]');
    if (manifestLink) {
      manifestLink.href = '/hospitality-manifest.json';
    }
    
    // Update page title and meta tags for hospitality section
    document.title = 'Hospitality Stats Tracker';
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription) {
      metaDescription.content = 'Track and analyze hospitality statistics';
    }
    
    // Cleanup: restore original manifest when component unmounts
    return () => {
      const manifestLink = document.querySelector('link[rel="manifest"]');
      if (manifestLink) {
        manifestLink.href = '/manifest.json';
      }
      document.title = 'Discord Log Dashboard';
    };
  }, []);

  const fetchHospitalityStats = async () => {
    try {
      const response = await axios.get('/api/hospitality/stats');
      setHospitalityStats(response.data);
      console.log('Hospitality stats loaded:', response.data.length, 'entries');
    } catch (error) {
      console.error('Error fetching hospitality stats:', error);
    }
  };

  const fetchHospitalityAnalytics = async () => {
    try {
      const response = await axios.get('/api/hospitality/analytics');
      setHospitalityAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching hospitality analytics:', error);
    }
  };

  const parseManagerMessage = (message) => {
    try {
      const lines = message.split('\n').map(line => line.trim()).filter(line => line);
      const data = {
        managers: [],
        predMiv: null,
        actualMiv: null,
        averageSpend: null,
        safe: null,
        till: null,
        cashExpected: null,
        cashActual: null,
        stationPlan: [],
        closingPlan: [],
        allStaff: new Set()
      };

      let currentSection = null;

      for (const line of lines) {
        // Manager names
        if (line.startsWith('Manager Name')) {
          const match = line.match(/Manager Name\(s\)?:\s*(.+)/i);
          if (match) {
            data.managers = match[1].split(/[,\s]+/).filter(n => n);
            data.managers.forEach(m => data.allStaff.add(m));
          }
        }
        // Pred MIV
        else if (line.startsWith('Pred MIV')) {
          const match = line.match(/Pred MIV:\s*(\d+)/i);
          if (match) data.predMiv = parseInt(match[1]);
        }
        // Actual MIV
        else if (line.startsWith('Actual MIV')) {
          const match = line.match(/Actual MIV:\s*(\d+)/i);
          if (match) data.actualMiv = parseInt(match[1]);
        }
        // Average Spend
        else if (line.startsWith('A$')) {
          const match = line.match(/A\$:\s*([\d.]+)/i);
          if (match) data.averageSpend = parseFloat(match[1]);
        }
        // Safe
        else if (line.startsWith('Safe:')) {
          const match = line.match(/Safe:\s*([\d.]+)/i);
          if (match) data.safe = parseFloat(match[1]);
        }
        // Till
        else if (line.startsWith('Till:')) {
          const match = line.match(/Till:\s*([\d.]+)/i);
          if (match) data.till = parseFloat(match[1]);
        }
        // Cash Expected
        else if (line.startsWith('Cash Expected')) {
          const match = line.match(/Cash Expected:\s*\$?([\d.]+)/i);
          if (match) data.cashExpected = parseFloat(match[1]);
        }
        // Cash Actual
        else if (line.startsWith('Cash Actual')) {
          const match = line.match(/Cash Actual:\s*\$?([\d.]+)/i);
          if (match) data.cashActual = parseFloat(match[1]);
        }
        // Section headers
        else if (line.startsWith('Station Plan')) {
          currentSection = 'station';
        }
        else if (line.startsWith('Closing Plan')) {
          currentSection = 'closing';
        }
        // Station/Role assignments
        else if (currentSection && line.includes(':')) {
          const [role, names] = line.split(':').map(s => s.trim());
          const staffNames = names.split(/[,\s]+/).filter(n => n);
          staffNames.forEach(name => data.allStaff.add(name));
          
          if (currentSection === 'station') {
            data.stationPlan.push({ role, staff: staffNames });
          } else if (currentSection === 'closing') {
            data.closingPlan.push({ role, staff: staffNames });
          }
        }
      }

      return data;
    } catch (error) {
      console.error('Error parsing message:', error);
      return null;
    }
  };

  const handleParseMessage = () => {
    const parsed = parseManagerMessage(messageInput);
    if (parsed) {
      setParsedData(parsed);
      // Save to manager reports with timestamp
      const reportWithDate = {
        ...parsed,
        date: new Date().toISOString(),
        rawMessage: messageInput
      };
      const updatedReports = [...managerReports, reportWithDate];
      setManagerReports(updatedReports);
      // Save to localStorage
      localStorage.setItem('managerReports', JSON.stringify(updatedReports));
      
      // Auto-fill the form with parsed data
      setNewStat({
        date: '',
        miv: parsed.actualMiv || '',
        average_spend: parsed.averageSpend || '',
        staff_member: parsed.managers.join(', ') || '',
        meal_period: 'dinner' // Manager reports are typically for dinner
      });
    } else {
      alert('Could not parse message. Please check the format.');
    }
  };

  const handleSubmitStat = async (e) => {
    e.preventDefault();
    
    if (!newStat.miv || !newStat.average_spend || !newStat.staff_member || !newStat.meal_period) {
      alert('Please fill in all fields');
      return;
    }
    
    try {
      await axios.post('/api/hospitality/stats', newStat);
      setNewStat({ date: '', miv: '', average_spend: '', staff_member: '', meal_period: 'lunch' });
      setMessageInput('');
      setParsedData(null);
      fetchHospitalityStats();
      fetchHospitalityAnalytics();
    } catch (error) {
      console.error('Error submitting stat:', error);
      alert('Error submitting stat: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleEditStat = (index) => {
    const stat = hospitalityStats[index];
    setEditingIndex(index);
    setEditingStat({
      ...stat,
      meal_period: stat.meal_period || 'lunch'
    });
  };

  const handleUpdateStat = async (e) => {
    e.preventDefault();
    
    if (!editingStat.miv || !editingStat.average_spend || !editingStat.staff_member || !editingStat.meal_period) {
      alert('Please fill in all required fields (MIV, Average Spend, Staff Member, Meal Period)');
      return;
    }
    
    try {
      console.log('Updating entry at index:', editingIndex);
      console.log('Update data:', editingStat);
      const response = await axios.put(`/api/hospitality/stats/${editingIndex}`, editingStat);
      console.log('Update response:', response.data);
      setEditingIndex(null);
      setEditingStat(null);
      fetchHospitalityStats();
      fetchHospitalityAnalytics();
    } catch (error) {
      console.error('Error updating stat:', error);
      console.error('Error response:', error.response?.data);
      alert('Error updating stat: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditingStat(null);
  };

  const handleDeleteStat = async (index) => {
    if (!window.confirm('Delete this entry?')) return;
    
    try {
      console.log('Deleting entry at index:', index);
      const response = await axios.delete(`/api/hospitality/stats/${index}`);
      console.log('Delete response:', response.data);
      fetchHospitalityStats();
      fetchHospitalityAnalytics();
    } catch (error) {
      console.error('Error deleting stat:', error);
      console.error('Error response:', error.response?.data);
      alert('Error deleting entry: ' + (error.response?.data?.error || error.message));
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString + 'T00:00:00');
      return format(date, 'dd/MM/yyyy');
    } catch {
      return dateString;
    }
  };

  const getFilteredAnalytics = () => {
    if (!hospitalityAnalytics || mealPeriodFilter === 'all') {
      return hospitalityAnalytics;
    }

    const filteredStats = hospitalityStats.filter(stat => stat.meal_period === mealPeriodFilter);
    
    if (filteredStats.length === 0) {
      return null;
    }

    const staffData = {};
    const dayData = {};
    let totalMiv = 0;
    let totalSpend = 0;

    filteredStats.forEach(entry => {
      const staff = entry.staff_member || 'Unknown';
      const miv = parseFloat(entry.miv || 0);
      const avgSpend = parseFloat(entry.average_spend || 0);

      if (!staffData[staff]) {
        staffData[staff] = { total_spend: 0, total_miv: 0, count: 0 };
      }
      staffData[staff].total_spend += avgSpend;
      staffData[staff].total_miv += miv;
      staffData[staff].count += 1;

      if (entry.date) {
        try {
          const date = new Date(entry.date + 'T00:00:00');
          const dayName = format(date, 'EEEE');
          if (!dayData[dayName]) {
            dayData[dayName] = { total_miv: 0, total_spend: 0, count: 0 };
          }
          dayData[dayName].total_miv += miv;
          dayData[dayName].total_spend += avgSpend;
          dayData[dayName].count += 1;
        } catch (e) {
          // Skip invalid dates
        }
      }

      totalMiv += miv;
      totalSpend += avgSpend;
    });

    const staffPerformance = Object.entries(staffData).map(([staff, data]) => ({
      staff_member: staff,
      avg_spend: (data.total_spend / data.count).toFixed(2),
      avg_miv: (data.total_miv / data.count).toFixed(2),
      total_entries: data.count
    })).sort((a, b) => parseFloat(b.avg_spend) - parseFloat(a.avg_spend));

    const dayOfWeekAvg = {};
    Object.entries(dayData).forEach(([day, data]) => {
      dayOfWeekAvg[day] = {
        avg_miv: (data.total_miv / data.count).toFixed(2),
        avg_spend: (data.total_spend / data.count).toFixed(2),
        count: data.count
      };
    });

    return {
      total_entries: filteredStats.length,
      staff_performance: staffPerformance,
      day_of_week_avg: dayOfWeekAvg,
      overall_avg_miv: (totalMiv / filteredStats.length).toFixed(2),
      overall_avg_spend: (totalSpend / filteredStats.length).toFixed(2)
    };
  };

  const handleMobileNav = (tab) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  // Calculate comprehensive analytics from manager reports
  const calculateManagerAnalytics = () => {
    if (managerReports.length === 0) return null;

    const now = new Date();
    const staffStats = {};
    const dailyStats = [];
    const weeklyStats = {};
    const monthlyStats = {};
    const yearlyStats = {};

    managerReports.forEach(report => {
      const reportDate = new Date(report.date);
      const dayKey = reportDate.toISOString().split('T')[0];
      const weekKey = `${reportDate.getFullYear()}-W${Math.ceil((reportDate.getDate()) / 7)}`;
      const monthKey = `${reportDate.getFullYear()}-${String(reportDate.getMonth() + 1).padStart(2, '0')}`;
      const yearKey = `${reportDate.getFullYear()}`;

      // Staff statistics
      Array.from(report.allStaff).forEach(staffName => {
        if (!staffStats[staffName]) {
          staffStats[staffName] = {
            name: staffName,
            totalShifts: 0,
            daysWorked: new Set(),
            totalMiv: 0,
            totalSpend: 0,
            roles: {},
            shiftsPerDay: {}
          };
        }
        
        staffStats[staffName].totalShifts++;
        staffStats[staffName].daysWorked.add(dayKey);
        staffStats[staffName].totalMiv += report.actualMiv || 0;
        staffStats[staffName].totalSpend += report.averageSpend || 0;

        // Track day of week
        const dayOfWeek = reportDate.toLocaleDateString('en-US', { weekday: 'long' });
        staffStats[staffName].shiftsPerDay[dayOfWeek] = (staffStats[staffName].shiftsPerDay[dayOfWeek] || 0) + 1;

        // Track roles
        [...report.stationPlan, ...report.closingPlan].forEach(station => {
          if (station.staff.includes(staffName)) {
            staffStats[staffName].roles[station.role] = (staffStats[staffName].roles[station.role] || 0) + 1;
          }
        });
      });

      // Daily stats
      dailyStats.push({
        date: dayKey,
        miv: report.actualMiv,
        predMiv: report.predMiv,
        avgSpend: report.averageSpend,
        managers: report.managers,
        staffCount: report.allStaff.size
      });

      // Weekly aggregation
      if (!weeklyStats[weekKey]) {
        weeklyStats[weekKey] = { totalMiv: 0, totalSpend: 0, count: 0, staffSet: new Set() };
      }
      weeklyStats[weekKey].totalMiv += report.actualMiv || 0;
      weeklyStats[weekKey].totalSpend += report.averageSpend || 0;
      weeklyStats[weekKey].count++;
      Array.from(report.allStaff).forEach(s => weeklyStats[weekKey].staffSet.add(s));

      // Monthly aggregation
      if (!monthlyStats[monthKey]) {
        monthlyStats[monthKey] = { totalMiv: 0, totalSpend: 0, count: 0, staffSet: new Set() };
      }
      monthlyStats[monthKey].totalMiv += report.actualMiv || 0;
      monthlyStats[monthKey].totalSpend += report.averageSpend || 0;
      monthlyStats[monthKey].count++;
      Array.from(report.allStaff).forEach(s => monthlyStats[monthKey].staffSet.add(s));

      // Yearly aggregation
      if (!yearlyStats[yearKey]) {
        yearlyStats[yearKey] = { totalMiv: 0, totalSpend: 0, count: 0, staffSet: new Set() };
      }
      yearlyStats[yearKey].totalMiv += report.actualMiv || 0;
      yearlyStats[yearKey].totalSpend += report.averageSpend || 0;
      yearlyStats[yearKey].count++;
      Array.from(report.allStaff).forEach(s => yearlyStats[yearKey].staffSet.add(s));
    });

    // Process staff stats
    const processedStaffStats = Object.values(staffStats).map(staff => ({
      ...staff,
      daysWorked: staff.daysWorked.size,
      avgMiv: (staff.totalMiv / staff.totalShifts).toFixed(2),
      avgSpend: (staff.totalSpend / staff.totalShifts).toFixed(2),
      mostFrequentDay: Object.entries(staff.shiftsPerDay).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A',
      topRole: Object.entries(staff.roles).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'
    })).sort((a, b) => b.totalShifts - a.totalShifts);

    // Calculate averages
    const calculateAvg = (stats) => {
      const entries = Object.entries(stats);
      if (entries.length === 0) return { avgMiv: 0, avgSpend: 0 };
      
      const totals = entries.reduce((acc, [key, val]) => ({
        miv: acc.miv + val.totalMiv,
        spend: acc.spend + val.totalSpend,
        count: acc.count + val.count
      }), { miv: 0, spend: 0, count: 0 });

      return {
        avgMiv: (totals.miv / totals.count).toFixed(2),
        avgSpend: (totals.spend / totals.count).toFixed(2)
      };
    };

    return {
      staffStats: processedStaffStats,
      dailyStats: dailyStats.sort((a, b) => new Date(b.date) - new Date(a.date)),
      weeklyAvg: calculateAvg(weeklyStats),
      monthlyAvg: calculateAvg(monthlyStats),
      yearlyAvg: calculateAvg(yearlyStats),
      totalReports: managerReports.length,
      uniqueStaff: Object.keys(staffStats).length
    };
  };

  return (
    <div className={`app ${darkMode ? 'dark-mode' : ''}`}>
      {/* Mobile Navigation Menu */}
      {mobileMenuOpen && (
        <div className="mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
          <div className="mobile-menu" onClick={(e) => e.stopPropagation()}>
            <div className="mobile-menu-header">
              <h2>Navigation</h2>
              <button onClick={() => setMobileMenuOpen(false)} className="mobile-menu-close">
                <X size={24} />
              </button>
            </div>
            <div className="mobile-menu-buttons">
              <button 
                className={`mobile-nav-btn ${activeTab === 'parser' ? 'active' : ''}`}
                onClick={() => handleMobileNav('parser')}
              >
                <MessageSquare size={32} />
                <span>Parse Report</span>
              </button>
              <button 
                className={`mobile-nav-btn ${activeTab === 'manual' ? 'active' : ''}`}
                onClick={() => handleMobileNav('manual')}
              >
                <FileText size={32} />
                <span>Manual Entry</span>
              </button>
              <button 
                className={`mobile-nav-btn ${activeTab === 'analytics' ? 'active' : ''}`}
                onClick={() => handleMobileNav('analytics')}
              >
                <BarChart3 size={32} />
                <span>Analytics</span>
              </button>
            </div>
          </div>
        </div>
      )}

      <header className="header">
        <div className="header-content">
          <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(true)}>
            <Menu size={24} />
          </button>
          <h1>📊 Hospitality Stats Dashboard</h1>
          <div className="header-actions">
            <span className="version-badge">v2.0.5</span>
            <button 
              className="dark-mode-toggle" 
              onClick={() => setDarkMode(!darkMode)}
              title={darkMode ? 'Light Mode' : 'Dark Mode'}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>

      <div className="container" style={{ gridTemplateColumns: '1fr', height: 'auto' }}>
        <main className="main-content">
          <div className="content-area hospitality-content">
            {/* Message Parser Section */}
            {activeTab === 'parser' && (
            <div className="hospitality-form-section">
              <h2>📋 Parse Manager Report</h2>
              <p style={{marginBottom: '16px', color: '#666'}}>Paste the daily manager message below to automatically extract stats</p>
              <div className="form-group">
                <label>Manager Report Message</label>
                <textarea
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  placeholder="Paste the manager report here..."
                  rows="12"
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #e0e0e0',
                    borderRadius: '8px',
                    fontSize: '14px',
                    fontFamily: 'monospace',
                    resize: 'vertical'
                  }}
                />
              </div>
              <button 
                type="button"
                onClick={handleParseMessage}
                className="submit-btn"
                disabled={!messageInput.trim()}
              >
                Parse Message
              </button>

              {parsedData && (
                <div style={{
                  marginTop: '20px',
                  padding: '16px',
                  background: '#f0f9ff',
                  border: '2px solid #0ea5e9',
                  borderRadius: '8px'
                }}>
                  <h3 style={{margin: '0 0 12px 0', color: '#0369a1'}}>✅ Parsed Data</h3>
                  <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '14px'}}>
                    <div><strong>Manager(s):</strong> {parsedData.managers.join(', ')}</div>
                    <div><strong>Pred MIV:</strong> {parsedData.predMiv}</div>
                    <div><strong>Actual MIV:</strong> {parsedData.actualMiv}</div>
                    <div><strong>Avg Spend:</strong> ${parsedData.averageSpend}</div>
                  </div>
                  <div style={{marginTop: '12px'}}>
                    <strong>Staff Working:</strong> {Array.from(parsedData.allStaff).join(', ')}
                  </div>
                  {parsedData.stationPlan.length > 0 && (
                    <div style={{marginTop: '12px'}}>
                      <strong>Station Plan:</strong>
                      <div style={{marginLeft: '12px', marginTop: '4px'}}>
                        {parsedData.stationPlan.map((station, idx) => (
                          <div key={idx}>{station.role}: {station.staff.join(', ')}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  {parsedData.closingPlan.length > 0 && (
                    <div style={{marginTop: '12px'}}>
                      <strong>Closing Plan:</strong>
                      <div style={{marginLeft: '12px', marginTop: '4px'}}>
                        {parsedData.closingPlan.map((station, idx) => (
                          <div key={idx}>{station.role}: {station.staff.join(', ')}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
            )}

            {/* Manual Entry Section */}
            {activeTab === 'manual' && (
            <div className="hospitality-form-section">
              <h2>Add Daily Stats</h2>
              <form onSubmit={handleSubmitStat} className="hospitality-form">
                <div className="form-group">
                  <label>Date (leave blank for today) - Will display as DD/MM/YYYY</label>
                  <input
                    type="date"
                    value={newStat.date}
                    onChange={(e) => setNewStat({...newStat, date: e.target.value})}
                    placeholder="YYYY-MM-DD"
                  />
                </div>
                <div className="form-group">
                  <label>Meal Period</label>
                  <select
                    value={newStat.meal_period}
                    onChange={(e) => setNewStat({...newStat, meal_period: e.target.value})}
                    required
                  >
                    <option value="lunch">Lunch</option>
                    <option value="dinner">Dinner</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>MIV (Main Item Value)</label>
                  <input
                    type="number"
                    value={newStat.miv}
                    onChange={(e) => setNewStat({...newStat, miv: e.target.value})}
                    placeholder="Number of burgers/salads sold"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Average Spend ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newStat.average_spend}
                    onChange={(e) => setNewStat({...newStat, average_spend: e.target.value})}
                    placeholder="Net sales ÷ MIV"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Staff Member</label>
                  <input
                    type="text"
                    value={newStat.staff_member}
                    onChange={(e) => setNewStat({...newStat, staff_member: e.target.value})}
                    placeholder="Who was tilling orders?"
                    required
                  />
                </div>
                <button type="submit" className="submit-btn">
                  <TrendingUp size={18} />
                  Add Entry
                </button>
              </form>

              {/* Manual Entry Analytics - shown below the form */}
              {hospitalityAnalytics && (
              <div className="analytics-section">
                <div className="analytics-header">
                  <h2>Analytics</h2>
                  <div className="meal-period-tabs">
                    <button 
                      className={mealPeriodFilter === 'all' ? 'active' : ''}
                      onClick={() => setMealPeriodFilter('all')}
                    >
                      All
                    </button>
                    <button 
                      className={mealPeriodFilter === 'lunch' ? 'active' : ''}
                      onClick={() => setMealPeriodFilter('lunch')}
                    >
                      Lunch
                    </button>
                    <button 
                      className={mealPeriodFilter === 'dinner' ? 'active' : ''}
                      onClick={() => setMealPeriodFilter('dinner')}
                    >
                      Dinner
                    </button>
                  </div>
                </div>
                
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-icon">
                      <BarChart3 size={24} />
                    </div>
                    <div className="stat-info">
                      <div className="stat-label">Total Entries</div>
                      <div className="stat-value">{getFilteredAnalytics()?.total_entries || 0}</div>
                    </div>
                  </div>
                  
                  <div className="stat-card">
                    <div className="stat-icon">
                      <TrendingUp size={24} />
                    </div>
                    <div className="stat-info">
                      <div className="stat-label">Overall Avg MIV</div>
                      <div className="stat-value">{getFilteredAnalytics()?.overall_avg_miv || 0}</div>
                    </div>
                  </div>
                  
                  <div className="stat-card">
                    <div className="stat-icon">
                      <DollarSign size={24} />
                    </div>
                    <div className="stat-info">
                      <div className="stat-label">Overall Avg Spend</div>
                      <div className="stat-value">${getFilteredAnalytics()?.overall_avg_spend || 0}</div>
                    </div>
                  </div>
                </div>

                <div className="analytics-tables">
                  <div className="analytics-table">
                    <h3><Users size={20} /> Staff Performance</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Staff Member</th>
                          <th>Avg Spend</th>
                          <th>Avg MIV</th>
                          <th>Entries</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(getFilteredAnalytics()?.staff_performance || []).map((staff, idx) => (
                          <tr key={idx}>
                            <td>{staff.staff_member}</td>
                            <td className="highlight">${staff.avg_spend}</td>
                            <td>{staff.avg_miv}</td>
                            <td>{staff.total_entries}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="analytics-table">
                    <h3><Calendar size={20} /> Day of Week Averages</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>Day</th>
                          <th>Avg MIV</th>
                          <th>Avg Spend</th>
                          <th>Entries</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(getFilteredAnalytics()?.day_of_week_avg || {}).map(([day, data]) => (
                          <tr key={day}>
                            <td>{day}</td>
                            <td>{data.avg_miv}</td>
                            <td className="highlight">${data.avg_spend}</td>
                            <td>{data.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="recent-entries">
                  <h3>Recent Entries</h3>
                  <div className="entries-list">
                    {hospitalityStats.slice().reverse().map((stat, idx) => {
                      const actualIndex = hospitalityStats.length - 1 - idx;
                      
                      return (
                        <div key={idx} className="entry-card">
                          <div className="entry-header">
                            <span className="entry-date">
                              {formatDate(stat.date)} - <span style={{textTransform: 'capitalize'}}>{stat.meal_period}</span>
                            </span>
                            <div className="entry-actions">
                              <button 
                                onClick={() => handleEditStat(actualIndex)}
                                className="edit-entry-btn"
                                title="Edit"
                              >
                                <Edit2 size={16} />
                              </button>
                              <button 
                                onClick={() => handleDeleteStat(actualIndex)}
                                className="delete-entry-btn"
                                title="Delete"
                              >
                                <Trash2 size={16} />
                              </button>
                            </div>
                          </div>
                          <div className="entry-details">
                            <div className="entry-detail">
                              <span className="label">MIV:</span>
                              <span className="value">{stat.miv}</span>
                            </div>
                            <div className="entry-detail">
                              <span className="label">Avg Spend:</span>
                              <span className="value">${stat.average_spend}</span>
                            </div>
                            <div className="entry-detail">
                              <span className="label">Staff:</span>
                              <span className="value">{stat.staff_member}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
              )}
            </div>
            )}

            {/* Manager Analytics Section */}
            {activeTab === 'analytics' && (() => {
              const managerAnalytics = calculateManagerAnalytics();
              
              if (!managerAnalytics) {
                return (
                  <div className="hospitality-form-section">
                    <h2>📊 Manager Report Analytics</h2>
                    <p style={{textAlign: 'center', padding: '40px', color: '#666'}}>
                      No manager reports parsed yet. Go to "Parse Report" to add data.
                    </p>
                  </div>
                );
              }

              return (
                <div className="hospitality-form-section">
                  <h2>📊 Manager Report Analytics</h2>
                  
                  {/* Summary Stats */}
                  <div className="stats-grid" style={{marginBottom: '24px'}}>
                    <div className="stat-card">
                      <div className="stat-icon"><FileText size={24} /></div>
                      <div className="stat-info">
                        <div className="stat-label">Total Reports</div>
                        <div className="stat-value">{managerAnalytics.totalReports}</div>
                      </div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-icon"><Users size={24} /></div>
                      <div className="stat-info">
                        <div className="stat-label">Unique Staff</div>
                        <div className="stat-value">{managerAnalytics.uniqueStaff}</div>
                      </div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-icon"><TrendingUp size={24} /></div>
                      <div className="stat-info">
                        <div className="stat-label">Weekly Avg MIV</div>
                        <div className="stat-value">{managerAnalytics.weeklyAvg.avgMiv}</div>
                      </div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-icon"><DollarSign size={24} /></div>
                      <div className="stat-info">
                        <div className="stat-label">Weekly Avg Spend</div>
                        <div className="stat-value">${managerAnalytics.weeklyAvg.avgSpend}</div>
                      </div>
                    </div>
                  </div>

                  {/* Period Averages */}
                  <div style={{marginBottom: '24px', padding: '16px', background: darkMode ? '#2b2d31' : '#f5f5f5', borderRadius: '8px'}}>
                    <h3 style={{marginTop: 0}}>Period Averages</h3>
                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px'}}>
                      <div>
                        <strong>Monthly:</strong>
                        <div>MIV: {managerAnalytics.monthlyAvg.avgMiv}</div>
                        <div>Spend: ${managerAnalytics.monthlyAvg.avgSpend}</div>
                      </div>
                      <div>
                        <strong>Yearly:</strong>
                        <div>MIV: {managerAnalytics.yearlyAvg.avgMiv}</div>
                        <div>Spend: ${managerAnalytics.yearlyAvg.avgSpend}</div>
                      </div>
                    </div>
                  </div>

                  {/* Staff Performance */}
                  <div style={{marginBottom: '24px'}}>
                    <h3>Staff Performance</h3>
                    <div style={{overflowX: 'auto'}}>
                      <table style={{width: '100%', borderCollapse: 'collapse'}}>
                        <thead>
                          <tr style={{borderBottom: '2px solid #ddd'}}>
                            <th style={{padding: '12px', textAlign: 'left'}}>Name</th>
                            <th style={{padding: '12px', textAlign: 'center'}}>Total Shifts</th>
                            <th style={{padding: '12px', textAlign: 'center'}}>Days Worked</th>
                            <th style={{padding: '12px', textAlign: 'center'}}>Most Frequent Day</th>
                            <th style={{padding: '12px', textAlign: 'center'}}>Top Role</th>
                            <th style={{padding: '12px', textAlign: 'center'}}>Avg MIV</th>
                            <th style={{padding: '12px', textAlign: 'center'}}>Avg Spend</th>
                          </tr>
                        </thead>
                        <tbody>
                          {managerAnalytics.staffStats.map((staff, idx) => (
                            <tr key={idx} style={{borderBottom: '1px solid #eee'}}>
                              <td style={{padding: '12px', fontWeight: 'bold'}}>{staff.name}</td>
                              <td style={{padding: '12px', textAlign: 'center'}}>{staff.totalShifts}</td>
                              <td style={{padding: '12px', textAlign: 'center'}}>{staff.daysWorked}</td>
                              <td style={{padding: '12px', textAlign: 'center'}}>{staff.mostFrequentDay}</td>
                              <td style={{padding: '12px', textAlign: 'center'}}>{staff.topRole}</td>
                              <td style={{padding: '12px', textAlign: 'center'}}>{staff.avgMiv}</td>
                              <td style={{padding: '12px', textAlign: 'center'}}>${staff.avgSpend}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Recent Reports */}
                  <div>
                    <h3>Recent Reports</h3>
                    {managerAnalytics.dailyStats.slice(0, 10).map((day, idx) => (
                      <div key={idx} style={{
                        padding: '12px',
                        marginBottom: '8px',
                        background: darkMode ? '#2b2d31' : '#f9f9f9',
                        borderRadius: '8px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <div>
                          <strong>{new Date(day.date).toLocaleDateString()}</strong>
                          <div style={{fontSize: '14px', color: '#666'}}>
                            Manager: {day.managers.join(', ')} | Staff: {day.staffCount}
                          </div>
                        </div>
                        <div style={{textAlign: 'right'}}>
                          <div>MIV: {day.miv} (Pred: {day.predMiv})</div>
                          <div>Spend: ${day.avgSpend}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* Edit Modal */}
            {editingIndex !== null && editingStat && (
              <div className="modal-overlay" onClick={handleCancelEdit}>
                <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                  <div className="modal-header">
                    <h2>Edit Entry</h2>
                    <button onClick={handleCancelEdit} className="modal-close">
                      <X size={24} />
                    </button>
                  </div>
                  <form onSubmit={handleUpdateStat} className="hospitality-form">
                    <div className="form-group">
                      <label>Date</label>
                      <input
                        type="date"
                        value={editingStat.date || ''}
                        onChange={(e) => setEditingStat({...editingStat, date: e.target.value})}
                      />
                    </div>
                    <div className="form-group">
                      <label>Meal Period</label>
                      <select
                        value={editingStat.meal_period}
                        onChange={(e) => setEditingStat({...editingStat, meal_period: e.target.value})}
                        required
                      >
                        <option value="lunch">Lunch</option>
                        <option value="dinner">Dinner</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>MIV</label>
                      <input
                        type="number"
                        value={editingStat.miv}
                        onChange={(e) => setEditingStat({...editingStat, miv: e.target.value})}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Average Spend ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={editingStat.average_spend}
                        onChange={(e) => setEditingStat({...editingStat, average_spend: e.target.value})}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Staff Member</label>
                      <input
                        type="text"
                        value={editingStat.staff_member}
                        onChange={(e) => setEditingStat({...editingStat, staff_member: e.target.value})}
                        required
                      />
                    </div>
                    <div className="modal-actions">
                      <button type="button" onClick={handleCancelEdit} className="cancel-btn">
                        <X size={18} />
                        Cancel
                      </button>
                      <button type="submit" className="submit-btn">
                        <Check size={18} />
                        Update
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default HospitalityStats;
