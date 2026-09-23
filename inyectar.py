import sqlite3

# Conectar a tu base de datos local
db = sqlite3.connect('ingectec.db')
cursor = db.cursor()

# Los productos exactos de la propuesta de la Javeriana
productos = [
    ("BREAKER 2X40", 101861, 100),
    ("TUBO EMT DE 1\" (INCLUYE ASCESORIOS DE INSTALACION)", 35547, 100)
]

# Inyectarlos en la tabla de inventario (inv)
for desc, precio, stock in productos:
    cursor.execute("INSERT OR REPLACE INTO inv (d, p, stock) VALUES (?, ?, ?)", (desc, precio, stock))

db.commit()
db.close()
print("¡Productos agregados con éxito a la bodega!")