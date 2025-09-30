import { Fragment } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import LiveCoderPage from "./pages/LiveCoder";
import AdminPage from "./pages/Admin";

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-full px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-teal-500 ${
          isActive ? "bg-teal-500 text-white shadow-soft" : "text-slate-600 hover:bg-slate-100"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 z-50">
        Skip to content
      </a>
      <header className="border-b border-slate-200 bg-white/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-xl font-semibold text-teal-500">
            AHS Billing Assistant
          </Link>
          <nav className="flex items-center gap-2">
            <NavItem to="/" label="Live Coder" />
            <NavItem to="/admin" label="Admin" />
          </nav>
        </div>
      </header>
      <main id="main" className="mx-auto flex max-w-6xl flex-1 flex-col gap-6 px-6 py-6">
        <Routes>
          <Route path="/" element={<LiveCoderPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </main>
    </div>
  );
}
