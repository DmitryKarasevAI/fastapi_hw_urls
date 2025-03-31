import pytest
from datetime import datetime, timedelta
from fastapi import status
import uuid


@pytest.mark.anyio
async def test_check_cache(client):
    resp = await client.get("/links/check_cache")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


# Test: Successful link shortening by an authenticated user
@pytest.mark.anyio
async def test_shorten_link_success(authed_client):
    payload = {"full_url": "https://example.com", "custom_alias": "123"}
    resp = await authed_client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["short_url"] == "123"


# Test: Auto-generation of alias when none is provided
@pytest.mark.anyio
async def test_shorten_link_auto_alias(authed_client):
    payload = {"full_url": "https://example.com"}
    resp = await authed_client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["short_url"]) == 10


# Test: shorten URL with invalid expires_at format
@pytest.mark.anyio
async def test_shorten_link_invalid_expires_at(authed_client):
    payload = {"full_url": "https://example.com", "expires_at": "2024-99-99 99:99"}
    resp = await authed_client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# Test: shorten URL with valid expires_at
@pytest.mark.anyio
async def test_shorten_link_valid_expires_at(authed_client):
    future_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    payload = {"full_url": "https://example.com", "expires_at": future_time}
    resp = await authed_client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_200_OK


# Test: Duplicate alias rejection
@pytest.mark.anyio
async def test_shorten_link_duplicate_alias(authed_client):
    payload = {"full_url": "https://example.com/1", "custom_alias": "123"}
    resp1 = await authed_client.post("/links/shorten", json=payload)
    assert resp1.status_code == status.HTTP_200_OK

    payload2 = {"full_url": "https://example.com/2", "custom_alias": "123"}
    resp2 = await authed_client.post("/links/shorten", json=payload2)
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST


# Test: Invalid URL input
@pytest.mark.anyio
async def test_shorten_link_invalid_url(authed_client):
    payload = {"full_url": "not-a-valid-url"}
    resp = await authed_client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# Test: Anonymous link shortening
@pytest.mark.anyio
async def test_shorten_link_anonymous(client):
    payload = {"full_url": "https://example.com"}
    resp = await client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_200_OK


# Test: Successful redirection
@pytest.mark.anyio
async def test_redirect_success(authed_client):
    original_url = "https://www.wikipedia.org"
    create_payload = {"full_url": original_url, "custom_alias": "wiki"}
    create_resp = await authed_client.post("/links/shorten", json=create_payload)
    assert create_resp.status_code == status.HTTP_200_OK

    redirect_resp = await authed_client.get("/links/wiki", follow_redirects=False)
    assert redirect_resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert redirect_resp.headers["location"] == original_url


# Test: Redirection for non-existent alias
@pytest.mark.anyio
async def test_redirect_not_found(client):
    resp = await client.get("/links/nonexistent", follow_redirects=False)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# Test: Successful link deletion
@pytest.mark.anyio
async def test_delete_link_success(authed_client):
    payload = {"full_url": "https://delete.me", "custom_alias": "todelete"}
    create_resp = await authed_client.post("/links/shorten", json=payload)
    assert create_resp.status_code == status.HTTP_200_OK

    delete_resp = await authed_client.delete("/links/todelete")
    assert delete_resp.status_code == status.HTTP_200_OK

    check_resp = await authed_client.get("/links/todelete")
    assert check_resp.status_code == status.HTTP_404_NOT_FOUND


# Test: Successful link renaming
@pytest.mark.anyio
async def test_rename_link_success(authed_client):
    payload = {"full_url": "https://example.com", "custom_alias": "oldalias"}
    create_resp = await authed_client.post("/links/shorten", json=payload)
    assert create_resp.status_code == status.HTTP_200_OK

    rename_resp = await authed_client.put("/links/oldalias", params={"new_alias": "newalias"})
    assert rename_resp.status_code == status.HTTP_200_OK

    old_resp = await authed_client.get("/links/oldalias")
    assert old_resp.status_code == status.HTTP_404_NOT_FOUND

    new_resp = await authed_client.get("/links/newalias", follow_redirects=False)
    assert new_resp.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert new_resp.headers["location"] == "https://example.com"


# Test: shorten URL with invalid custom alias format
@pytest.mark.anyio
async def test_shorten_link_invalid_alias_format(authed_client):
    payload = {"full_url": "https://example.com", "custom_alias": "invalid alias!@#"}
    resp = await authed_client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# Test: shorten URL with invalid custom alias format
@pytest.mark.anyio
async def test_shorten_link_invalid_alias_format_anonymous(client):
    payload = {"full_url": "https://example.com", "custom_alias": "invalid alias!@#"}
    resp = await client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# Test: shorten URL that exceeds hashing attempts
@pytest.mark.anyio
async def test_shorten_link_exceed_hash_attempts(mocker, authed_client):
    fake_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    mocker.patch("uuid.uuid4", return_value=fake_uuid)  # Mock UUID to always generate the same hash

    payload = {"full_url": "https://example.com"}
    resp1 = await authed_client.post("/links/shorten", json=payload)
    assert resp1.status_code == status.HTTP_200_OK

    # The next request will attempt to generate the same hash and fail after 3 attempts
    resp2 = await authed_client.post("/links/shorten", json=payload)
    assert resp2.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# Test: Redirecting expired URL
