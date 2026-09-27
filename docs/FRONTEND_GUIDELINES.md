# LexLink Frontend Architecture & Implementation Guidelines

This guide details the React 19 + TypeScript frontend implementation patterns, folder structures, component conventions, state management, and responsive CSS styling for **LexLink**.

---

## 📁 1. Frontend Directory Structure (`frontend/src/`)

```
frontend/src/
├── api/                   # Typed API clients & Axios interceptors
│   ├── client.ts          # Base Axios instance with JWT interceptors
│   ├── auth.ts            # Auth & verification API calls
│   ├── documents.ts       # Document upload & listing calls
│   ├── chat.ts            # Chat session & SSE streaming logic
│   ├── search.ts          # Vector & keyword search API
│   ├── highlights.ts      # Highlight annotations CRUD
│   └── notes.ts           # Sticky notes CRUD
│
├── components/            # Reusable UI component library (by feature)
│   ├── auth/              # LoginForm, SignupForm, RoleSelector
│   ├── documents/         # DocumentUpload, DocumentList, DocumentViewer
│   ├── highlights/        # HighlightOverlay, HighlightPanel
│   ├── notes/             # NoteModal, NotesList, StickyNotePin
│   ├── chat/              # ChatWindow, ChatMessage, SessionSelector, CitationPill
│   ├── search/            # SearchBar, FilterSidebar, SearchResultCard
│   ├── dictionary/        # DictionarySearch, TermDefinitionCard
│   ├── admin/             # TokenUsageChart, VerificationReviewQueue
│   └── common/            # Header, Sidebar, Button, Input, Modal, StatusBadge
│
├── pages/                 # Full-screen page views
│   ├── HomePage.tsx       # Landing & quick action dashboard
│   ├── LoginPage.tsx      # Auth entry point
│   ├── DashboardPage.tsx  # User hub (recent judgments, pinned cases)
│   ├── DocumentPage.tsx   # Split-screen PDF reader & annotation workspace
│   ├── SearchPage.tsx     # Semantic vector search & briefing grid
│   ├── DictionaryPage.tsx # Legal terminology & maxim search
│   └── AdminPage.tsx      # Platform telemetry & verification approval
│
├── hooks/                 # Custom React hooks
│   ├── useAuth.ts         # User session, JWT refresh, role verification
│   ├── useDocument.ts     # PDF rendering & bbox coordinate mapping
│   ├── useChat.ts         # SSE streaming & message management
│   ├── useSearch.ts       # Debounced vector search query execution
│   └── useHighlights.ts   # Local & persisted highlight state
│
├── theme/                 # Design tokens & color constants
│   └── theme.ts           # Sage green color tokens & stage definitions
│
├── assets/                # Static assets, SVG icons & stylesheets
│   └── styles/
│       └── globals.css    # Tailwind directives & custom scrollbars
│
├── App.tsx                # App root layout & routing
└── main.tsx               # DOM bootstrap
```

---

## 🔌 2. API Client with JWT Interceptors (`src/api/client.ts`)

