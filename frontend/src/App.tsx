import { useState } from "react";
import Sidebar from "./components/common/Sidebar";
import TopBar from "./components/common/TopBar";
import Footer from "./components/common/Footer";
import DocumentIngestion from "./pages/DocumentIngestion";

export default function App() {
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState("Document Ingestion");

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar activeLabel={activeTab} onNavigate={setActiveTab} />

      <div className="flex-1 flex flex-col justify-between min-w-0">
        <div>
          <TopBar searchValue={search} onSearchChange={setSearch} />
          <main>
            <DocumentIngestion />
          </main>
        </div>

        <Footer />
      </div>
    </div>
  );
}