import { useState } from "react";
import Sidebar from "./components/common/Sidebar";
import TopBar from "./components/common/TopBar";
import Footer from "./components/common/Footer";
import DocumentIngestion from "./pages/DocumentIngestion";
import Dashboard from "./pages/Dashboard";
import AuthPage from "./pages/AuthPage";
import { AuthProvider } from "./context/AuthContext";

export default function App() {
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState("Document Ingestion");

  const handleLoginSuccess = (role: string) => {
    if (role === "admin") {
      setActiveTab("Dashboard");
    } else {
      setActiveTab("Document Ingestion");
    }
  };

  return (
    <AuthProvider>
      <div className="flex min-h-screen bg-slate-50">
        {/* Sidebar only shown on regular console pages */}
        {activeTab !== "Auth" && (
          <Sidebar activeLabel={activeTab} onNavigate={setActiveTab} />
        )}

        <div className="flex-1 flex flex-col justify-between min-w-0">
          <div>
            {activeTab !== "Auth" && (
              <TopBar
                searchValue={search}
                onSearchChange={setSearch}
                onNavigateToAuth={() => setActiveTab("Auth")}
              />
            )}
            <main>
              {activeTab === "Auth" ? (
                <AuthPage onLoginSuccess={handleLoginSuccess} />
              ) : activeTab === "Dashboard" ? (
                <Dashboard onNavigateToIngestion={() => setActiveTab("Document Ingestion")} />
              ) : (
                <DocumentIngestion />
              )}
            </main>
          </div>

          {activeTab !== "Auth" && <Footer />}
        </div>
      </div>
    </AuthProvider>
  );
}