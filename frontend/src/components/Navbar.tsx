import { NavLink } from 'react-router-dom';

export function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo">⚡</span>
        <span className="navbar-title">CivicPulse</span>
      </div>
      <div className="navbar-links">
        <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Submit
        </NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Dashboard
        </NavLink>
        <NavLink to="/stats" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Stats
        </NavLink>
      </div>
    </nav>
  );
}
