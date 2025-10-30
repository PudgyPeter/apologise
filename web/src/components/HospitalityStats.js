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
  Calendar
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

  useEffect(() => {
    fetchHospitalityStats();
    fetchHospitalityAnalytics();
    
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

  const handleSubmitStat = async (e) => {
    e.preventDefault();
    
    if (!newStat.miv || !newStat.average_spend || !newStat.staff_member || !newStat.meal_period) {
      alert('Please fill in all fields');
      return;
    }
    
    try {
      await axios.post('/api/hospitality/stats', newStat);
      setNewStat({ date: '', miv: '', average_spend: '', staff_member: '', meal_period: 'lunch' });
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

  return (
    <div className={`app ${darkMode ? 'dark-mode' : ''}`}>
      <header className="header">
        <div className="header-content">
          <h1>📊 Hospitality Stats Dashboard</h1>
          <span className="version-badge">v2.0.5</span>
          <button 
            className="dark-mode-toggle" 
            onClick={() => setDarkMode(!darkMode)}
            title={darkMode ? 'Light Mode' : 'Dark Mode'}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      <div className="container" style={{ gridTemplateColumns: '1fr', height: 'auto' }}>
        <main className="main-content">
          <div className="content-area hospitality-content">
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
            </div>

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
