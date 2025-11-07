import React, { useState, useEffect } from 'react';
import { Moon, Plus, Search, TrendingUp, Calendar, Tag, X, Edit2, Trash2, Save, Wifi, WifiOff } from 'lucide-react';
import { dreamAPI } from '../supabaseClient';

const DreamJournal = ({ darkMode, setDarkMode }) => {
  const [dreams, setDreams] = useState([]);
  const [stats, setStats] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingDream, setEditingDream] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    date: new Date().toISOString().split('T')[0],
    tags: ''
  });
  const [selectedDream, setSelectedDream] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [syncStatus, setSyncStatus] = useState('synced'); // 'synced', 'syncing', 'offline'

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setSyncStatus('syncing');
      // Reload data when coming back online
      loadData();
    };
    const handleOffline = () => {
      setIsOnline(false);
      setSyncStatus('offline');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Fetch dreams
  const fetchDreams = async () => {
    try {
      const data = await dreamAPI.getAll({ search: searchTerm });
      setDreams(data);
      setSyncStatus('synced');
    } catch (error) {
      console.error('Error fetching dreams:', error);
      setSyncStatus('offline');
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const data = await dreamAPI.getStats();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Load data
  const loadData = async () => {
    setLoading(true);
    await Promise.all([fetchDreams(), fetchStats()]);
    setLoading(false);
  };

  // Initial load and real-time subscription
  useEffect(() => {
    loadData();

    // Subscribe to real-time changes (only if Supabase is configured)
    const subscription = dreamAPI.subscribeToChanges((payload) => {
      console.log('Real-time update received:', payload);
      
      if (payload.eventType === 'INSERT') {
        setDreams(prev => [payload.new, ...prev]);
        fetchStats(); // Refresh stats
      } else if (payload.eventType === 'UPDATE') {
        setDreams(prev => prev.map(d => d.id === payload.new.id ? payload.new : d));
        fetchStats();
      } else if (payload.eventType === 'DELETE') {
        setDreams(prev => prev.filter(d => d.id !== payload.old.id));
        fetchStats();
      }
    });

    return () => {
      if (subscription) {
        dreamAPI.unsubscribe(subscription);
      }
    };
  }, []);

  // Create or update dream
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSyncStatus('syncing');
    try {
      const dreamData = {
        title: formData.title,
        content: formData.content,
        date: formData.date,
        tags: formData.tags.split(',').map(t => t.trim()).filter(t => t)
      };

      if (editingDream) {
        await dreamAPI.update(editingDream.id, dreamData);
      } else {
        await dreamAPI.create(dreamData);
      }

      setFormData({ title: '', content: '', date: new Date().toISOString().split('T')[0], tags: '' });
      setShowAddForm(false);
      setEditingDream(null);
      setSyncStatus('synced');
      // Refresh data (real-time will update if Supabase is configured, otherwise we need to fetch)
      await loadData();
    } catch (error) {
      console.error('Error saving dream:', error);
      setSyncStatus('offline');
      alert('Failed to save dream. Please check your connection.');
    }
  };

  // Delete dream
  const handleDelete = async (dreamId) => {
    if (window.confirm('Are you sure you want to delete this dream?')) {
      setSyncStatus('syncing');
      try {
        await dreamAPI.delete(dreamId);
        setSelectedDream(null);
        setSyncStatus('synced');
        // Refresh data
        await loadData();
      } catch (error) {
        console.error('Error deleting dream:', error);
        setSyncStatus('offline');
        alert('Failed to delete dream. Please check your connection.');
      }
    }
  };

  // Edit dream
  const handleEdit = (dream) => {
    setEditingDream(dream);
    setFormData({
      title: dream.title,
      content: dream.content,
      date: dream.date,
      tags: dream.tags.join(', ')
    });
    setShowAddForm(true);
    setSelectedDream(null);
  };

  // Filter dreams
  const filteredDreams = dreams.filter(dream =>
    dream.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dream.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dream.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Highlight keywords in text
  const highlightKeywords = (text, keywords) => {
    if (!keywords || Object.keys(keywords).length === 0) return text;
    
    const topKeywords = Object.entries(keywords)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([word]) => word);
    
    let highlightedText = text;
    topKeywords.forEach(keyword => {
      const regex = new RegExp(`\\b(${keyword})\\b`, 'gi');
      highlightedText = highlightedText.replace(regex, '<mark class="keyword-highlight">$1</mark>');
    });
    
    return highlightedText;
  };

  // Set body background color to match gradient
  React.useEffect(() => {
    document.body.style.background = darkMode 
      ? '#1a202c' 
      : '#667eea';
    return () => {
      document.body.style.background = '';
    };
  }, [darkMode]);

  return (
    <div className={`app-container ${darkMode ? 'dark-mode' : ''}`}>
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <Moon size={32} className="header-icon" />
            <h1>Dream Journal</h1>
            {/* Sync Status Indicator */}
            <div className={`sync-status ${syncStatus}`} title={
              syncStatus === 'synced' ? 'All changes saved' :
              syncStatus === 'syncing' ? 'Syncing...' :
              'Offline - changes will sync when online'
            }>
              {isOnline ? (
                syncStatus === 'syncing' ? (
                  <><Wifi size={16} className="pulse" /> Syncing...</>
                ) : (
                  <><Wifi size={16} /> Synced</>
                )
              ) : (
                <><WifiOff size={16} /> Offline</>
              )}
            </div>
          </div>
          <div className="header-right">
            <button
              className="theme-toggle"
              onClick={() => setDarkMode(!darkMode)}
              title={darkMode ? 'Light Mode' : 'Dark Mode'}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>

      {/* Stats Dashboard */}
      {stats && (
        <div className="stats-container">
          <div className="stat-card">
            <div className="stat-icon">📖</div>
            <div className="stat-content">
              <div className="stat-value">{stats.total_dreams}</div>
              <div className="stat-label">Total Dreams</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📝</div>
            <div className="stat-content">
              <div className="stat-value">{stats.total_words.toLocaleString()}</div>
              <div className="stat-label">Total Words</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📊</div>
            <div className="stat-content">
              <div className="stat-value">{stats.avg_words_per_dream}</div>
              <div className="stat-label">Avg Words/Dream</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔑</div>
            <div className="stat-content">
              <div className="stat-value">{stats.top_keywords.length}</div>
              <div className="stat-label">Unique Keywords</div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="main-content">
        {/* Sidebar - Keywords */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <h3><TrendingUp size={20} /> Top Keywords</h3>
            {stats && stats.top_keywords.length > 0 ? (
              <div className="keywords-list">
                {stats.top_keywords.slice(0, 20).map((kw, idx) => (
                  <div key={idx} className="keyword-item">
                    <span className="keyword-word">{kw.word}</span>
                    <span className="keyword-count">{kw.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state">No keywords yet</p>
            )}
          </div>

          <div className="sidebar-section">
            <h3><Calendar size={20} /> Dreams by Month</h3>
            {stats && Object.keys(stats.dreams_by_month).length > 0 ? (
              <div className="months-list">
                {Object.entries(stats.dreams_by_month)
                  .sort((a, b) => b[0].localeCompare(a[0]))
                  .map(([month, count]) => (
                    <div key={month} className="month-item">
                      <span className="month-name">{month}</span>
                      <span className="month-count">{count}</span>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="empty-state">No dreams yet</p>
            )}
          </div>
        </aside>

        {/* Dream List */}
        <div className="dreams-section">
          <div className="dreams-header">
            <div className="search-bar">
              <Search size={20} />
              <input
                type="text"
                placeholder="Search dreams..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button
              className="add-dream-btn"
              onClick={() => {
                setShowAddForm(!showAddForm);
                setEditingDream(null);
                setFormData({ title: '', content: '', date: new Date().toISOString().split('T')[0], tags: '' });
              }}
            >
              <Plus size={20} />
              New Dream
            </button>
          </div>

          {/* Add/Edit Form */}
          {showAddForm && (
            <div className="dream-form-card">
              <div className="form-header">
                <h3>{editingDream ? 'Edit Dream' : 'New Dream'}</h3>
                <button onClick={() => { setShowAddForm(false); setEditingDream(null); }}>
                  <X size={20} />
                </button>
              </div>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label>Title</label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    placeholder="Give your dream a title..."
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Date</label>
                  <input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Dream Content</label>
                  <textarea
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    placeholder="Describe your dream in detail..."
                    rows={10}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Tags (comma-separated)</label>
                  <input
                    type="text"
                    value={formData.tags}
                    onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                    placeholder="nightmare, flying, family..."
                  />
                </div>
                <div className="form-actions">
                  <button type="submit" className="save-btn">
                    <Save size={20} />
                    {editingDream ? 'Update Dream' : 'Save Dream'}
                  </button>
                  <button type="button" className="cancel-btn" onClick={() => { setShowAddForm(false); setEditingDream(null); }}>
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Dreams List */}
          <div className="dreams-list">
            {loading ? (
              <div className="loading">Loading dreams...</div>
            ) : filteredDreams.length === 0 ? (
              <div className="empty-state">
                {searchTerm ? 'No dreams match your search' : 'No dreams yet. Start logging your dreams!'}
              </div>
            ) : (
              filteredDreams.map(dream => (
                <div
                  key={dream.id}
                  className={`dream-card ${selectedDream?.id === dream.id ? 'selected' : ''}`}
                  onClick={() => setSelectedDream(selectedDream?.id === dream.id ? null : dream)}
                >
                  <div className="dream-header">
                    <h3>{dream.title}</h3>
                    <div className="dream-actions">
                      <button onClick={(e) => { e.stopPropagation(); handleEdit(dream); }}>
                        <Edit2 size={16} />
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); handleDelete(dream.id); }}>
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                  <div className="dream-date">
                    <Calendar size={14} />
                    {new Date(dream.date).toLocaleDateString('en-US', { 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric' 
                    })}
                  </div>
                  {dream.tags && dream.tags.length > 0 && (
                    <div className="dream-tags">
                      {dream.tags.map((tag, idx) => (
                        <span key={idx} className="tag">
                          <Tag size={12} />
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="dream-content">
                    {selectedDream?.id === dream.id ? (
                      <div
                        dangerouslySetInnerHTML={{
                          __html: highlightKeywords(dream.content, dream.keywords)
                        }}
                      />
                    ) : (
                      <p>{dream.content.substring(0, 150)}{dream.content.length > 150 ? '...' : ''}</p>
                    )}
                  </div>
                  {selectedDream?.id === dream.id && dream.keywords && Object.keys(dream.keywords).length > 0 && (
                    <div className="dream-keywords">
                      <h4>Keywords in this dream:</h4>
                      <div className="keywords-cloud">
                        {Object.entries(dream.keywords)
                          .sort((a, b) => b[1] - a[1])
                          .slice(0, 15)
                          .map(([word, count]) => (
                            <span key={word} className="keyword-tag" style={{ fontSize: `${12 + Math.min(count * 2, 12)}px` }}>
                              {word} ({count})
                            </span>
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DreamJournal;
