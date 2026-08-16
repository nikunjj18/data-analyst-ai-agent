import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { DatasetProvider } from "./DatasetContext";
import TopNav from "./components/TopNav";
import UploadData from "./pages/UploadData";
import Dashboard from "./pages/Dashboard";
import AskData from "./pages/AskData";
import ExportReport from "./pages/ExportReport";
import "./App.css";

function AppShell() {
  const location = useLocation();
  const isAskPage = location.pathname === "/ask";

  return (
    <div className="app-shell">
      <TopNav />
      <main className={isAskPage ? "page-body-full" : "page-body"}>
        <Routes>
          <Route path="/" element={<UploadData />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/ask" element={<AskData />} />
          <Route path="/export" element={<ExportReport />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <DatasetProvider>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </DatasetProvider>
  );
}

export default App;