import { NavLink } from 'react-router';

export default function Navbar() {
  const navClass = ({ isActive }: { isActive: boolean }) =>
    `nav-item${isActive ? ' active' : ''}`;

  return (
    <header className="topbar">
      <div className="flex items-center gap-3">
        <div className="logo">
          Intelli<span>Supply</span>
        </div>
        <nav className="nav">
          <NavLink to="/overview" className={navClass}>
            Overview
          </NavLink>
          <NavLink to="/inventory" className={navClass}>
            Inventory
          </NavLink>
          <NavLink to="/routes" className={navClass}>
            Routes
          </NavLink>
          <NavLink to="/copilot" className={navClass}>
            Copilot
          </NavLink>
        </nav>
      </div>
      <div className="topbar-right">
        <span className="pill">V2.1 MVP</span>
        <span className="pill dark">Admin</span>
      </div>
    </header>
  );
}
