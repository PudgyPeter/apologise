import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FileText, 
  Search, 
  Download, 
  Trash2, 
  Calendar,
  MessageSquare,
  BarChart3,
  RefreshCw,
  ChevronLeft,
  ChevronRight
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
  const [activeTab, setActiveTab] = useState('logs'); // 'logs' or 'search'
  const [currentPage, setCurrentPage] = useState(0);
  const itemsPerPage = 20;

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, []);

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

  const fetchLogContent = async (filename) => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/logs/${filename}`);
      setLogContent(response.data);
      setSelectedLog(filename);
      setCurrentPage(0);
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
      setCurrentPage(0);
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

  const renderLogEntry = (entry, index) => (
    <div key={index} className="log-entry">
      <div className="log-header">
        <span className="log-emoji">{getTypeEmoji(entry.type)}</span>
        <span className="log-author">{entry.author}</span>
        <span className="log-channel">#{entry.channel}</span>
        <span className="log-time">{formatTimestamp(entry.created_at)}</span>
      </div>
      <div className="log-content">
        {entry.type === 'edit' && entry.before && (
          <div className="log-edit">
            <div className="edit-before">Before: {entry.before}</div>
            <div className="edit-after">After: {entry.content}</div>
          </div>
        )}
        {entry.type !== 'edit' && (
          <div>{entry.content || '(no text)'}</div>
        )}
        {entry.attachments && entry.attachments.length > 0 && (
          <div className="log-attachments">
            {entry.attachments.map((url, i) => (
              <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                📎 Attachment {i + 1}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const totalPages = Math.ceil(
    (activeTab === 'search' ? searchResults.length : logContent.length) / itemsPerPage
  );

  const paginatedData = (activeTab === 'search' ? searchResults : logContent)
    .slice(currentPage * itemsPerPage, (currentPage + 1) * itemsPerPage);

  return (
    <div className="app">
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
              <div className="log-entries">
                {paginatedData.map((entry, index) => renderLogEntry(entry, index))}
              </div>
            </div>
          )}

          {!loading && activeTab === 'search' && searchResults.length > 0 && (
            <div className="content-area">
              <div className="content-header">
                <h2>Search Results for "{searchTerm}"</h2>
                <span>{searchResults.length} results</span>
              </div>
              <div className="log-entries">
                {paginatedData.map((entry, index) => renderLogEntry(entry, index))}
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

          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                disabled={currentPage === 0}
              >
                <ChevronLeft size={20} />
              </button>
              <span>
                Page {currentPage + 1} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages - 1, currentPage + 1))}
                disabled={currentPage === totalPages - 1}
              >
                <ChevronRight size={20} />
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
