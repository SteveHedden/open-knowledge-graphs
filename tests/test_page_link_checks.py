import asyncio
import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_pages


class HomepageContentTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