@pytest.mark.anyio
async def test_redirect_expired_url(authed_client):
    expired_time = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    payload = {"full_url": "https://example.com/expired", "custom_alias": "expired", "expires_at": expired_time}
    resp = await authed_client.post("/links/shorten", json=payload)
    assert resp.status_code == status.HTTP_200_OK

    redirect_resp = await authed_client.get("/links/expired", follow_redirects=False)
    assert redirect_resp.status_code == status.HTTP_404_NOT_FOUND


# Test: Unauthorized deletion attempt
@pytest.mark.anyio
async def test_delete_link_unauthorized(client):
    resp = await client.delete("/links/somealias")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED or resp.status_code == status.HTTP_403_FORBIDDEN


# Test: Deleting link that doesn't exist
@pytest.mark.anyio
async def test_delete_link_not_exist(authed_client):
    resp = await authed_client.delete("/links/nonexistent")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# Test: Renaming link to an existing alias
@pytest.mark.anyio
async def test_rename_link_duplicate_alias(authed_client):
    payload1 = {"full_url": "https://example.com", "custom_alias": "alias1"}
    payload2 = {"full_url": "https://example.org", "custom_alias": "alias2"}

    resp1 = await authed_client.post("/links/shorten", json=payload1)
    assert resp1.status_code == status.HTTP_200_OK

    resp2 = await authed_client.post("/links/shorten", json=payload2)
    assert resp2.status_code == status.HTTP_200_OK

    rename_resp = await authed_client.put("/links/alias2", params={"new_alias": "alias1"})
    assert rename_resp.status_code == status.HTTP_400_BAD_REQUEST


# Test: Get link statistics for non-existent link
@pytest.mark.anyio
async def test_get_link_stats_nonexistent(authed_client):
    resp = await authed_client.get("/links/nonexistent/stats")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# Test: Get expired link stats with no expired links
@pytest.mark.anyio
async def test_get_expired_links_stats_empty(authed_client):
    resp = await authed_client.get("/links/expired/stats")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []


# Test: Get expired link stats with expired links
@pytest.mark.anyio
async def test_get_expired_links_stats(authed_client):
    payload = {"full_url": "https://example.com", "custom_alias": "123", "expires_at": "1970-01-01 00:00"}

    resp1 = await authed_client.post("/links/shorten", json=payload)
    assert resp1.status_code == status.HTTP_200_OK

    resp2 = await authed_client.get("/links/expired/stats")
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json() != []


# Test: Searching correct link
@pytest.mark.anyio
async def test_search_correct_link(authed_client):
    payload1 = {"full_url": "https://example.com", "custom_alias": "123"}

    resp = await authed_client.post("/links/shorten", json=payload1)
    assert resp.status_code == status.HTTP_200_OK

    params = {"full_url": "https://example.com"}

    rename_resp = await authed_client.get("/links/search", params=params)
    assert rename_resp.status_code == status.HTTP_200_OK


# Test: Searching incorrect link
@pytest.mark.anyio
async def test_search_incorrect_link(authed_client):
    params = {"full_url": "https://example.com"}

    rename_resp = await authed_client.get("/links/search", params=params)
    assert rename_resp.status_code == status.HTTP_404_NOT_FOUND


# Test: Successful link renaming with no new_alias
@pytest.mark.anyio
async def test_rename_link_success_no_alias(authed_client):
    payload = {"full_url": "https://example.com", "custom_alias": "oldalias"}
    create_resp = await authed_client.post("/links/shorten", json=payload)
    assert create_resp.status_code == status.HTTP_200_OK

    rename_resp = await authed_client.put("/links/oldalias", params={"new_alias": None})
    assert rename_resp.status_code == status.HTTP_200_OK

    old_resp = await authed_client.get("/links/oldalias")
    assert old_resp.status_code == status.HTTP_404_NOT_FOUND


# Test: Check incorrect values for renaming
@pytest.mark.anyio
async def test_rename_link_incorrect_input(authed_client, client):

    payload1 = {"full_url": "https://example.com", "custom_alias": "123"}
    create_resp = await authed_client.post("/links/shorten", json=payload1)
    assert create_resp.status_code == status.HTTP_200_OK

    rename_resp = await client.put("/links/123", params={"new_alias": "123"})
    assert rename_resp.status_code == status.HTTP_403_FORBIDDEN

    payload2 = {"full_url": "https://example.com", "custom_alias": "321"}
    create_resp = await client.post("/links/shorten", json=payload2)
    assert create_resp.status_code == status.HTTP_200_OK

    rename_resp = await authed_client.put("/links/321", params={"new_alias": None})
    assert rename_resp.status_code == status.HTTP_403_FORBIDDEN


# Test: Get link statistics for existing link
@pytest.mark.anyio
async def test_get_link_stats_existing(authed_client):

    payload = {"full_url": "https://example.com", "custom_alias": "123"}
    create_resp = await authed_client.post("/links/shorten", json=payload)
    assert create_resp.status_code == status.HTTP_200_OK

    resp = await authed_client.get("/links/123/stats")
    assert resp.status_code == status.HTTP_200_OK


# Test: Check auth
@pytest.mark.anyio
async def test_registering(client):

    payload1 = {
                "email": "user@example.com",
                "password": "string",
                "is_active": "true",
                "is_superuser": "false",
                "is_verified": "false"
            }
    create_resp = await client.post("/auth/register", json=payload1)
    assert create_resp.status_code == status.HTTP_201_CREATED
