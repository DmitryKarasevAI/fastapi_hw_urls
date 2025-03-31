from locust import HttpUser, task, between
import random


class LinkShortenerUser(HttpUser):
    wait_time = between(1, 5)

    @task(2)
    def create_short_link(self):
        long_url = f"https://example.com/test/{random.randint(1, 1000000)}"
        payload = {"full_url": long_url}
        with self.client.post("/links/shorten", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Failed to create link")

    @task(1)
    def get_link_stats(self):
        long_url = f"https://example.com/stats/{random.randint(1, 1000000)}"
        payload = {"full_url": long_url}
        with self.client.post("/links/shorten", json=payload, catch_response=True) as create_response:
            if create_response.status_code == 200:
                data = create_response.json()
                short_url = data.get("short_url")
                if short_url:
                    self.client.get(f"/links/{short_url}/stats")
            else:
                create_response.failure("Failed to create link")

    @task(1)
    def test_redirect(self):
        long_url = f"https://example.com/redirect/{random.randint(1, 1000000)}"
        payload = {"full_url": long_url}
        with self.client.post("/links/shorten", json=payload, catch_response=True) as create_response:
            if create_response.status_code == 200:
                data = create_response.json()
                short_url = data.get("short_url")
                if short_url:
                    self.client.get(f"/links/{short_url}", allow_redirects=False)
            else:
                create_response.failure("Failed to create link")
