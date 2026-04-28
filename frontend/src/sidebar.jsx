const Sidebar = ({ user, sessions, currentSessionId, onSelectSession, onDeleteSession, onNew, onNav, activeNav, onLogout, onProfile }) => {
  const [confirmDelete, setConfirmDelete] = React.useState(null);

  const handleDelete = (e, id) => {
    e.stopPropagation();
    if (confirmDelete === id) {
      onDeleteSession && onDeleteSession(id);
      setConfirmDelete(null);
    } else {
      setConfirmDelete(id);
      setTimeout(() => setConfirmDelete(null), 2500);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="lm">TS</div>
          <span>Tax Sathi</span>
        </div>
        <span className="chip"><span className="dot"/>TY 25-26</span>
      </div>

      <button className="new-chat-btn" onClick={onNew}>
        <span className="plus"><Icon name="plus" size={14} /></span>
        New question
      </button>

      <div className="nav-group">
        <button className={`nav-item ${activeNav === 'chat' ? 'active' : ''}`} onClick={() => onNav('chat')}>
          <Icon name="chat" size={15} /> Ask
        </button>
        <button className={`nav-item ${activeNav === 'calendar' ? 'active' : ''}`} onClick={() => onNav('calendar')}>
          <Icon name="calendar" size={15} /> Tax calendar
          <span className="count">4</span>
        </button>
        <button className={`nav-item ${activeNav === 'profile' ? 'active' : ''}`} onClick={() => onNav('profile')}>
          <Icon name="user" size={15} /> Profile &amp; context
        </button>
      </div>

      <div className="history">
        {(!sessions || sessions.length === 0) && (
          <div style={{padding:"12px 16px", color:"var(--ink-4)", fontSize:12}}>No sessions yet</div>
        )}
        {(sessions || []).map(s => (
          <div
            key={s.id}
            className={`history-item ${currentSessionId === s.id ? 'active' : ''}`}
            style={{display:"flex", alignItems:"center", gap:4}}
          >
            <button
              style={{flex:1, background:"none", border:"none", padding:"6px 8px", textAlign:"left", cursor:"pointer", minWidth:0}}
              onClick={() => onSelectSession(s.id)}
            >
              <span className="t" style={{display:"block", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"}}>{s.title}</span>
              {s.last_message_preview && (
                <span className="m" style={{display:"block", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"}}>
                  {s.last_message_preview.slice(0, 45)}
                </span>
              )}
            </button>
            <button
              className="icon"
              title={confirmDelete === s.id ? "Click again to confirm" : "Delete session"}
              style={{flexShrink:0, color: confirmDelete === s.id ? "var(--rose)" : undefined}}
              onClick={(e) => handleDelete(e, s.id)}
            >
              <Icon name="close" size={12}/>
            </button>
          </div>
        ))}
      </div>

      <div className="sidebar-user">
        <div className="avatar">{user.initials}</div>
        <div style={{flex: 1, minWidth: 0}}>
          <div className="name" style={{whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{user.name}</div>
          <div className="email" style={{whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{user.filerStatus} · NTN {user.ntn}</div>
        </div>
        <button className="icon" onClick={onProfile} title="Settings"><Icon name="settings" size={14} /></button>
        <button className="icon" onClick={onLogout} title="Log out"><Icon name="logout" size={14} /></button>
      </div>
    </aside>
  );
};
window.Sidebar = Sidebar;
