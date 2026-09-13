import heroBanner from "../assets/brand/hero-banner.png";

export default function HeroBanner() {
  return (
    <div className="hero-banner">
      <img src={heroBanner} alt="DiagnoZ — from household issues to happier homes" className="hero-banner-img" />
      <div className="hero-stat hero-stat-overlay">
        <div className="hero-stat-value">35&ndash;45%</div>
        <div className="hero-stat-label">fewer unnecessary technician visits</div>
      </div>
    </div>
  );
}
