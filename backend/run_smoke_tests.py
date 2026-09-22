"""Run the small backend suite used for ordinary pull requests."""

import unittest


SMOKE_TESTS = (
    "test_main.FireEndpointsTest.test_fires_passes_days_to_data_source",
    "test_main.FireEndpointsTest.test_fires_exposes_stale_cache_metadata",
    "test_main.FireEndpointsTest.test_expired_data_is_returned_when_nasa_is_unavailable",
    "test_incident_clustering.IncidentClusteringTest.test_incidents_endpoint_uses_requested_window",
    "test_rate_limit.ClientIdentityTest.test_uuid_is_replaced_by_a_secret_hmac_key",
    "test_rate_limit.AppCheckTest.test_cloud_mode_rejects_a_missing_token",
    "test_logging.CorsLoggingContractTest.test_request_id_header_is_allowed_and_exposed",
    "test_historical_ingest.HistoricalIngestionServiceTest.test_stale_nasa_data_is_never_written",
    "test_historical_ingest.BigQueryRepositoryTest.test_write_uses_parameters_and_one_transaction",
    "test_nasa_client.NasaClientTest.test_rejects_declared_oversized_payload",
)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromNames(SMOKE_TESTS)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
