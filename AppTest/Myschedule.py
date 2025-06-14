import schedule


def mi_funcion():
    print("Ejecutando mi_funcion a las", datetime.now())

schedule.every(5).seconds.do(mi_funcion)

print(schedule.jobs)
