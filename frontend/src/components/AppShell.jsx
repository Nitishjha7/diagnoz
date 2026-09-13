import { NavLink } from "react-router-dom";
import Logo from "./Logo";
import { useAuth } from "../hooks/useAuth";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "⌂", end: true },
  { to: "/customer", label: "New Diagnosis", icon: "◉" },
  { to: "/dispatch", label: "Dispatch & Service", icon: "\u{1F69A}" },
  { to: "/technician", label: "Technician Console", icon: "\u{1F6E0}" },
];

function initials(name) {
  if (!name) return "?";
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default function AppShell({ children }) {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Logo />

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
            >
              <span className="icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-promo">
          <strong>Real Experts. Real Solutions.</strong>
          Right at home — fewer truck rolls, faster fixes, a greener tomorrow.
        </div>

        <div className="sidebar-user">
          <div className="sidebar-avatar">{initials(user?.full_name)}</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user?.full_name || "..."}</div>
            <div className="sidebar-user-role">{user?.role}</div>
          </div>
        </div>
        <button className="sidebar-logout" onClick={logout}>
          Logout
        </button>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-search">
            <input placeholder="Search sessions, appliances, or help..." />
          </div>
          <div className="topbar-right">
            <span>Smarter Diagnostics. A Greener Tomorrow.</span>
          </div>
        </header>

        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
