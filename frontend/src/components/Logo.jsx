export default function Logo({ withTagline = true, size = 28 }) {
  return (
    <div className="brand">
      <svg
        className="brand-mark"
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="diagnoz-pulse" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#2563eb" />
            <stop offset="1" stopColor="#7c3aed" />
          </linearGradient>
        </defs>
        <path
          d="M2 17h5l2.5-9 5 18 3-13 2 4h10.5"
          stroke="url(#diagnoz-pulse)"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>
      <div>
        <div className="brand-name">
          Diagno<span className="z-accent">Z</span>
        </div>
        {withTagline && <div className="brand-tagline">See it. Solve it. Sooner.</div>}
      </div>
    </div>
  );
}
