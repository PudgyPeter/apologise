import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FileText, 
  Search, 
  Download, 
  Trash2, 
  Calendar,
  MessageSquare,
  RefreshCw
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

  useEffect(() => {
    fetchLogs();
    fetchStats();
    fetchLiveMessages();
    
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

  const formatTimestamp = (timestamp) => {
    try {
      return format(new Date(timestamp), 'MMM dd, yyyy HH:mm:ss');
    } catch {
      return timestamp;
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
              <span className="message-author">{entry.author_display || entry.author}</span>
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
    const bottom = e.target.scrollHeight - e.target.scrollTop <= e.target.clientHeight + 100;
    if (bottom && hasMore) {
      setDisplayCount(prev => prev + 50);
    }
  };

  return (
    <div className={`app ${darkMode ? 'dark-mode' : ''}`}>
      <header className="header">
        <h1>📊 Discord Log Dashboard</h1>
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
              onClick={() => { setActiveTab('live'); setDisplayCount(50); }}
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
          </div>

          {loading && (
            <div className="loading">
              <RefreshCw className="spin" size={32} />
              <p>Loading...</p>
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
            </div>
          )}

          {!loading && activeTab === 'live' && (
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
        </main>
      </div>
    </div>
  );
}

export default App;
