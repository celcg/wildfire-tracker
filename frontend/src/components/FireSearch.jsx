import { useState } from "react";
import { describeFireSearchFilters, isSupportedSearchPlace } from "../domain/fireSearch.js";
import { interpretFireSearch } from "../services/fireApi.js";

export function FireSearch({ activeFilters, onApply, onClear }) {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    const candidate = question.trim();
    if (candidate.length < 3) {
      setStatus({ kind: "error", text: "Describe the observations you want to find." });
      return;
    }

    setLoading(true);
    setStatus(null);
    try {
      const { data } = await interpretFireSearch({ question: candidate });
      if (data.status === "emergency_advice") {
        setStatus({
          kind: "warning",
          text: "This map cannot advise on evacuation or personal safety. Follow instructions from local emergency services.",
        });
      } else if (data.status === "unsupported") {
        setStatus({
          kind: "error",
          text: "That request cannot be translated into the available map filters. Try a time window, FRP, confidence, severity, or persistence.",
        });
      } else if (!isSupportedSearchPlace(data.filters.place)) {
        setStatus({
          kind: "error",
          text: "That place is not available yet. Galicia is currently supported as a named area.",
        });
      } else {
        onApply(data.filters);
        setStatus({ kind: "success", text: "Filters applied to the map and observation log." });
      }
    } catch (error) {
      const wait = error?.retryAfterSeconds;
      setStatus({
        kind: "error",
        text: wait
          ? `Automated search is limited. Try again in ${wait} seconds.`
          : "Automated search is temporarily unavailable. Manual controls still work.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="fire-search" aria-labelledby="fire-search-title">
      <div className="fire-search-copy">
        <h2 id="fire-search-title">Search observations</h2>
        <p>Describe filters in Spanish or English. Interpretation is automated and may be wrong.</p>
      </div>
      <form onSubmit={submit} className="fire-search-form">
        <label htmlFor="fire-search-question" className="sr-only">Search question</label>
        <input
          id="fire-search-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={240}
          placeholder="Persistent clusters near Galicia since yesterday"
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="6.5" />
            <path d="m16 16 4 4" />
          </svg>
          {loading ? "Interpreting" : "Apply search"}
        </button>
      </form>
      {activeFilters ? (
        <div className="fire-search-filters" aria-label="Applied search filters">
          {describeFireSearchFilters(activeFilters).map((description) => (
            <span key={description}>{description}</span>
          ))}
          <button type="button" onClick={onClear}>Clear search</button>
        </div>
      ) : null}
      {status ? (
        <p className={`fire-search-status is-${status.kind}`} role={status.kind === "error" ? "alert" : "status"}>
          {status.text}
        </p>
      ) : null}
    </section>
  );
}
