import redis
import json

# Conexión a la base de datos Redis
r = redis.Redis()

def obtener_ultimo_id():
    # Obtener el último ID utilizado
    ultimo_id = r.get("ultimo_id") or b"0"
    return int(ultimo_id)

def incrementar_ultimo_id():
    # Incrementar el último ID utilizado
    r.incr("ultimo_id")
    
def ver_libros():
    books = r.keys("*")
    if books:
        for book in books:
            print(f"Título: {book.decode()}, ID: {r.get(book).decode()}")
    else:
        print("No hay libros en la base de datos.")
        
def obtener_book(id_book):
    book_json = r.get(f"book:{id_book}")
    if book_json:
        book = json.loads(book_json)
        print(f"ID: {book['id']}")
        print(f"Nombre: {book['nombre']}")
        print(f"Genero: {book['genero']}")
        print(f"Descripción: {book['descripcion']}")
        print(f"Link de la Imagen: {book['link_imagen']}")
    else:
        print("Book no encontrado")

def agregar_book(nombre, genero, descripcion, link_imagen):
    # Obtener el último ID y generar el nuevo ID sumando uno
    id_book = obtener_ultimo_id() + 1
    # Crear un diccionario con los datos del book
    book = {
        "id": id_book,
        "nombre": nombre,
        "genero": genero,
        "descripcion": descripcion,
        "link_imagen": link_imagen
    }
    # Convertir el diccionario a JSON y almacenarlo en Redis
    r.set(f"book:{id_book}", json.dumps(book))
    # Actualizar el último ID utilizado
    incrementar_ultimo_id()

def borrar_book(id_book):
    if r.exists(f"book:{id_book}"):
        r.delete(f"book:{id_book}")
        print(f"Book borrado: {id_book}")
    else:
        print(f"El book '{id_book}' no existe en la base de datos.")

while True:
    print("\n--- Menú ---")
    print("1. Ver books")
    print("2. Añadir book")
    print("3. Borrar book")
    print("4. Buscar por ID")
    print("5. Salir")
    opcion = input("Seleccione una opción: ")

    if opcion == "1":
        ver_libros()
    elif opcion == "2":
        nombre = input("Ingrese el titulo del book: ")
        genero = input("Ingrese el genero del book: ")
        descripcion = input("Ingrese la descripcion del book: ")
        link_imagen = input("Ingrese el link de la imagen del book: ")
        agregar_book(nombre, genero, descripcion, link_imagen)
    elif opcion == "3":
        id_book = input("Ingrese el ID del book a borrar: ")
        borrar_book(id_book)
    elif opcion == "4":
        id_book = input("Ingrese el ID del book que quiere buscar: ")
        obtener_book(id_book)
    elif opcion == "5":
        break
    else:
        print("Opción no válida. Por favor, seleccione una opción válida.")
