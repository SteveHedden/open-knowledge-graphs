import asyncio
import contextlib
import io
import sys
import unittest
from unittest import mock
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_pages


class HomepageContentTests(unittest.TestCase):
    def test_wiki_missing_link_tooltip_is_not_a_missing_homepage(self):
        body = ('<html><title>MIAPA</title><h1>MIAPA</h1>'
                '<p>Minimum information about a phylogenetic analysis. '
                'Ontology documentation and downloads.</p>'
                '<a class="new" title="Phylotastic I (page does not exist)" '
                'href="/w/index.php?title=Phylotastic_I&amp;redlink=1">Phylotastic I</a></html>')
        self.assertTrue(generate_pages.usable_homepage_content(body, "text/html"))
        missing = body.replace('<h1>MIAPA</h1>', '<h1>This page does not exist</h1>')
        self.assertFalse(generate_pages.usable_homepage_content(missing, "text/html"))

    def test_visible_error_text_remains_rejected(self):
        for message in ('Page not found', '404 not found', 'This page has been removed'):
            body = '<title>' + message + '</title><p>' + 'Try another address. ' * 20 + '</p>'
            self.assertFalse(generate_pages.usable_homepage_content(body, "text/html"))

    def test_valid_turtle_can_mention_parked_domains_and_missing_pages(self):
        body = '''@prefix ex: <https://example.org/> .
# An unrelated service is now a parked domain; its page does not exist.
ex:ontology ex:description "Documentation mentions buy this domain as an example." .
'''
        for content_type, url in (
            ("text/turtle; charset=utf-8", "https://example.org/ontology"),
            ("text/plain", "https://example.org/ontology.ttl"),
        ):
            with self.subTest(content_type=content_type):
                self.assertTrue(generate_pages.usable_homepage_content(body, content_type, url))

    def test_rdf_url_or_content_type_does_not_hide_real_error_pages(self):
        for body in (
            "<html><h1>Buy this domain</h1>" + "Domain parking. " * 20 + "</html>",
            "<html><h1>Page not found</h1>" + "Try another page. " * 20 + "</html>",
        ):
            for content_type in ("text/html", "text/turtle", "text/plain"):
                with self.subTest(content_type=content_type, body=body[:40]):
                    self.assertFalse(generate_pages.usable_homepage_content(
                        body, content_type, "https://example.org/ontology.ttl"))

    def test_ordinary_html_and_empty_responses_keep_existing_behavior(self):
        self.assertTrue(generate_pages.usable_homepage_content(
            "<html>Ontology documentation and download links. " * 10, "text/html"))
        self.assertFalse(generate_pages.usable_homepage_content("", "text/turtle"))


class HomepageHeaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_large_headers_preserve_content_checks_and_bounded_limit(self):
        async def respond(reader, writer):
            request = await reader.readuntil(b"\r\n\r\n")
            path = request.split(b" ")[1]
            size = 70000 if path == b"/oversized" else 12000
            body = b"A substantive classification homepage. " * 20
            if path == b"/soft404":
                body = b"Page not found. " * 20
            elif path == b"/parked":
                body = b"Buy this domain. " * 20
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Security-Policy: "
                + b"x" * size
                + b"\r\nContent-Length: " + str(len(body)).encode()
                + b"\r\nConnection: close\r\n\r\n" + body
            )
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(respond, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            base = f"http://127.0.0.1:{port}"
            items = [{"homepage": base + path} for path in
                     ("/valid", "/soft404", "/parked", "/oversized")]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                accepted = await generate_pages.check_links(items)
        self.assertEqual(accepted, {base + "/valid"})
        self.assertIn("Link check failed: " + base + "/oversized", output.getvalue())
        self.assertIn("ClientResponseError", output.getvalue())


class HomepageRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_failures_retry_but_dead_pages_stay_excluded(self):
        counts = Counter()

        async def respond(reader, writer):
            request = await reader.readuntil(b"\r\n\r\n")
            path = request.split(b" ")[1].decode()
            counts[path] += 1
            status = 200
            if path in ("/rate-recover", "/server-recover") and counts[path] == 1:
                status = 429 if path == "/rate-recover" else 503
            elif path == "/rate-block":
                status = 429
            elif path in ("/challenge", "/known-broken-challenge"):
                status = 202
            elif path == "/forbidden":
                status = 403
            elif path == "/missing":
                status = 404
            elif path == "/server-down":
                status = 503
            body = b"Substantive resource documentation. " * 20
            if path == "/soft404":
                body = b"Page not found. " * 20
            if path == "/slow-recover" and counts[path] == 1:
                await asyncio.sleep(0.08)
            if path == "/timeout":
                await asyncio.sleep(0.2)
            extra = "x-amzn-waf-action: challenge\r\n" if status == 202 else ""
            writer.write(f"HTTP/1.1 {status} Response\r\n{extra}Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body)
            try:
                await writer.drain()
            except ConnectionError:
                pass
            finally:
                writer.close()

        server = await asyncio.start_server(respond, "127.0.0.1", 0)
        async with server:
            base = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            paths = ["/rate-recover", "/server-recover", "/rate-block", "/missing", "/server-down", "/soft404", "/slow-recover", "/timeout", "/challenge", "/known-broken-challenge", "/forbidden"]
            output = io.StringIO()
            with mock.patch.object(generate_pages, "LINK_TIMEOUTS", (0.05, 0.1, 0.15)), contextlib.redirect_stdout(output):
                health = {base + path: {"status": "unavailable"} for path in ("/rate-recover", "/known-broken-challenge")}
                accepted = await generate_pages.check_links([{"homepage": base + p} for p in paths], health)
        self.assertEqual(accepted, {base + p for p in ("/rate-recover", "/server-recover", "/rate-block", "/slow-recover", "/challenge", "/forbidden")})
        self.assertEqual(health[base + "/challenge"]["status"], "restricted")
        self.assertEqual(health[base + "/known-broken-challenge"]["status"], "unavailable")
        self.assertEqual(health[base + "/missing"]["status"], "unavailable")
        self.assertEqual(health[base + "/timeout"]["status"], "unavailable")
        self.assertEqual(health[base + "/rate-block"]["status"], "restricted")
        self.assertEqual(health[base + "/rate-recover"]["status"], "available")
        self.assertEqual(counts["/missing"], 1)
        self.assertEqual(counts["/soft404"], 1)
        self.assertEqual(counts["/rate-block"], 3)
        self.assertEqual(counts["/server-down"], 3)
        self.assertIn("Homepage access restricted: " + base + "/rate-block", output.getvalue())
        self.assertIn("Link check failed: " + base + "/timeout", output.getvalue())


if __name__ == "__main__":
    unittest.main()
