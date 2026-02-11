import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { 
  FileText, 
  Search, 
  Download, 
  Trash2, 
  MessageSquare,
  RefreshCw,
  Menu,
  Activity,
  X,
  Hash,
  Users,
  BarChart3,
  ChevronDown,
  Filter,
  Pencil,
  Trash,
  Clock,
  TrendingUp,
  AtSign,
  Send,
  SmilePlus,
  ChevronRight
} from 'lucide-react';
import { format } from 'date-fns';

function DiscordDashboard({ darkMode, setDarkMode }) {
  // --- State ---
  const [logs, setLogs] = useState([]);
  const [selectedLog, setSelectedLog] = useState(null);
  const [logContent, setLogContent] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [, setStats] = useState(null);
  const [enhancedStats, setEnhancedStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('live');
  const [liveMessages, setLiveMessages] = useState([]);
  const isNearBottomRef = useRef(true);
  const [displayCount, setDisplayCount] = useState(100);
  const [historyMessages, setHistoryMessages] = useState([]); // older messages from previous days
  const [historyBeforeDate, setHistoryBeforeDate] = useState(null); // cursor for next history fetch
  const [historyHasMore, setHistoryHasMore] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Discord-like features
  const [channels, setChannels] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [filterType, setFilterType] = useState('all'); // all, create, edit, delete
  const [showUserPanel, setShowUserPanel] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Discord API interaction
  const [discordChannels, setDiscordChannels] = useState([]); // channels with IDs from Discord API
  const [, setGuildId] = useState(null);
  const [channelMap, setChannelMap] = useState({}); // name -> id mapping
  const [messageInput, setMessageInput] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [sendChannelId, setSendChannelId] = useState(null); // override channel for sending
  const [emojiPickerMsg, setEmojiPickerMsg] = useState(null); // {channelId, messageId} for open picker
  const [hoveredMsgId, setHoveredMsgId] = useState(null);

  // Mobile
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const logEntriesRef = useRef(null);
  const messageInputRef = useRef(null);

  const QUICK_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🔥', '👀', '💀', '✅', '❌', '🎉', '💯', '🤔', '😍', '👎', '⭐'];

  // --- Data Fetching ---
  useEffect(() => {
    fetchLogs();
    fetchStats();
    fetchLiveMessages();
    fetchChannels();
    fetchUsers();
    fetchEnhancedStats();
    fetchDiscordGuilds();

    const interval = setInterval(() => {
      if (activeTab === 'live') fetchLiveMessages();
    }, 5000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  // Build channel name -> ID map from Discord API + message data
  useEffect(() => {
    const map = {};
    // First pass: extract channel_id from actual messages (reliable fallback)
    [...liveMessages, ...historyMessages].forEach(msg => {
      if (msg.channel && msg.channel_id) {
        map[msg.channel] = String(msg.channel_id);
      }
    });
    // Second pass: Discord API channels override (authoritative)
    discordChannels.forEach(ch => { map[ch.name] = ch.id; });
    setChannelMap(map);
  }, [discordChannels, liveMessages, historyMessages]);

  useEffect(() => {
    if (activeTab === 'live' && isNearBottomRef.current && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [liveMessages, activeTab]);

  const fetchLogs = async () => {
    try {
      const res = await axios.get('/api/logs');
      setLogs(res.data);
    } catch (e) { console.error('Error fetching logs:', e); }
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/stats');
      setStats(res.data);
    } catch (e) { console.error('Error fetching stats:', e); }
  };

  const fetchEnhancedStats = async () => {
    try {
      const res = await axios.get('/api/stats/enhanced');
      setEnhancedStats(res.data);
    } catch (e) { console.error('Error fetching enhanced stats:', e); }
  };

  const fetchLiveMessages = async () => {
    try {
      const res = await axios.get('/api/live');
      setLiveMessages(res.data);
      // Set history cursor to today's date on first load so history fetches older days
      if (!historyBeforeDate && res.data.length > 0) {
        try {
          const oldest = res.data[0];
          const d = new Date(oldest.created_at);
          // Use the date of the oldest message in the live feed as the starting cursor
          const dateStr = d.toISOString().split('T')[0];
          setHistoryBeforeDate(dateStr);
        } catch { /* ignore */ }
      }
    } catch (e) { console.error('Error fetching live messages:', e); }
  };

  const fetchHistory = async () => {
    if (loadingHistory || !historyHasMore) return;
    setLoadingHistory(true);
    try {
      const params = historyBeforeDate ? `?before_date=${historyBeforeDate}&limit=3` : '?limit=3';
      const res = await axios.get(`/api/live/history${params}`);
      const { messages, has_more, oldest_date } = res.data;
      if (messages.length > 0) {
        setHistoryMessages(prev => [...messages, ...prev]);
      }
      setHistoryHasMore(has_more);
      if (oldest_date) {
        setHistoryBeforeDate(oldest_date);
      } else {
        setHistoryHasMore(false);
      }
    } catch (e) { console.error('Error fetching history:', e); }
    finally { setLoadingHistory(false); }
  };

  const fetchChannels = async () => {
    try {
      const res = await axios.get('/api/channels');
      setChannels(res.data);
    } catch (e) { console.error('Error fetching channels:', e); }
  };

  const fetchUsers = async () => {
    try {
      const res = await axios.get('/api/users');
      setUsers(res.data);
    } catch (e) { console.error('Error fetching users:', e); }
  };

  const fetchDiscordGuilds = async () => {
    try {
      const res = await axios.get('/api/discord/guilds');
      if (res.data.length > 0) {
        const gid = res.data[0].id;
        setGuildId(gid);
        fetchDiscordChannels(gid);
      }
    } catch (e) { console.error('Error fetching guilds:', e); }
  };

  const fetchDiscordChannels = async (gid) => {
    try {
      const res = await axios.get(`/api/discord/channels/${gid}`);
      setDiscordChannels(res.data);
    } catch (e) { console.error('Error fetching discord channels:', e); }
  };

  // --- Discord Actions ---
  const getChannelId = (entry) => {
    // Use channel_id from entry if available, otherwise look up by name
    if (entry.channel_id) return String(entry.channel_id);
    return channelMap[entry.channel] || null;
  };

  const handleSendMessage = async () => {
    const content = messageInput.trim();
    if (!content || sendingMessage) return;
    // Determine target channel
    const targetId = sendChannelId || (selectedChannel ? channelMap[selectedChannel] : null);
    if (!targetId) {
      alert('Select a channel to send messages to');
      return;
    }
    setSendingMessage(true);
    try {
      await axios.post('/api/discord/send', { channel_id: targetId, content });
      setMessageInput('');
      // Refresh live feed after a short delay to pick up the new message
      setTimeout(fetchLiveMessages, 1500);
    } catch (e) {
      console.error('Error sending message:', e);
      alert('Failed to send message: ' + (e.response?.data?.error || e.message));
    } finally { setSendingMessage(false); }
  };

  const handleReact = async (entry, emoji) => {
    const chId = getChannelId(entry);
    const msgId = entry.message_id || entry.id;
    if (!chId || !msgId) { console.error('Missing channel or message ID for reaction'); return; }
    setEmojiPickerMsg(null);
    try {
      await axios.post('/api/discord/react', {
        channel_id: chId,
        message_id: String(msgId),
        emoji: encodeURIComponent(emoji)
      });
    } catch (e) {
      console.error('Error adding reaction:', e);
      alert('Failed to react: ' + (e.response?.data?.error || e.message));
    }
  };

  const handleDeleteMessage = async (entry) => {
    const chId = getChannelId(entry);
    const msgId = entry.message_id || entry.id;
    if (!chId || !msgId) { console.error('Missing channel or message ID for delete'); return; }
    if (!window.confirm('Delete this message from Discord?')) return;
    try {
      await axios.delete(`/api/discord/messages/${chId}/${msgId}`);
      setTimeout(fetchLiveMessages, 1000);
    } catch (e) {
      console.error('Error deleting message:', e);
      alert('Failed to delete: ' + (e.response?.data?.error || e.message));
    }
  };

  const fetchLogContent = async (filename) => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/logs/${filename}`);
      setLogContent(res.data);
      setSelectedLog(filename);
      setDisplayCount(50);
    } catch (e) { console.error('Error fetching log content:', e); }
    finally { setLoading(false); }
  };

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;
    setLoading(true);
    setActiveTab('search');
    try {
      const res = await axios.post('/api/search', { term: searchTerm, max_results: 200 });
      setSearchResults(res.data.results);
      setDisplayCount(50);
    } catch (e) { console.error('Error searching:', e); }
    finally { setLoading(false); }
  };

  const handleDownload = async (filename) => {
    try {
      const res = await axios.get(`/api/logs/${filename}/download`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename.replace('.json', '.txt'));
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (e) { console.error('Error downloading:', e); }
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
    } catch (e) { console.error('Error deleting:', e); }
  };

  // --- Helpers ---
  const formatTimestamp = (timestamp) => {
    try { return format(new Date(timestamp), 'MMM dd, yyyy HH:mm:ss'); }
    catch { return timestamp; }
  };

  const formatShortTime = (timestamp) => {
    try { return format(new Date(timestamp), 'HH:mm'); }
    catch { return ''; }
  };

  const getAvatarUrl = (entry) => {
    if (entry.avatar_url) return entry.avatar_url;
    const author = entry.author || entry.author_display || 'Unknown';
    const hash = author.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const colors = ['5865F2', '57F287', 'FEE75C', 'EB459E', 'ED4245', '3BA55D'];
    const color = colors[hash % colors.length];
    const initials = author.split('#')[0].substring(0, 2).toUpperCase();
    return `https://ui-avatars.com/api/?name=${initials}&background=${color}&color=fff&size=128`;
  };

  // --- Filtering ---
  const getDataForTab = useCallback(() => {
    if (activeTab === 'search') return searchResults;
    if (activeTab === 'live') return [...historyMessages, ...liveMessages];
    if (activeTab === 'stats') return [];
    return logContent;
  }, [activeTab, searchResults, liveMessages, historyMessages, logContent]);

  const filteredData = useCallback(() => {
    let data = getDataForTab();
    if (selectedChannel) {
      data = data.filter(e => e.channel === selectedChannel);
    }
    if (selectedUser) {
      data = data.filter(e => (e.author_display || e.author) === selectedUser);
    }
    if (filterType !== 'all') {
      data = data.filter(e => e.type === filterType);
    }
    return data;
  }, [getDataForTab, selectedChannel, selectedUser, filterType]);

  const allFiltered = filteredData();
  const displayedData = allFiltered.slice(Math.max(0, allFiltered.length - displayCount));
  const hasMore = allFiltered.length > displayCount;

  const scrollRestorationRef = useRef(null);

  // After React re-renders with new content, restore scroll position so it doesn't jump
  useEffect(() => {
    if (scrollRestorationRef.current && logEntriesRef.current) {
      const el = logEntriesRef.current;
      const { prevScrollHeight, prevScrollTop } = scrollRestorationRef.current;
      el.scrollTop = el.scrollHeight - prevScrollHeight + prevScrollTop;
      scrollRestorationRef.current = null;
    }
  }, [displayedData.length, historyMessages.length]);

  const handleScroll = (e) => {
    const el = e.target;
    const { scrollTop, scrollHeight, clientHeight } = el;
    // Track if user is near the bottom (within 150px)
    isNearBottomRef.current = scrollHeight - scrollTop - clientHeight < 150;
    // Load more displayed messages when scrolling near the top
    if (scrollTop < 300 && !loading) {
      if (hasMore) {
        scrollRestorationRef.current = { prevScrollHeight: el.scrollHeight, prevScrollTop: scrollTop };
        setDisplayCount(prev => prev + 50);
      } else if (activeTab === 'live' && historyHasMore && !loadingHistory) {
        scrollRestorationRef.current = { prevScrollHeight: el.scrollHeight, prevScrollTop: scrollTop };
        fetchHistory().then(() => {
          setDisplayCount(prev => prev + 200);
        });
      }
    }
  };

  // --- Render Message ---
  const renderMessage = (entry, index) => {
    const data = displayedData;
    const prev = index > 0 ? data[index - 1] : null;
    const isGroupStart = !prev || 
      prev.author !== entry.author ||
      prev.channel !== entry.channel ||
      (new Date(entry.created_at) - new Date(prev.created_at)) > 420000; // 7min gap

    const typeBadge = entry.type !== 'create' ? (
      <span className={`dc-type-badge dc-type-${entry.type}`}>
        {entry.type === 'edit' && <Pencil size={10} />}
        {entry.type === 'delete' && <Trash size={10} />}
        {entry.type}
      </span>
    ) : null;

    const msgUniqueId = entry.message_id || entry.id || index;
    const isHovered = hoveredMsgId === msgUniqueId;
    const pickerOpen = emojiPickerMsg && emojiPickerMsg.msgId === msgUniqueId;
    const canInteract = activeTab === 'live' && entry.type === 'create';

    return (
      <div 
        key={index} 
        className={`dc-message ${isGroupStart ? 'dc-group-start' : ''} ${entry.type === 'delete' ? 'dc-deleted' : ''}`}
        onMouseEnter={() => setHoveredMsgId(msgUniqueId)}
        onMouseLeave={() => { setHoveredMsgId(null); if (pickerOpen) setEmojiPickerMsg(null); }}
      >
        {/* Hover action buttons */}
        {isHovered && canInteract && (
          <div className="dc-msg-actions">
            <button title="Add Reaction" onClick={() => setEmojiPickerMsg(pickerOpen ? null : { msgId: msgUniqueId, entry })}>
              <SmilePlus size={16} />
            </button>
            <button title="Delete Message" className="dc-action-delete" onClick={() => handleDeleteMessage(entry)}>
              <Trash size={16} />
            </button>
          </div>
        )}

        {/* Emoji picker popup */}
        {pickerOpen && (
          <div className="dc-emoji-picker">
            {QUICK_EMOJIS.map(em => (
              <button key={em} className="dc-emoji-btn" onClick={() => handleReact(entry, em)}>{em}</button>
            ))}
          </div>
        )}

        {isGroupStart ? (
          <div className="dc-msg-avatar">
            <img src={getAvatarUrl(entry)} alt="" />
          </div>
        ) : (
          <div className="dc-msg-avatar-spacer">
            <span className="dc-msg-hover-time">{formatShortTime(entry.created_at)}</span>
          </div>
        )}
        <div className="dc-msg-body">
          {isGroupStart && (
            <div className="dc-msg-header">
              <span className="dc-msg-author" style={entry.role_color ? {color: entry.role_color} : {}}>
                {entry.author_display || entry.author}
              </span>
              {!selectedChannel && (
                <span className="dc-msg-channel" onClick={() => setSelectedChannel(entry.channel)}>
                  #{entry.channel}
                </span>
              )}
              <span className="dc-msg-time">{formatTimestamp(entry.created_at)}</span>
              {typeBadge}
            </div>
          )}

          {entry.reply_preview && (
            <div className="dc-reply">
              <div className="dc-reply-spine"></div>
              <img className="dc-reply-avatar" src={getAvatarUrl(entry.reply_preview)} alt="" />
              <span className="dc-reply-author">{entry.reply_preview.author}</span>
              <span className="dc-reply-text">{entry.reply_preview.content}</span>
            </div>
          )}

          {entry.type === 'edit' && entry.before ? (
            <div className="dc-edit-content">
              <div className="dc-edit-before">{entry.before}</div>
              <div className="dc-edit-after">{entry.content}</div>
            </div>
          ) : (
            <div className="dc-msg-text">{entry.content || '(no text)'}</div>
          )}

          {entry.attachments && entry.attachments.length > 0 && (
            <div className="dc-attachments">
              {entry.attachments.map((url, i) => {
                const isImage = /\.(gif|png|jpe?g|webp)(\?|$)/i.test(url);
                const isVideo = /\.(mp4|mov|webm)(\?|$)/i.test(url);
                if (isImage) return <div key={i} className="dc-attach-img"><img src={url} alt="" loading="lazy" /></div>;
                if (isVideo) return <div key={i} className="dc-attach-video"><video controls src={url} /></div>;
                const fname = url.split('/').pop().split('?')[0];
                return <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="dc-attach-file"><FileText size={16} />{fname}</a>;
              })}
            </div>
          )}

          {entry.reactions && Object.keys(entry.reactions).length > 0 && (
            <div className="dc-reactions">
              {Object.entries(entry.reactions).map(([emoji, info]) => (
                <div key={emoji} className="dc-reaction" onClick={() => handleReact(entry, emoji)}>
                  <span>{emoji}</span>
                  <span className="dc-reaction-count">{info.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // --- Render Stats Panel ---
  const renderStatsPanel = () => {
    if (!enhancedStats) return <div className="dc-loading"><RefreshCw className="spin" size={24} /> Loading stats...</div>;
    const s = enhancedStats;
    return (
      <div className="dc-stats-panel">
        <div className="dc-stats-grid">
          <div className="dc-stat-card">
            <div className="dc-stat-icon"><MessageSquare size={24} /></div>
            <div className="dc-stat-info">
              <div className="dc-stat-value">{s.total_messages?.toLocaleString()}</div>
              <div className="dc-stat-label">Messages</div>
            </div>
          </div>
          <div className="dc-stat-card">
            <div className="dc-stat-icon"><Pencil size={24} /></div>
            <div className="dc-stat-info">
              <div className="dc-stat-value">{s.total_edits?.toLocaleString()}</div>
              <div className="dc-stat-label">Edits</div>
            </div>
          </div>
          <div className="dc-stat-card">
            <div className="dc-stat-icon"><Trash size={24} /></div>
            <div className="dc-stat-info">
              <div className="dc-stat-value">{s.total_deletes?.toLocaleString()}</div>
              <div className="dc-stat-label">Deletes</div>
            </div>
          </div>
          <div className="dc-stat-card">
            <div className="dc-stat-icon"><FileText size={24} /></div>
            <div className="dc-stat-info">
              <div className="dc-stat-value">{s.total_logs}</div>
              <div className="dc-stat-label">Log Files</div>
            </div>
          </div>
        </div>

        <div className="dc-stats-row">
          <div className="dc-stats-section">
            <h3><TrendingUp size={16} /> Top Users</h3>
            <div className="dc-leaderboard">
              {s.top_users?.map((u, i) => (
                <div key={i} className="dc-lb-row" onClick={() => { setSelectedUser(u.name); setActiveTab('live'); }}>
                  <span className="dc-lb-rank">{i < 3 ? ['🥇','🥈','🥉'][i] : `#${i+1}`}</span>
                  <span className="dc-lb-name">{u.name}</span>
                  <span className="dc-lb-count">{u.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="dc-stats-section">
            <h3><Hash size={16} /> Top Channels</h3>
            <div className="dc-leaderboard">
              {s.top_channels?.map((c, i) => (
                <div key={i} className="dc-lb-row" onClick={() => { setSelectedChannel(c.name); setActiveTab('live'); }}>
                  <span className="dc-lb-rank">#{i+1}</span>
                  <span className="dc-lb-name">#{c.name}</span>
                  <span className="dc-lb-count">{c.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="dc-stats-section">
          <h3><Clock size={16} /> Hourly Activity (UTC)</h3>
          <div className="dc-activity-chart">
            {s.hourly_activity?.map((h) => {
              const max = Math.max(...s.hourly_activity.map(x => x.count), 1);
              return (
                <div key={h.hour} className="dc-bar-col">
                  <div className="dc-bar" style={{height: `${(h.count / max) * 100}%`}}></div>
                  <span className="dc-bar-label">{h.hour}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // --- Active Filters Bar ---
  const hasActiveFilters = selectedChannel || selectedUser || filterType !== 'all';

  return (
    <div className="dc-app">
      {/* Channel Sidebar */}
      <div className={`dc-sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="dc-sidebar-header">
          <h2>Bot Dashboard</h2>
          <button className="dc-collapse-btn" onClick={() => setSidebarCollapsed(!sidebarCollapsed)}>
            <ChevronDown size={16} style={{transform: sidebarCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)'}} />
          </button>
        </div>

        {!sidebarCollapsed && (
          <>
            {/* Navigation */}
            <div className="dc-nav-section">
              <button className={`dc-nav-item ${activeTab === 'live' ? 'active' : ''}`} onClick={() => { setActiveTab('live'); setSelectedChannel(null); }}>
                <Activity size={18} />
                <span>Live Feed</span>
                {liveMessages.length > 0 && <span className="dc-badge">{liveMessages.length}</span>}
              </button>
              <button className={`dc-nav-item ${activeTab === 'stats' ? 'active' : ''}`} onClick={() => setActiveTab('stats')}>
                <BarChart3 size={18} />
                <span>Statistics</span>
              </button>
              <button className={`dc-nav-item ${activeTab === 'search' ? 'active' : ''}`} onClick={() => setActiveTab('search')}>
                <Search size={18} />
                <span>Search</span>
              </button>
            </div>

            {/* Channels */}
            <div className="dc-section-header">
              <span>CHANNELS</span>
            </div>
            <div className="dc-channel-list">
              <button 
                className={`dc-channel-item ${!selectedChannel && activeTab === 'live' ? 'active' : ''}`}
                onClick={() => { setSelectedChannel(null); setActiveTab('live'); }}
              >
                <Hash size={16} />
                <span>all-channels</span>
              </button>
              {channels.slice(0, 20).map(ch => (
                <button 
                  key={ch.name}
                  className={`dc-channel-item ${selectedChannel === ch.name ? 'active' : ''}`}
                  onClick={() => { setSelectedChannel(ch.name); setActiveTab('live'); }}
                >
                  <Hash size={16} />
                  <span>{ch.name}</span>
                  <span className="dc-channel-count">{ch.message_count}</span>
                </button>
              ))}
            </div>

            {/* Log Files */}
            <div className="dc-section-header">
              <span>LOG FILES</span>
              <button onClick={fetchLogs} className="dc-section-action"><RefreshCw size={12} /></button>
            </div>
            <div className="dc-channel-list dc-log-files">
              {logs.map(log => (
                <div key={log.filename} className={`dc-channel-item dc-log-item ${selectedLog === log.filename ? 'active' : ''}`}>
                  <div className="dc-log-main" onClick={() => { fetchLogContent(log.filename); setActiveTab('logs'); }}>
                    <FileText size={16} />
                    <span>{log.is_custom ? '⭐ ' : ''}{log.name}</span>
                  </div>
                  <div className="dc-log-actions">
                    <button onClick={() => handleDownload(log.filename)} title="Download"><Download size={12} /></button>
                    {log.is_custom && <button onClick={() => handleDelete(log.name)} title="Delete" className="dc-delete"><Trash2 size={12} /></button>}
                  </div>
                </div>
              ))}
            </div>

          </>
        )}
      </div>

      {/* Main Content */}
      <div className="dc-main">
        {/* Top Bar */}
        <div className="dc-topbar">
          <div className="dc-topbar-left">
            <button className="dc-mobile-menu" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
              <Menu size={20} />
            </button>
            <Hash size={20} className="dc-topbar-hash" />
            <span className="dc-topbar-title">
              {activeTab === 'stats' ? 'Statistics' :
               activeTab === 'search' ? 'Search' :
               activeTab === 'logs' ? (selectedLog || 'Log Viewer') :
               selectedChannel ? selectedChannel : 'live-feed'}
            </span>
            {activeTab === 'live' && (
              <span className="dc-topbar-desc">Real-time messages from your Discord server</span>
            )}
          </div>
          <div className="dc-topbar-right">
            {/* Filter controls */}
            <div className="dc-filter-group">
              <select 
                value={filterType} 
                onChange={e => setFilterType(e.target.value)}
                className="dc-filter-select"
              >
                <option value="all">All Types</option>
                <option value="create">Messages</option>
                <option value="edit">Edits</option>
                <option value="delete">Deletes</option>
              </select>
            </div>
            <div className="dc-search-bar">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <button className="dc-topbar-btn" onClick={() => setShowUserPanel(!showUserPanel)} title="Members">
              <Users size={20} />
            </button>
          </div>
        </div>

        {/* Active filters bar */}
        {hasActiveFilters && (
          <div className="dc-filters-bar">
            {selectedChannel && (
              <span className="dc-filter-tag">
                <Hash size={12} /> {selectedChannel}
                <button onClick={() => setSelectedChannel(null)}><X size={12} /></button>
              </span>
            )}
            {selectedUser && (
              <span className="dc-filter-tag">
                <AtSign size={12} /> {selectedUser}
                <button onClick={() => setSelectedUser(null)}><X size={12} /></button>
              </span>
            )}
            {filterType !== 'all' && (
              <span className="dc-filter-tag">
                <Filter size={12} /> {filterType}
                <button onClick={() => setFilterType('all')}><X size={12} /></button>
              </span>
            )}
            <button className="dc-clear-filters" onClick={() => { setSelectedChannel(null); setSelectedUser(null); setFilterType('all'); }}>
              Clear all
            </button>
          </div>
        )}

        {/* Content */}
        <div className="dc-content-wrapper">
          <div className="dc-messages-col">
            <div className="dc-messages-area" ref={logEntriesRef} onScroll={handleScroll}>
              <div className="dc-messages-spacer">
                {loading && (
                  <div className="dc-loading"><RefreshCw className="spin" size={24} /> Loading...</div>
                )}

                {activeTab === 'stats' && renderStatsPanel()}

                {activeTab !== 'stats' && !loading && displayedData.length > 0 && (
                  <>
                    {loadingHistory && <div className="dc-loading-more"><RefreshCw className="spin" size={14} /> Loading older messages...</div>}
                    {!loadingHistory && hasMore && <div className="dc-loading-more">Scroll up for older messages...</div>}
                    {!loadingHistory && !hasMore && activeTab === 'live' && historyHasMore && <div className="dc-loading-more">Scroll up to load previous days...</div>}
                    {!loadingHistory && !hasMore && !historyHasMore && activeTab === 'live' && <div className="dc-loading-more" style={{color:'#4e5058'}}>Beginning of message history</div>}
                    <div className="dc-msg-count">{allFiltered.length.toLocaleString()} messages {hasActiveFilters ? '(filtered)' : ''}</div>
                    {displayedData.map((entry, i) => renderMessage(entry, i))}
                    <div ref={messagesEndRef} />
                  </>
                )}

                {activeTab !== 'stats' && !loading && displayedData.length === 0 && (
                  <div className="dc-empty">
                    {activeTab === 'logs' && !selectedLog ? (
                      <>
                        <FileText size={48} />
                        <h3>Select a log file</h3>
                        <p>Choose a log from the sidebar to view messages</p>
                      </>
                    ) : activeTab === 'search' && !searchTerm ? (
                      <>
                        <Search size={48} />
                        <h3>Search messages</h3>
                        <p>Enter a search term in the top bar</p>
                      </>
                    ) : (
                      <>
                        <MessageSquare size={48} />
                        <h3>No messages</h3>
                        <p>{hasActiveFilters ? 'No messages match your filters' : 'Waiting for messages...'}</p>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Message Input Bar */}
            {activeTab === 'live' && (() => {
              const resolvedId = sendChannelId || channelMap[selectedChannel] || null;
              const resolvedName = resolvedId
                ? (discordChannels.find(c => c.id === resolvedId)?.name || selectedChannel || 'channel')
                : null;
              return (
                <div className="dc-input-bar">
                  <div className="dc-input-channel-selector">
                    <select
                      value={resolvedId || ''}
                      onChange={(e) => setSendChannelId(e.target.value || null)}
                      className="dc-input-channel-select"
                    >
                      <option value="">{selectedChannel ? `#${selectedChannel}` : '— pick channel —'}</option>
                      {discordChannels.map(ch => (
                        <option key={ch.id} value={ch.id}>#{ch.name}</option>
                      ))}
                    </select>
                    <ChevronRight size={14} className="dc-input-arrow" />
                  </div>
                  <input
                    ref={messageInputRef}
                    className="dc-input-field"
                    placeholder={resolvedName ? `Message #${resolvedName}` : 'Select a channel to send messages...'}
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }}
                    disabled={sendingMessage || !resolvedId}
                  />
                  <button
                    className="dc-input-send"
                    onClick={handleSendMessage}
                    disabled={sendingMessage || !messageInput.trim() || !resolvedId}
                  >
                    <Send size={18} />
                  </button>
                </div>
              );
            })()}
          </div>

          {/* User Panel */}
          {showUserPanel && (
            <div className="dc-user-panel">
              <div className="dc-user-panel-header">
                <h3>Members — {users.length}</h3>
              </div>
              <div className="dc-user-list">
                <div 
                  className={`dc-user-item ${!selectedUser ? 'active' : ''}`}
                  onClick={() => setSelectedUser(null)}
                >
                  <div className="dc-user-avatar-wrap">
                    <Users size={16} />
                  </div>
                  <span className="dc-user-name">All Users</span>
                </div>
                {users.map(u => (
                  <div 
                    key={u.id}
                    className={`dc-user-item ${selectedUser === u.name ? 'active' : ''}`}
                    onClick={() => setSelectedUser(selectedUser === u.name ? null : u.name)}
                  >
                    <div className="dc-user-avatar-wrap">
                      <img src={u.avatar_url || `https://ui-avatars.com/api/?name=${u.name.substring(0,2)}&background=5865F2&color=fff&size=32`} alt="" />
                    </div>
                    <span className="dc-user-name">{u.name}</span>
                    <span className="dc-user-count">{u.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="dc-mobile-overlay" onClick={() => setMobileMenuOpen(false)}>
          <div className="dc-mobile-sidebar" onClick={e => e.stopPropagation()}>
            <div className="dc-sidebar-header">
              <h2>Navigation</h2>
              <button onClick={() => setMobileMenuOpen(false)}><X size={20} /></button>
            </div>
            <div className="dc-nav-section">
              <button className={`dc-nav-item ${activeTab === 'live' ? 'active' : ''}`} onClick={() => { setActiveTab('live'); setMobileMenuOpen(false); }}>
                <Activity size={18} /><span>Live Feed</span>
              </button>
              <button className={`dc-nav-item ${activeTab === 'stats' ? 'active' : ''}`} onClick={() => { setActiveTab('stats'); setMobileMenuOpen(false); }}>
                <BarChart3 size={18} /><span>Statistics</span>
              </button>
            </div>
            <div className="dc-section-header"><span>CHANNELS</span></div>
            <div className="dc-channel-list">
              {channels.slice(0, 15).map(ch => (
                <button key={ch.name} className={`dc-channel-item ${selectedChannel === ch.name ? 'active' : ''}`}
                  onClick={() => { setSelectedChannel(ch.name); setActiveTab('live'); setMobileMenuOpen(false); }}>
                  <Hash size={16} /><span>{ch.name}</span>
                </button>
              ))}
            </div>
            <div className="dc-section-header"><span>LOG FILES</span></div>
            <div className="dc-channel-list">
              {logs.map(log => (
                <button key={log.filename} className={`dc-channel-item ${selectedLog === log.filename ? 'active' : ''}`}
                  onClick={() => { fetchLogContent(log.filename); setActiveTab('logs'); setMobileMenuOpen(false); }}>
                  <FileText size={16} /><span>{log.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DiscordDashboard;
