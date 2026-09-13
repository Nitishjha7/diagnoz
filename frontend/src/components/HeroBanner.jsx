const PILLS = [
  { icon: "\u{1F3A4}", label: "Voice AI Triage" },
  { icon: "\u{1F4F9}", label: "Live Video Support" },
  { icon: "\u{1F464}", label: "Expert Technicians On-Demand" },
  { icon: "\u{1F69A}", label: "Fewer Truck Rolls" },
  { icon: "\u{1F343}", label: "Happier, Greener Homes" },
];

export default function HeroBanner() {
  return (
    <div className="hero-banner">
      <div className="hero-banner-left">
        <h1>DiagnoZ</h1>
        <p>
          Real-time video tele-diagnostic, voice AI triage &amp; field service dispatch.
          Diagnose faster, dispatch smarter, keep life running.
        </p>
        <div className="hero-pills">
          {PILLS.map((pill) => (
            <span key={pill.label} className="hero-pill">
              <span>{pill.icon}</span> {pill.label}
            </span>
          ))}
        </div>
      </div>
      <div className="hero-stat">
        <div className="hero-stat-value">35&ndash;45%</div>
        <div className="hero-stat-label">fewer unnecessary technician visits</div>
      </div>
    </div>
  );
}
