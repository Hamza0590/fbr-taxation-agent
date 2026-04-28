const CalendarModal = ({ onClose }) => (
  <div className="modal-backdrop" onClick={onClose}>
    <div className="modal" onClick={e => e.stopPropagation()}>
      <div className="modal-head">
        <h2>Tax calendar — Pakistan</h2>
        <span className="chip" style={{marginRight:10}}><span className="dot"/>4 upcoming</span>
        <button className="close-x" onClick={onClose}><Icon name="close" size={16}/></button>
      </div>
      <div className="modal-body">
        {CALENDAR.map((c, i) => (
          <div key={i} className={`cal-item ${c.status === 'due-soon' ? 'due-soon' : c.status === 'overdue' ? 'overdue' : ''}`}>
            <div className="cal-date">
              <div className="d">{c.date}</div>
              <div className="m">{c.month}</div>
            </div>
            <div>
              <div className="title">{c.title}</div>
              <div className="sub">{c.sub}</div>
            </div>
            <div className={`status ${c.status === 'ok' || c.status === 'filed' ? 'ok' : ''}`}>{c.statusText}</div>
          </div>
        ))}
        <div style={{marginTop:18, fontSize:12, color:"var(--ink-3)", fontFamily:"var(--mono)"}}>
          Reminders email at T-14, T-3, T-0. Configure in Profile.
        </div>
      </div>
    </div>
  </div>
);

window.CalendarModal = CalendarModal;
