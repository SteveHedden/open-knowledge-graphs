import asyncio
import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_pages


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
