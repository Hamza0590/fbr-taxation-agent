const Tweaks = ({ visible, values, onChange }) => {
  if (!visible) return null;
  return (
    <div className="tweaks-panel">
      <div className="tweaks-head">
        <span className="t">Tweaks</span>
      </div>
      <div className="tweaks-row">
        <span className="l">Theme</span>
        <div className="seg">
          <button className={values.theme === "light" ? "active" : ""} onClick={() => onChange({theme: "light"})}>Light</button>
          <button className={values.theme === "dark" ? "active" : ""} onClick={() => onChange({theme: "dark"})}>Dark</button>
        </div>
      </div>
      <div className="tweaks-row">
        <span className="l">Layout</span>
        <div className="seg">
          <button className={values.layout === "split" ? "active" : ""} onClick={() => onChange({layout: "split"})}>Split</button>
          <button className={values.layout === "stack" ? "active" : ""} onClick={() => onChange({layout: "stack"})}>Stacked</button>
        </div>
      </div>
      <div className="tweaks-row">
        <span className="l">Backend trace</span>
        <div className={`switch ${values.showTrace ? 'on' : ''}`} onClick={() => onChange({showTrace: !values.showTrace})}/>
      </div>
      <div className="tweaks-row">
        <span className="l">Density</span>
        <div className="seg">
          <button className={values.density === "comfortable" ? "active" : ""} onClick={() => onChange({density: "comfortable"})}>Comfy</button>
          <button className={values.density === "compact" ? "active" : ""} onClick={() => onChange({density: "compact"})}>Compact</button>
        </div>
      </div>
    </div>
  );
};
window.Tweaks = Tweaks;
