import "leaflet/dist/leaflet.css";
import "./App.css";
import { ControlDeck } from "./components/ControlDeck";
import { FireMap } from "./components/FireMap";
import { Hero } from "./components/Hero";
import { useFireData } from "./hooks/useFireData";
import { useScrollReveal } from "./hooks/useScrollReveal";

function App() {
  useScrollReveal();

  // App composes feature sections; networking and browser APIs stay in hooks.
  const {
    days,
    error,
    fires,
    lastUpdated,
    loading,
    refresh,
    selectDays,
  } = useFireData();

  return (
    <main className="app-shell">
      <Hero />

      <ControlDeck
        days={days}
        detectionCount={fires.length}
        lastUpdated={lastUpdated}
        loading={loading}
        onDaysChange={selectDays}
        onRefresh={refresh}
      />

      {error ? (
        <p className="error" role="alert">
          <span aria-hidden="true">!</span>
          {error}
        </p>
      ) : null}

      <FireMap fires={fires} />

      <footer className="site-footer">
        <span>Environmental intelligence through open data</span>
        <span>Data source · NASA FIRMS</span>
      </footer>
    </main>
  );
}

export default App;
