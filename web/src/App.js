import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FileText, 
  Search, 
  Download, 
  Trash2, 
  Calendar,
  MessageSquare,
  RefreshCw,
  TrendingUp,
  Users,
  DollarSign,
  BarChart3,
  Edit2,
  X,
  Check,
  Menu,
  Activity
} from 'lucide-react';
import { format } from 'date-fns';
import './App.css';

function App() {
  const [logs, setLogs] = useState([]);
  const [selectedLog, setSelectedLog] = useState(null);
  const [logContent, setLogContent] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('logs'); // 'logs', 'search', or 'live'
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved === 'true';
  });
  const [liveMessages, setLiveMessages] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [displayCount, setDisplayCount] = useState(50);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileLogSelectorOpen, setMobileLogSelectorOpen] = useState(false);
  
  // Hospitality stats state
  const [hospitalityStats, setHospitalityStats] = useState([]);
  const [hospitalityAnalytics, setHospitalityAnalytics] = useState(null);
  const [mealPeriodFilter, setMealPeriodFilter] = useState('all'); // 'all', 'lunch', 'dinner'
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
    fetchLogs();
    fetchStats();
    fetchLiveMessages();
    
    // Fetch hospitality stats if on that tab
    if (activeTab === 'hospitality') {
      fetchHospitalityStats();
      fetchHospitalityAnalytics();
    }

    // Listen for service worker cache updates
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'CACHE_UPDATED') {
          console.log('Cache updated to version:', event.data.version);
          // Auto-reload to get fresh content
          window.location.reload();
        }
      });
    }
    
    // Auto-refresh live messages every 5 seconds
    const interval = setInterval(() => {
      if (activeTab === 'live') {
        fetchLiveMessages();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [activeTab]);

  // Persist dark mode preference
  useEffect(() => {
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  // Auto-scroll to bottom when live messages update
  useEffect(() => {
    if (activeTab === 'live' && autoScroll) {
      const container = document.querySelector('.log-entries');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [liveMessages, activeTab, autoScroll]);

  const fetchLogs = async () => {
    try {
      const response = await axios.get('/api/logs');
      setLogs(response.data);
    } catch (error) {
      console.error('Error fetching logs:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchLiveMessages = async () => {
    try {
      const response = await axios.get('/api/live');
      console.log('Live messages fetched:', response.data.length);
      setLiveMessages(response.data);
    } catch (error) {
      console.error('Error fetching live messages:', error);
    }
  };

  const fetchLogContent = async (filename) => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/logs/${filename}`);
      setLogContent(response.data);
      setSelectedLog(filename);
      setDisplayCount(50);
    } catch (error) {
      console.error('Error fetching log content:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;
    
    setLoading(true);
    setActiveTab('search');
    try {
      const response = await axios.post('/api/search', { 
        term: searchTerm,
        max_results: 200 
      });
      setSearchResults(response.data.results);
      setDisplayCount(50);
    } catch (error) {
      console.error('Error searching logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (filename) => {
    try {
      const response = await axios.get(`/api/logs/${filename}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename.replace('.json', '.txt'));
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading log:', error);
    }
  };

  const handleDelete = async (name) => {
    if (!window.confirm(`Delete custom log "${name}"?`)) return;
    
    try {
      await axios.delete(`/api/logs/custom/${name}`);
      fetchLogs();
      if (selectedLog === `custom_${name}.json`) {
        setSelectedLog(null);
        setLogContent([]);
      }
    } catch (error) {
      console.error('Error deleting log:', error);
    }
  };

  // Hospitality stats functions
  const fetchHospitalityStats = async () => {
    try {
      const response = await axios.get('/api/hospitality/stats');
      setHospitalityStats(response.data);
      console.log('Hospitality stats loaded:', response.data.length, 'entries');
      console.log('Valid indices: 0 to', response.data.length - 1);
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
    // Ensure meal_period has a default value if it doesn't exist
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

  const formatTimestamp = (timestamp) => {
    try {
      return format(new Date(timestamp), 'MMM dd, yyyy HH:mm:ss');
    } catch {
      return timestamp;
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      // Parse YYYY-MM-DD format and convert to DD/MM/YYYY
      const date = new Date(dateString + 'T00:00:00'); // Add time to avoid timezone issues
      return format(date, 'dd/MM/yyyy');
    } catch {
      return dateString;
    }
  };

  const getTypeEmoji = (type) => {
    const emojis = {
      create: '💬',
      edit: '✏️',
      delete: '🗑️',
      reaction: '🔁'
    };
    return emojis[type] || '💬';
  };

  // Filter analytics data by meal period
  const getFilteredAnalytics = () => {
    if (!hospitalityAnalytics || mealPeriodFilter === 'all') {
      return hospitalityAnalytics;
    }

    // Filter stats by meal period
    const filteredStats = hospitalityStats.filter(stat => stat.meal_period === mealPeriodFilter);
    
    if (filteredStats.length === 0) {
      return null;
    }

    // Recalculate analytics for filtered data
    const staffData = {};
    const dayData = {};
    let totalMiv = 0;
    let totalSpend = 0;

    filteredStats.forEach(entry => {
      const staff = entry.staff_member || 'Unknown';
      const miv = parseFloat(entry.miv || 0);
      const avgSpend = parseFloat(entry.average_spend || 0);

      // Staff stats
      if (!staffData[staff]) {
        staffData[staff] = { total_spend: 0, total_miv: 0, count: 0 };
      }
      staffData[staff].total_spend += avgSpend;
      staffData[staff].total_miv += miv;
      staffData[staff].count += 1;

      // Day of week stats
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

    // Calculate staff performance
    const staffPerformance = Object.entries(staffData).map(([staff, data]) => ({
      staff_member: staff,
      avg_spend: (data.total_spend / data.count).toFixed(2),
      avg_miv: (data.total_miv / data.count).toFixed(2),
      total_entries: data.count
    })).sort((a, b) => parseFloat(b.avg_spend) - parseFloat(a.avg_spend));

    // Calculate day of week averages
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

  const getAvatarUrl = (entry) => {
    // Use real Discord avatar if available
    if (entry.avatar_url) {
      return entry.avatar_url;
    }
    
    // Fallback to generated avatar
    const author = entry.author || entry.author_display || 'Unknown';
    const hash = author.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const colors = ['#5865F2', '#57F287', '#FEE75C', '#EB459E', '#ED4245', '#3BA55D'];
    const color = colors[hash % colors.length];
    const initials = author.split('#')[0].substring(0, 2).toUpperCase();
    
    return `https://ui-avatars.com/api/?name=${initials}&background=${color.substring(1)}&color=fff&size=128`;
  };

  const renderLogEntry = (entry, index) => {
    const data = displayedData;
    const isGroupStart = index === 0 || 
      data[index - 1].author !== entry.author ||
      data[index - 1].channel !== entry.channel;
    
    return (
      <div key={index} className={`discord-message ${isGroupStart ? 'group-start' : ''}`}>
        {isGroupStart && (
          <div className="message-avatar">
            <img src={getAvatarUrl(entry)} alt={entry.author} />
          </div>
        )}
        {!isGroupStart && <div className="message-avatar-spacer"></div>}
        
        <div className="message-content-wrapper">
          {isGroupStart && (
            <div className="message-header">
              <span className="message-author" style={entry.role_color ? {color: entry.role_color} : {}}>
                {entry.author_display || entry.author}
              </span>
              <span className="message-timestamp">{formatTimestamp(entry.created_at)}</span>
              <span className="message-channel">#{entry.channel}</span>
              {entry.type !== 'create' && (
                <span className="message-type-badge">{getTypeEmoji(entry.type)} {entry.type}</span>
              )}
            </div>
          )}
          
          <div className="message-body">
            {entry.reply_preview && (
              <div className="message-reply">
                <div className="reply-bar"></div>
                <div className="reply-content">
                  <span className="reply-author">{entry.reply_preview.author}</span>
                  <span className="reply-text">{entry.reply_preview.content}</span>
                </div>
              </div>
            )}
            
            {entry.type === 'edit' && entry.before && (
              <div className="message-edit">
                <div className="edit-before">
                  <span className="edit-label">Before:</span> {entry.before}
                </div>
                <div className="edit-after">
                  <span className="edit-label">After:</span> {entry.content}
                </div>
              </div>
            )}
            
            {entry.type !== 'edit' && (
              <div className="message-text">{entry.content || '(no text)'}</div>
            )}
            
            {entry.attachments && entry.attachments.length > 0 && (
              <div className="message-attachments">
                {entry.attachments.map((url, i) => {
                  const isImage = /\.(gif|png|jpe?g|webp)$/i.test(url);
                  const isVideo = /\.(mp4|mov|webm)$/i.test(url);
                  
                  if (isImage) {
                    return (
                      <div key={i} className="attachment-image">
                        <img src={url} alt={`Attachment ${i + 1}`} />
                      </div>
                    );
                  } else if (isVideo) {
                    return (
                      <div key={i} className="attachment-video">
                        <video controls src={url} />
                      </div>
                    );
                  } else {
                    const filename = url.split('/').pop().split('?')[0];
                    return (
                      <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="attachment-link">
                        📎 {filename}
                      </a>
                    );
                  }
                })}
              </div>
            )}
            
            {entry.reactions && Object.keys(entry.reactions).length > 0 && (
              <div className="message-reactions">
                {Object.entries(entry.reactions).map(([emoji, info]) => (
                  <div key={emoji} className="reaction">
                    <span className="reaction-emoji">{emoji}</span>
                    <span className="reaction-count">{info.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const getDataForTab = () => {
    if (activeTab === 'search') return searchResults;
    if (activeTab === 'live') return liveMessages;
    return logContent;
  };

  const displayedData = getDataForTab().slice(0, displayCount);
  const hasMore = getDataForTab().length > displayCount;

  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 200;
    
    if (isNearBottom && hasMore && !loading) {
      console.log('Loading more messages...');
      setDisplayCount(prev => prev + 50);
    }
  };

  const handleMobileNav = (tab) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
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
                className={`mobile-nav-btn ${activeTab === 'logs' ? 'active' : ''}`}
                onClick={() => handleMobileNav('logs')}
              >
                <FileText size={32} />
                <span>Logs</span>
              </button>
              <button 
                className={`mobile-nav-btn ${activeTab === 'live' ? 'active' : ''}`}
                onClick={() => handleMobileNav('live')}
              >
                <Activity size={32} />
                <span>Live Feed</span>
              </button>
              <button 
                className={`mobile-nav-btn ${activeTab === 'hospitality' ? 'active' : ''}`}
                onClick={() => handleMobileNav('hospitality')}
              >
                <TrendingUp size={32} />
                <span>Stats</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Log Selector Panel */}
      {mobileLogSelectorOpen && (
        <div className="mobile-menu-overlay" onClick={() => setMobileLogSelectorOpen(false)}>
          <div className="mobile-log-selector" onClick={(e) => e.stopPropagation()}>
            <div className="mobile-menu-header">
              <h2>Select Log</h2>
              <button onClick={() => setMobileLogSelectorOpen(false)} className="mobile-menu-close">
                <X size={24} />
              </button>
            </div>
            <div className="mobile-log-list">
              {logs.map((log) => (
                <button
                  key={log.filename}
                  className={`mobile-log-item ${selectedLog === log.filename ? 'active' : ''}`}
                  onClick={() => {
                    fetchLogContent(log.filename);
                    setMobileLogSelectorOpen(false);
                  }}
                >
                  <div className="mobile-log-info">
                    <div className="mobile-log-name">
                      {log.is_custom && '⭐ '}
                      {log.name}
                    </div>
                    <div className="mobile-log-size">{log.size_kb} KB</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <header className="header">
        <div className="header-content">
          <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(true)}>
            <Menu size={24} />
          </button>
          <h1>📊 Pudge's Dashboard</h1>
          <span className="version-badge">v2.0.5</span>
        </div>
        {stats && (
          <div className="stats">
            <div className="stat">
              <FileText size={20} />
              <span>{stats.total_logs} Daily Logs</span>
            </div>
            <div className="stat">
              <Calendar size={20} />
              <span>{stats.custom_logs} Custom Logs</span>
            </div>
            <div className="stat">
              <MessageSquare size={20} />
              <span>{stats.total_messages.toLocaleString()} Messages</span>
            </div>
            <button 
              className="dark-mode-toggle" 
              onClick={() => setDarkMode(!darkMode)}
              title={darkMode ? 'Light Mode' : 'Dark Mode'}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        )}
      </header>

      <div className="container">
        <aside className="sidebar">
          <div className="search-box">
            <input
              type="text"
              placeholder="Search all logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button onClick={handleSearch} disabled={loading}>
              <Search size={20} />
            </button>
          </div>

          <div className="log-list">
            <div className="log-list-header">
              <h3>Available Logs</h3>
              <button onClick={fetchLogs} className="refresh-btn">
                <RefreshCw size={16} />
              </button>
            </div>
            {logs.map((log) => (
              <div
                key={log.filename}
                className={`log-item ${selectedLog === log.filename ? 'active' : ''}`}
              >
                <div 
                  className="log-item-info"
                  onClick={() => fetchLogContent(log.filename)}
                >
                  <div className="log-item-name">
                    {log.is_custom && '⭐ '}
                    {log.name}
                  </div>
                  <div className="log-item-size">{log.size_kb} KB</div>
                </div>
                <div className="log-item-actions">
                  <button
                    onClick={() => handleDownload(log.filename)}
                    title="Download"
                  >
                    <Download size={16} />
                  </button>
                  {log.is_custom && (
                    <button
                      onClick={() => handleDelete(log.name)}
                      title="Delete"
                      className="delete-btn"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </aside>

        <main className="main-content">
          <div className="tabs">
            <button
              className={activeTab === 'logs' ? 'active' : ''}
              onClick={() => setActiveTab('logs')}
            >
              <FileText size={18} />
              Log Viewer
            </button>
            <button
              className={activeTab === 'live' ? 'active' : ''}
              onClick={() => { 
                setActiveTab('live'); 
                setDisplayCount(50);
                if (liveMessages.length === 0) {
                  fetchLiveMessages();
                }
              }}
            >
              <MessageSquare size={18} />
              Live Feed
            </button>
            <button
              className={activeTab === 'search' ? 'active' : ''}
              onClick={() => setActiveTab('search')}
            >
              <Search size={18} />
              Search Results
            </button>
            <button
              className={activeTab === 'hospitality' ? 'active' : ''}
              onClick={() => setActiveTab('hospitality')}
            >
              <TrendingUp size={18} />
              Hospitality Stats
            </button>
          </div>

          {loading && (
            <div className="loading">
              <RefreshCw className="spin" size={32} />
              <p>Loading...</p>
            </div>
          )}

          {!loading && activeTab === 'logs' && logContent.length === 0 && (
            <div className="empty-state">
              <FileText size={64} />
              <h3>No log selected</h3>
              <p>Select a log file to view its contents</p>
              
              {/* Mobile floating button to select logs */}
              <button className="mobile-log-selector-btn" onClick={() => setMobileLogSelectorOpen(true)}>
                <FileText size={24} />
              </button>
            </div>
          )}

          {!loading && activeTab === 'logs' && logContent.length > 0 && (
            <div className="content-area">
              <div className="content-header">
                <h2>{selectedLog}</h2>
                <span>{logContent.length} messages</span>
              </div>
              <div className="log-entries" onScroll={handleScroll}>
                {displayedData.map((entry, index) => renderLogEntry(entry, index))}
                {hasMore && <div className="loading-more">Scroll for more...</div>}
              </div>
              
              {/* Mobile floating button to select logs */}
              <button className="mobile-log-selector-btn" onClick={() => setMobileLogSelectorOpen(true)}>
                <FileText size={24} />
              </button>
            </div>
          )}

          {!loading && activeTab === 'live' && liveMessages.length > 0 && (
            <div className="content-area">
              <div className="content-header">
                <h2>Live Feed</h2>
                <span>{liveMessages.length} messages</span>
              </div>
              <div className="log-entries" onScroll={handleScroll}>
                {displayedData.map((entry, index) => renderLogEntry(entry, index))}
                {hasMore && <div className="loading-more">Scroll for more...</div>}
              </div>
            </div>
          )}

          {!loading && activeTab === 'live' && liveMessages.length === 0 && (
            <div className="empty-state">
              <MessageSquare size={64} />
              <h3>No live messages yet</h3>
              <p>Messages will appear here as they are sent in Discord</p>
            </div>
          )}

          {!loading && activeTab === 'search' && searchResults.length > 0 && (
            <div className="content-area">
              <div className="content-header">
                <h2>Search Results for "{searchTerm}"</h2>
                <span>{searchResults.length} results</span>
              </div>
              <div className="log-entries" onScroll={handleScroll}>
                {displayedData.map((entry, index) => renderLogEntry(entry, index))}
                {hasMore && <div className="loading-more">Scroll for more...</div>}
              </div>
            </div>
          )}

          {!loading && activeTab === 'logs' && logContent.length === 0 && (
            <div className="empty-state">
              <FileText size={64} />
              <h3>No log selected</h3>
              <p>Select a log from the sidebar to view its contents</p>
            </div>
          )}

          {!loading && activeTab === 'search' && searchResults.length === 0 && searchTerm && (
            <div className="empty-state">
              <Search size={64} />
              <h3>No results found</h3>
              <p>Try a different search term</p>
            </div>
          )}

          {activeTab === 'hospitality' && (
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
                        const isEditing = editingIndex === actualIndex;
                        
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
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
