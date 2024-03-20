from functools import cached_property
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import uuid
import redis
import re
import json
import os


def load_html(filename):
    with open(filename, "r") as file:
        return file.read()

def agregar_book(nombre, genero, descripcion, link_imagen):
    id_book = obtener_ultimo_id() + 1
    book = {
        "id": id_book,
        "nombre": nombre,
        "genero": genero,
        "descripcion": descripcion,
        "link_imagen": link_imagen
    }
    r.set(f"book:{id_book}", json.dumps(book))
    incrementar_ultimo_id()

def obtener_ultimo_id():
    # Obtener el último ID utilizado
    ultimo_id = r.get("ultimo_id") or b"0"
    return int(ultimo_id)

def incrementar_ultimo_id():
    # Incrementar el último ID utilizado
    r.incr("ultimo_id")


mappings = [
    (r"^/books?/(?P<book_id>\d+)$","get_book"),
    (r"^/$","index"),
    (r"^/search/$","search"),
    (r"^/show_all_books", "show_all_books"),
    (r"/add_book$", "add_book"),
    (r"^/search_all$", "search_books_by_title"),
]

styles = """
<style>
    body {
        font-family: Arial, sans-serif;
        background-color: #f9f9f9;
        margin: 0;
        padding: 0 5%;
    }
    
    .container {
        max-width: 800px;
        margin: 20px auto;
        padding: 20px;
        background-color: #fff;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        border-radius: 5px;
    }
    
    h1 {
        color: #333;
        text-align: center;
    }
    
    .book {
        display: flex;
        margin-bottom: 20px;
        border-bottom: 1px solid #ddd;
        padding-bottom: 20px;
    }
    
    .book img {
        max-width: 200px;
        max-height: 200px;
        margin-left: auto;
    }
    
    .book-details {
        flex: 1;
        padding-right: 20px;
    }
    
    .book-details a {
        text-decoration: none;
        color: #0000FF;
        font-weight: bold;
    }
    
    .book-details p {
        margin: 5px 0;
        line-height: 1.4;
    }
    
    .genre {
        color: #666;
    }
    
    .button {
        display: inline-block;
        padding: 10px 20px;
        background-color: #333;
        color: #fff;
        text-decoration: none;
        border-radius: 5px;
        transition: background-color 0.3s ease;
    }
    .button:hover {
        background-color: #555;
    }
    .button-container {
        text-align: center;
        position: absolute;
        left: 20px;
        top: 20px;
    }
</style>
"""

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

    def do_GET(self):
        if 'session' not in self.url.query:
            referer = self.headers.get('Referer')
            
            if referer:
                print(referer)
                query_string = urlparse(referer).query
                # Analizar la cadena de consulta en un diccionario de parámetros
                query_params = parse_qsl(query_string)
                # Obtener el valor del parámetro 'session', si está presente
                
                session_param = None
                for key, value in query_params:
                    if key == 'session':
                        session_param = value
                        break
                
                if session_param is not None:
                    session_id = session_param
                else:
                    session_id = str(uuid.uuid4())
            else:
                session_id = str(uuid.uuid4())
            
            if '?' in self.path:
                self.path += f"&session={session_id}"
            else:
                self.path += f"?session={session_id}"
            self.send_response(302)
            self.send_header('Location', self.path)
            self.end_headers()
            return
    
        if self.path == "/":
            self.index()
        elif self.path.startswith("/add_book"):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("add_book.html", "r") as file:
                content = file.read()
            self.wfile.write(content.encode("utf-8"))
        elif self.path.startswith("/search?q="):
            title = self.query_data.get("q", "")
            session_id = self.query_data.get("session", "")
            self.search_book(title, session_id)
        elif self.path.startswith("/search_all?q="):
            query = urlparse(self.path).query
            title = self.query_data.get("q", "")
            self.search_books_by_title(title)
        elif self.path.startswith("/show_all_books"):
            self.show_all_books()
        else:
            self.index()

    
    def do_POST(self):
        if self.path.startswith("/add_book"):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            post_params = dict(parse_qsl(post_data.decode('utf-8')))
            
            nombre = post_params.get("nombre", "")
            genero = post_params.get("genero", "")
            descripcion = post_params.get("descripcion", "")
            link_imagen = post_params.get("link_imagen", "")
            
            agregar_book(nombre, genero, descripcion, link_imagen)
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write((styles + """<meta charset=\"UTF-8\"><h1>Libro agregado exitosamente</h1>
                <div class="button-container">
                    <a href="/" class="button">Regresar al índice</a>
                </div>""").encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write("Not Found".encode("utf-8"))
    
    def get_params(self, pattern, path):
        match = re.match(pattern, path)
        if match:
            return match.groupdict()
        
    def index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        index_page = load_html("index.html")
        self.wfile.write(index_page.encode("utf-8"))
            
    def search_book(self, title, session_id):
        r.lpush(f"session:{session_id}", f"book:{title}")
        book_info_json = r.get(f"book:{title}")
        if book_info_json:
            book_info = json.loads(book_info_json)
            with open("book_details.html", "r") as file:
                html_content = file.read()
            formatted_html = html_content.format(
                nombre=book_info["nombre"],
                id=book_info["id"],
                genero=book_info["genero"],
                descripcion=book_info["descripcion"],
                link_imagen=book_info["link_imagen"]
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(formatted_html.encode("utf-8"))
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

    def search_books_by_title(self, title):
        books = r.keys("book:*")
        if books:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            book_list_html = """
            <meta charset=\"UTF-8\">
            <br />
            <h1>Lista de libros</h1>
            <div class="button-container">
                <a href="/" class="button">Regresar al índice</a>
            </div>
            """
            
            for book_key in books:
                book_info_json = r.get(book_key)
                book_info = json.loads(book_info_json)
                if title.lower() in book_info['nombre'].lower():
                    book_list_html += f"""
                        <div class="book container">
                            <div class="book-details">
                                <p><strong>Nombre:</strong><a href="/search?q={book_info['id']}">{book_info['nombre']}</a></p>
                                <p><strong>Género:</strong> {book_info['genero']}</p>
                            </div>
                            <div class="book-image">
                                <img src="{book_info['link_imagen']}">
                            </div>
                        </div>
                        """
            self.wfile.write((styles+book_list_html).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write("<h1>No hay libros en la base de datos</h1>".encode("utf-8"))
            
    def show_all_books(self):
        books = r.keys("book:*")
        if books:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            # Encabezado
            book_list_html = """
            <meta charset=\"UTF-8\">
            <br />
            <h1>Lista de libros</h1>
            <div class="button-container">
                <a href="/" class="button">Regresar al índice</a>
            </div>"""
            
            # Contenido de la lista
            for book_key in books:
                book_info_json = r.get(book_key)
                book_info = json.loads(book_info_json)
                book_list_html += f"""
                <div class="book container">
                    <div class="book-details">
                        <p><strong>Nombre:</strong><a href="/search?q={book_info['id']}">{book_info['nombre']}</a></p>
                        <p><strong>Género:</strong> {book_info['genero']}</p>
                    </div>
                    <div class="book-image">
                        <img src="{book_info['link_imagen']}">
                    </div>
                </div>
                """
            
            self.wfile.write((styles + book_list_html).encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write("<h1>No hay libros en la base de datos</h1>".encode("utf-8"))

if __name__ == "__main__":
    print("Server starting ...")
    server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
    server.serve_forever()