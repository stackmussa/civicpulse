import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { ErrorBoundary } from './components/ErrorBoundary';
import { SubmitPage } from './pages/SubmitPage';
import { DashboardPage } from './pages/DashboardPage';
import { StatsPage } from './pages/StatsPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <div className="app-container">
          <Navbar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<SubmitPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/stats" element={<StatsPage />} />
            </Routes>
          </main>
        </div>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
