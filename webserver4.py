import redis
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
from http.cookies import SimpleCookie

# Conexión a la base de datos Redis
r = redis.Redis()

class WebRequestHandler(BaseHTTPRequestHandler):
    @property
    def query_data(self):
        return dict(parse_qsl(self.url.query))
    
    @property
    def url(self):
        return urlparse(self.path)

    def do_GET(self):
        if self.path.startswith("/search?q="):
            query = self.query_data.get("q", "")
            try:
                query = int(query)
            except ValueError:
                pass
            self.search_book(query)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write("Not Found".encode("utf-8"))

    def search_book(self, query):
        book_info_json = r.get(f"book:{query}")
        if book_info_json:
            book_info = json.loads(book_info_json)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_cookies()
            self.end_headers()
            book_details = f"""
            <html>
            <head>
                <title>Detalles del libro</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f0f0f0;
                    }}
                    h1 {{
                        color: #333;
                    }}
                    p {{
                        margin-bottom: 10px;
                    }}
                    img {{
                        max-width: 200px;
                        max-height: 200px;
                    }}
                </style>
            </head>
            <body>
                <h1>Detalles del libro:</h1>
                <p><strong>Nombre:</strong> {book_info['nombre']}</p>
                <p><strong>ID:</strong> {book_info['id']}</p>
                <p><strong>Descripción:</strong> {book_info['descripcion']}</p>
                <p><strong>Link de la Imagen:</strong> <img src="{book_info['link_imagen']}"></p>
            </body>
            </html>
            """.encode("utf-8")
            self.wfile.write(book_details)
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            not_found_message = """
            <html>
            <head>
                <title>Resultado de búsqueda</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f0f0f0;
                    }
                    h1 {
                        color: #333;
                    }
                </style>
            </head>
            <body>
                <h1>Libro no encontrado</h1>
            </body>
            </html>
            """.encode("utf-8")
            self.wfile.write(not_found_message)

    def send_cookies(self):
        cookies = self.cookies()
        if "session_id" not in cookies:
            session_id = uuid.uuid4()
            self.write_session_cookie(session_id)
        else:
            session_id = cookies["session_id"].value
        self.send_header("Set-Cookie", f"session_id={session_id}; Max-Age=3600; HttpOnly")

    def cookies(self):
        raw_cookie = self.headers.get("Cookie")
        if raw_cookie:
            return SimpleCookie(raw_cookie)
        return SimpleCookie()

    def write_session_cookie(self, session_id):
        self.send_header("Set-Cookie", f"session_id={session_id}; Max-Age=3600; HttpOnly")

if __name__ == "__main__":
    print("Server starting ...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()
