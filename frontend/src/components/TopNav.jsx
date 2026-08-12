import { NavLink } from "react-router-dom";
import { Upload, LayoutDashboard, MessageSquareText, FileDown } from "lucide-react";
import { useDataset } from "../DatasetContext";

function TopNav() {
  const { isReady, dataset } = useDataset();

  const navItems = [
    { to: "/", label: "Upload & Clean", icon: Upload, locked: false },
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, locked: !isReady },
    { to: "/ask", label: "Ask Your Data", icon: MessageSquareText, locked: !isReady },
    { to: "/export", label: "Export Report", icon: FileDown, locked: !isReady },
  ];

  return (
    <header className="topnav">
      <div className="topnav-left">
        <div className="logo-mark">#</div>
        <div>
          <h1 className="topnav-title">Data Analyst Agent</h1>
          <div className="pulse-line">
            <svg viewBox="0 0 120 14" preserveAspectRatio="none">
              <path className="pulse-path" d="M0,7 L18,7 L23,2 L28,12 L33,3 L38,10 L43,7 L70,7 L75,2 L80,12 L85,3 L90,10 L95,7 L120,7" />
            </svg>
          </div>
        </div>
      </div>

      <nav className="topnav-tabs">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `topnav-tab ${isActive ? "active" : ""} ${item.locked ? "locked" : ""}`}
              onClick={(e) => item.locked && e.preventDefault()}
            >
              <Icon size={15} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      <div className={`status-pill ${isReady ? "ready" : ""}`}>
        <span className="status-dot"></span>
        {isReady ? dataset.name : "No data"}
      </div>
    </header>
  );
}

export default TopNav;