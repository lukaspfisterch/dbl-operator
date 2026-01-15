from __future__ import annotations

import os
import httpx
from unittest.mock import patch

import pytest
from dbl_operator.app_cli import _build_client
from dbl_operator.gateway_client import FakeGatewayClient
from dbl_operator.http_gateway_client import HttpGatewayClient


def test_build_client_defaults_to_fake() -> None:
    with patch.dict(os.environ, {}, clear=True):
        client = _build_client()
        assert isinstance(client, FakeGatewayClient)


def test_build_client_selects_http_when_base_url_set() -> None:
    with patch.dict(os.environ, {"DBL_GATEWAY_BASE_URL": "http://localhost:8010"}, clear=True), \
         patch.object(HttpGatewayClient, "check_capabilities"):
        client = _build_client()
        assert isinstance(client, HttpGatewayClient)
        assert client.base_url == "http://localhost:8010"
        assert client.token is None


def test_build_client_respects_token_and_timeout() -> None:
    env = {
        "DBL_GATEWAY_BASE_URL": "http://localhost:8010",
        "DBL_GATEWAY_TOKEN": "secret-token",
        "DBL_GATEWAY_TIMEOUT_SECS": "30.0",
    }
    with patch.dict(os.environ, env, clear=True), \
         patch.object(HttpGatewayClient, "check_capabilities"):
        client = _build_client()
        assert isinstance(client, HttpGatewayClient)
        assert client.token == "secret-token"
        assert client.timeout == 30.0


@pytest.mark.integration
def test_http_client_connection_error() -> None:
    """This test requires an actual gateway or a mock server, but here we just check it doesn't crash on init."""
    client = HttpGatewayClient(base_url="http://invalid.local")
    assert client.base_url == "http://invalid.local"


def test_fake_client_returns_empty_results() -> None:
    client = FakeGatewayClient()
    assert client.get_timeline("t") == ()
    assert client.get_decision("t", "1") is None
    assert client.get_audit("t") == ()
    assert client.get_audit("t", turn_id="1") == ()


def test_http_client_check_capabilities_map_shape() -> None:
    client = HttpGatewayClient(base_url="http://localhost:8010")
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value.json.return_value = {
            "interface_version": 2,
            "surfaces": {
                "snapshot": True, 
                "ingress_intent": True, 
                "capabilities": True,
                "tail": True
            }
        }
        mock_get.return_value.status_code = 200
        client.check_capabilities() # Should not raise


def test_http_client_check_capabilities_list_shape() -> None:
    client = HttpGatewayClient(base_url="http://localhost:8010")
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value.json.return_value = {
            "interface_version": 2,
            "surfaces": ["snapshot", "ingress_intent", "capabilities", "tail"]
        }
        mock_get.return_value.status_code = 200
        client.check_capabilities() # Should not raise


def test_http_client_check_capabilities_missing_tail() -> None:
    client = HttpGatewayClient(base_url="http://localhost:8010")
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value.json.return_value = {
            "interface_version": 2,
            "surfaces": ["snapshot", "ingress_intent", "capabilities"] # Missing tail
        }
        mock_get.return_value.status_code = 200
        with pytest.raises(RuntimeError, match=r"missing required surfaces: \['tail'\]"):
            client.check_capabilities()


def test_http_client_check_capabilities_mismatch() -> None:
    client = HttpGatewayClient(base_url="http://localhost:8010")
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value.json.return_value = {
            "interface_version": 1,
            "surfaces": ["snapshot", "ingress_intent", "capabilities", "tail"]
        }
        mock_get.return_value.status_code = 200
        with pytest.raises(RuntimeError, match="Gateway interface mismatch"):
            client.check_capabilities()


def test_http_client_no_heuristics_in_timeline_mapping() -> None:
    client = HttpGatewayClient(base_url="http://localhost:8010")
    
    # Mocking snapshot response
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value.json.return_value = {
            "events": [
                {
                    "index": 1,
                    "kind": "DECISION",
                    "thread_id": "t",
                    "turn_id": "1",
                    "parent_turn_id": None,
                    "digest": "d1",
                    "payload": {"context_digest": "c1"}
                }
            ]
        }
        mock_get.return_value.status_code = 200
        
        summaries = client.get_timeline("t")
        assert len(summaries) == 1
        assert summaries[0].turn_id == "1"
        assert summaries[0].execution_status is None
        assert summaries[0].context_digest == "c1"
        assert summaries[0].decision_digest == "d1"


def test_http_client_send_intent_mandatory_cid() -> None:
    from dbl_operator.domain_types import IntentEnvelope, Anchors
    client = HttpGatewayClient(base_url="http://localhost:8010")
    envelope = IntentEnvelope(
        anchors=Anchors("t", "1", None),
        intent_type="test",
        payload={},
        context_spec=None
    )
    
    with patch.object(httpx.Client, "post") as mock_post:
        mock_post.return_value.json.return_value = {"correlation_id": "fixed-id"}
        mock_post.return_value.status_code = 202
        
        client.send_intent(envelope, correlation_id="manual-id")
        
        # Check call arguments
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["correlation_id"] == "manual-id"


def test_http_client_get_audit_derivation() -> None:
    client = HttpGatewayClient(base_url="http://localhost:8010")
    
    with patch.object(httpx.Client, "get") as mock_get:
        mock_get.return_value.json.return_value = {
            "events": [
                {
                    "index": 1,
                    "kind": "DECISION",
                    "thread_id": "t",
                    "turn_id": "1",
                    "digest": "d1",
                    "payload": {}
                }
            ]
        }
        mock_get.return_value.status_code = 200
        
        audit = client.get_audit("t")
        assert len(audit) == 1
        assert audit[0].event_digest == "d1"
