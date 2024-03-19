from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
from http.cookies import SimpleCookie

import redis
import uuid
import re

# Código basado en:
# https://realpython.com/python-http-server/
# https://docs.python.org/3/library/http.server.html
# https://docs.python.org/3/library/http.cookies.html

mappings = [ 
    (r"^/$books/(?P<book_id>\d+)$", "get_book"),
    (r"^/$book/(?P<book_id>\d+)$", "get_book"),
    (r"^/$", "index" ),
    (r"^/search", "search")
    ]

r = redis.StrictRedis(host="localhost", port = 6379, db = 0)

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
        return SimpleCookie(self.headers.get('Cookie'))
    
    def get_session(self):
        cookies = self.cookies()
        return uuid.uuid4() if not cookies else cookies["session_id"].value
   
    def get_or_create_session(self):
        cookies = self.cookies()
        session_id = None
        if not cookies:
            session_id = uuid.uuid4()
        else:
            session_id = cookies["session_id"].value
        return session_id
                
    def write_session_cookie(self, session_id):
        cookies = SimpleCookie()
        cookies["session_id"] = session_id
        cookies["session_id"]["max.age"] = 1000
        self.send_header("Set-Cookie", cookies.output(header=""))
        
    def do_GET(self):
        self.url_mapping_response()
    
    def url_mapping_response(self):
        for (pattern, method) in mappings:
            match = self.get_params(pattern, self.path)
            if match is not None:
                nd = getattr(self, method)
                nd(**match)
                return
        
        self.send_response(404)
        self.end_headers()
        self.wfile.write("Not Found").encode("utf-8")
    
    def get_params(self, pattern, path):
        match = re.match(pattern, path)
        if match:
            return match.groupdict()
        
    def index(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        index_page = f"""
        <h1> Bienvenido a los Libros </h1>
        <form action="/search" method="GET" >
            <label for="q">Search </label>
            <input type="text" name="q" />
            <input type="submit" value="Buscar libros" />
        </form>
        """.encode("utf-8")
        self.wfile.write(index_page) 
        
    def get_book(self, book_id):
        session_id = self.get_session()
        r.lpush(f"session:{session_id}", f"book:{book_id}")
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.write_session_cookie(session_id)
        self.end_headers()
        
        book_info = r.get(book_id) or "No existe el libro".encode("utf-8")
        #self.wfile.write(book_info).encode("utf-8")
        # self.wfile.write(f"session:{session_id}".encode("utf-8"))
        book_info += f"session:{session_id}".encode("utf-8") #Borrar linea si falla
        self.wfile.write(f"book:{book_info}").encode("utf-8")

        book_list = r.lrange(f"Session:{session_id}", 0, -1)
        
        for book in book_list:
            decoded_bookID = book.decode("utf-8")
            self.wfile.write(f"Book:{decoded_bookID}".encode("utf-8"))


print("Server starting...")
server = HTTPServer(("0.0.0.0", 8000), WebRequestHandler)
server.serve_forever()
