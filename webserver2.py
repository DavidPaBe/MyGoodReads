from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import uuid
import redis
import re

# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html

mappings = [
    (r"^/books?/(?P<book_id>\d+)$","get_book"),
    (r"^/$","index"),
    (r"^/search/$","search"),
]

#r = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)
r = redis.Redis()

class WebRequestHandler(BaseHTTPRequestHandler):
    @property
    def query_data(self):
        return dict(parse_qsl(self.url.query))
    
    @property
    def url(self):
        return urlparse(self.path)
    
    def search(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        index_page = f"<h1>{self.path}</h1>".encode("utf-8")
        self.wfile.write(index_page)
	
    def cookies(self):
        return SimpleCookie(self.headers.get("Cookie"))

    def get_session(self):
        cookies = self.cookies()
        return uuid.uuid4() if not cookies else cookies["session_id"].value
        
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie()
        cookies["session_id"] = session_id
        cookies["session_id"]["max-age"] = 1000
        self.send_header("Set-Cookie", cookies.output(header=""))
        
    def do_GET(self):
        if self.path.startswith("/search?q="):
            title = self.query_data.get("q", "")
            self.search_book(title)
        else:
            self.url_mapping_response()


        
    def url_mapping_response(self):
        for pattern, method in mappings:
            params = self.get_params(pattern, self.path)
            if params is not None:
                ad = getattr(self, method)
                ad(**params)
                return
        self.send_response(404)
        self.end_headers()
        self.wfile.write("Not Found".encode("utf-8"))
    
    def get_or_create_session(self):
	    cookies = self.cookies()
	    session_id = None
	    if not cookies:
	    	session_id = uuid.uuid4()
	    	cookies = SimpleCookie()
	    	cookies["session_id"] = session_id
	    	cookies["max_age"] = 1000
	    else:
	    	session_id = cookies["session_id"].value
	    return session_id
	
    def get_params(self, pattern, path):
        match = re.match(pattern, path)
        if match:
	        return match.groupdict()
		
    def index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        index_page = """
            <html>
            <head>
                <title>Biblioteca</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                        background-color: #f0f0f0;
                    }
                    h1 {
                        text-align: center;
                        color: #333;
                    }
                    form {
                        text-align: center;
                        margin-top: 50px;
                    }
                    input[type="text"] {
                        padding: 5px;
                        width: 300px;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        font-size: 16px;
                    }
                    input[type="submit"] {
                        padding: 5px 20px;
                        background-color: #007bff;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-size: 16px;
                        cursor: pointer;
                    }
                </style>
            </head>
            <body>
                <h1>Bienvenidos a la biblioteca!</h1>   
                <form action="/search" method="GET">
                    <label for="q">Buscar libros:</label>
                    <input type="text" name="q" placeholder="Ingrese el titulo del libro"/>
                    <input type="submit" value="Buscar"/>
                </form>
            </body>
            </html>
        """.encode("utf-8")
        self.wfile.write(index_page)

    def get_book(self,book_id):
        session_id = self.get_session()
        r.lpush(f"session:{session_id}",f"book:{book_id}")
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        self.end_headers()
        
        book_info = r.get(f"book:{book_id}") or "<h1> No existe el libro </h1>"
        book_info += f"Session ID:{session_id}".encode("utf-8")
        self.wfile.write(book_info)
        #self.wfile.write(str(book_info).encode("utf-8"))
        #self.wfile.write(f"session:{session_id}".encode("utf-8"))
        #book_list = r.lrange(f"session:{session_id}", 0, -1)
        books = r.lrange(f"session:{session_id}",0,-1)
        for book in books:
            decoded_book_id = book.decode("utf-8")
            self.wfile.write(f"<br>book:{book}".encode("utf-8"))
            
    def search_book(self, title):
        book_info_json = r.get(f"book:{title}")
        if book_info_json:
            book_info = json.loads(book_info_json)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
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


if __name__ == "__main__":
    print("Server starting ...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()

#print("Server starting...")
#server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
#server.serve_forever()
