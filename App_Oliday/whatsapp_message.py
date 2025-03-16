from datetime import *

import pywhatkit

try:
    # Enviamos el mensaje
    ahora = datetime.now()
    enviar_a = ahora + timedelta(minutes=2)
    hora = enviar_a.hour
    minutos = enviar_a.minute

    pywhatkit.sendwhatmsg_instantly("+5491157986148",
                          "Oliday Estetica:: le recordamos que tienen turno xxxx",
                                    15, True, 3)
    pywhatkit.shutdown(3)

    pywhatkit.show_history()
    #pywhatkit.sendwhatmsg("+5491157986148",
    #                      "Mensaje De Prueba :: Oliday Estetica (va con 911 de prefijo)",
    #                      hora, minutos, 15, True, 2)

    print("Mensaje Enviado {}:{}".format(hora, minutos))

except EncodingWarning as e:
    print("[error] {}".format(e))