```typescript
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// Request Interceptor: Attach Access Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("lexlink_access_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response Interceptor: Handle 401 Unauthorized & Token Refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshRes = await axios.post(
          `${API_BASE_URL}/api/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const newToken = refreshRes.data.access_token;
        localStorage.setItem("lexlink_access_token", newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        localStorage.removeItem("lexlink_access_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
```

---

## 📄 3. Split-Screen Document Workspace Pattern

The core workspace combines an interactive PDF reader with bounding-box highlights and a right-hand side contextual panel (RAG Chat, Sticky Notes, Key Citations):

```tsx
// src/pages/DocumentPage.tsx
import React, { useState } from "react";
import DocumentViewer from "../components/documents/DocumentViewer";
import HighlightPanel from "../components/highlights/HighlightPanel";
import ChatWindow from "../components/chat/ChatWindow";
import NotesList from "../components/notes/NotesList";

export default function DocumentPage({ documentId }: { documentId: string }) {
  const [activeTab, setActiveTab] = useState<"chat" | "highlights" | "notes">("chat");
  const [selectedBbox, setSelectedBbox] = useState<number[] | null>(null);

  return (
    <div className="flex h-screen bg-[#F8FAF8] overflow-hidden">
      {/* Left: Interactive PDF Reader with Highlight Overlays */}
      <div className="flex-1 border-r border-[#D4E8DC] overflow-y-auto custom-scrollbar p-6">
        <DocumentViewer 
          documentId={documentId} 
          highlightBbox={selectedBbox}
          onSelectText={(bbox) => setSelectedBbox(bbox)}
        />
      </div>

      {/* Right: Contextual Research Panel */}
      <div className="w-[480px] flex flex-col bg-white border-l border-[#D4E8DC]">
        {/* Tab Navigation */}
        <div className="flex border-b border-[#D4E8DC] px-4 pt-3 space-x-2">
          {(["chat", "highlights", "notes"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-3 text-sm font-medium border-b-2 capitalize transition-colors ${
                activeTab === tab
                  ? "border-[#7FA89A] text-[#1A1A1A]"
                  : "border-transparent text-[#52605B] hover:text-[#1A1A1A]"
              }`}
            >
              {tab === "chat" ? "AI Research" : tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden p-4">
          {activeTab === "chat" && <ChatWindow documentId={documentId} />}
          {activeTab === "highlights" && <HighlightPanel documentId={documentId} />}
          {activeTab === "notes" && <NotesList documentId={documentId} />}
        </div>
      </div>
    </div>
  );
}
```

---

## 🔍 4. Semantic Search & Briefing Grid Pattern

```tsx
// src/components/search/SearchBar.tsx
import React, { useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";

interface SearchBarProps {
  onSearch: (query: string, court: string) => void;
  isLoading?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState("");
  const [court, setCourt] = useState("all");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSearch(query, court);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-4xl mx-auto">
      <div className="flex items-center bg-white border border-[#D4E8DC] rounded-xl shadow-sm hover:border-[#7FA89A] focus-within:border-[#7FA89A] focus-within:ring-2 focus-within:ring-[#7FA89A]/20 transition-all p-2">
        <Search className="w-5 h-5 text-[#52605B] ml-3" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search legal precedents, ratios, case numbers, or legal principles..."
          className="flex-1 px-4 py-2 text-[#1A1A1A] placeholder-[#52605B] outline-none text-base bg-transparent"
        />
        <select
          value={court}
          onChange={(e) => setCourt(e.target.value)}
          aria-label="Filter by Court"
          className="text-sm text-[#52605B] bg-[#F8FAF8] border border-[#D4E8DC] rounded-lg px-3 py-1.5 mr-2 outline-none"
        >
          <option value="all">All Courts</option>
          <option value="supreme">Supreme Court</option>
          <option value="highcourt_lahore">Lahore High Court</option>
          <option value="highcourt_sindh">Sindh High Court</option>
        </select>
        <button
          type="submit"
          disabled={isLoading}
          className="bg-[#7FA89A] hover:bg-[#668F81] text-white px-5 py-2 rounded-lg font-medium text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {isLoading ? "Searching..." : "Search"}
        </button>
      </div>
    </form>
  );
};
```

---

## 📱 5. Responsive Design Standards & Breakpoints

- **Mobile (`< 640px`):** Single column stack, collapsible drawer sidebar, full-width modal dialogs.
- **Tablet (`640px - 1024px`):** Condensed sidebar, stacked document workspace with toggleable chat drawer.
- **Desktop (`> 1024px`):** Full persistent sidebar, split-screen PDF + AI assistant workspace.
- **Wide Screens (`> 1440px`):** 3-pane layout (Navigation + Document Viewer + Multi-Tab Research Hub).
