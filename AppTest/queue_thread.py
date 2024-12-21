import threading
import queue
import time

def producer(q):
    for i in range(5):
        print(f'Produciendo {i}')
        q.put(i)
        time.sleep(1)

def consumer(q):
    while True:
        item = q.get()
        if item is None:
            break
        print(f'Consumiendo {item}')
        q.task_done()

# Crear una cola
q = queue.Queue()

# Crear hilos de productor y consumidor
producer_thread = threading.Thread(target=producer, args=(q,))
consumer_thread = threading.Thread(target=consumer, args=(q,))

# Iniciar los hilos
producer_thread.start()
consumer_thread.start()

# Esperar a que el productor termine
producer_thread.join()

# Colocar None en la cola para detener el consumidor
q.put(None)

# Esperar a que el consumidor termine
consumer_thread.join()

print("Proceso completado")
