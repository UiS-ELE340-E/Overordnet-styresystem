# --------------------------------------------------------------------------
# Metode for aa gi ut int-verdien til eit hexadesimalt teikn i ASCII-format
# --------------------------------------------------------------------------
def hexascii2int(hex_teikn):
    if '0' <= hex_teikn <= '9':
        return (int(ord(hex_teikn) - 48))  # ASCII-koden for '0' er 0x30 = 48
    elif 'A' <= hex_teikn <= 'F':
        return (int(ord(hex_teikn) - 55))  # ASCII-koden for 'A' er 0x41 = 65
    

#-------------------------------------------------------------------------
# Kode for ein traad som les serieporten konfigurert i hovudtraaden main.
# Lesinga startar naar traaden faar ein 'k'(koeyr) via ein kommandokoe og
# stansar naar traaden faar ein 's' og etterpaa les meldingshalen ETX.
# Alle mottatte teikn blir lagt inn i ei meldingsliste.
# Serieporten blir stengt til slutt.
#-------------------------------------------------------------------------


def seriekomm(serieport, kommando_koe, meldingar):  # Innhald i traaden
    try:
        ny_kommando = kommando_koe.get()  # Vil henga til han faar foerste kommandoen
    except Exception:
        pass  # Ignorer, men kvitter ut evt. unntak som oppstaar.

    tilstand = ny_kommando
    tidteller=0
    hextall=[]
    #    x_verdi=[]
    verdi=0



    while tilstand == 'k':  # Saa lenge ein vil k(oeyra logging)

        #		while serieport.inWaiting() > 0:
        data = raakode_gui_metoder.serieport.read(21)
        
        print_bytes(data)
        
        # teikn = str(serieport.read(1), encoding='utf-8')  # Les eitt teikn.  #KT La til convert til str
        
                                                          # Vil blokkera/henga til det er kome noko aa lesa
        teikn=0
        meldingar.append(teikn)
        if teikn == 'X':
            tidteller=4
        if tidteller>0:
            tidteller=tidteller-1
            
            if teikn != 'X':
                hextall.append(teikn)
            if len(hextall)==3:
                verdi=256*hexascii2int(hextall[0])+16*hexascii2int(hextall[1])+hexascii2int(hextall[2])
                if verdi >= 32768:
                    
                    kommando_status.maaleverdi = verdi-65536
                    print(kommando_status.maaleverdi)
                else:
                    
                    kommando_status.maaleverdi = verdi
                    print(kommando_status.maaleverdi)

    
                
                hextall=[]
                



        try:
            ny_kommando = kommando_koe.get(block=False)  # Her skal ein ikkje henga/blokkera
        except Exception:  # men bare sjekka om det er kome ny kommando
            pass  # Her faar ein eit"Empty"-unntak kvar gong ein les ein tom koe. Dette skal
        # ignorerast, men kvitterast ut.

        if ny_kommando == 's':
            tilstand = ny_kommando  # Stans logging men fullfoer lesing t.o.m meldingshalen ETX

    while teikn != '\xF0':  # Heilt til og med meldingshalen ETX
        #		while serieport.inWaiting() > 0:
        teikn = str(serieport.read(1), encoding='utf-8')  # Les eitt teikn. #KT La til convert til str
        meldingar.append(teikn)

    serieport.close()  # Steng ned
    print(serieport.name, 'er stengt')




#-------------------------------------------------------------------------------------
# Hovudtraad (main).
# Denne opnar loggefil, kommandokoe, serieport og startar serietraaden.
# Saa vil traaden venta paa koeyr-kommando fraa tastaturet. Han vil saa gi melding via
# ein brukarkommandokoe til serietraaden om aa starta logging og til mikrokontrolleren
# om aa starta maalingane og sending av filtrerte X-, Y-, Z-data med tidsreferanse.
# Saa vil han venta paa stoppkommando fraa tastaturet. Etter aa ha faatt denne vil han
# gi melding til serietraaden og saa mikrokontrolleren om aa stoppa. Serietraaden vil
# daa halda fram til han les meldingshalen ETX.

# Serietraaden vil skriva ut heile meldinga og vil saa laga raae (dvs. uskalerte) tids-
# og akselerasjonslister som blir skrivne ut.
# Saa blir det laga skalerte lister samt lister for absolutt akselerasjon samt stamp-
# og rullvinkel. Alt dette blir saa plotta til slutt.
#-------------------------------------------------------------------------------------
def main():
    kommando = '0'
    fileName = 'logg.txt'
    f = open(fileName, 'r+')

    uC_meldingar = []
    brukarkommandoar = queue.Queue()

    connected = True
    #port = 'COM13'
    #baud = 115200  # 9600

    #serieport = serial.Serial(port, baud, timeout=1)

    

    if raakode_gui_metoder.serieport.isOpen():
        print(raakode_gui_metoder.serieport.name, 'er open')
    else:
        raakode_gui_metoder.serieport.open()

    #serie_traad = threading.Thread(target=seriekomm, args=(raakode_gui_metoder.serieport, brukarkommandoar, uC_meldingar))
    serie_traad = threading.Thread(target=seriekomm_egen, daemon=True)
    serie_traad.start()

    print('Loggaren er klar')

#    while kommando != 'k':
#        kommando = input('Gi kommando(k-koeyr logging, s-stopp logging):\n')  # Loepande lesing, dvs. vil staa her
    # til det kjem noko inn fraa tastaturet.
    while not kommando_status.start_event.is_set():
        time.sleep(0.1)

    kommando='k'
    print('Startar logging')
    brukarkommandoar.put(kommando)  # Gi melding til serietraaden om aa starta sjekking av port
    #serieport.write('k'.encode('utf-8'))  # Gi melding til uC-en om aa koeyra i gong # KT la til encoding

#    while kommando != 's':
#        kommando = input('Gi kommando:\n')  # Loepande lesing, dvs. staar her

    while not kommando_status.stopp_event.is_set():
        time.sleep(0.1)

    stopp_kommando='s'
    brukarkommandoar.put(kommando)  # Gi melding til serietraaden om aa stoppa, men fullfoera logging tom. ETX
    time.sleep(1)  # Sikra at traaden faar med seg slutten paa meldinga
    raakode_gui_metoder.serieport.write('s'.encode('utf-8'))  # Gi melding til uC-en om aa stoppa sending av nye data #KT La til encoding
    print('Stoppar logging')

    # serieport.close()     # Det er naa kome kommando om aa stoppa logginga
    # print '%s %s'  %(serieport.name, 'er stengt')

    print(uC_meldingar)

    f.write(str(uC_meldingar))
    f.close()

 # Lag lister av raadata.
    tid_raa = []
    a_x_raa = []
    a_y_raa = []
    a_z_raa = []

    for i in range(0, len(uC_meldingar)):
        if uC_meldingar[i] == 'T':
            kommando_status.tid_raa.append(16 * hexascii2int(uC_meldingar[i + 1]) + hexascii2int(uC_meldingar[i + 2]))

        elif uC_meldingar[i] == 'X':
            #Fiks slik at ein faar fram negative tal.
            a_x_raa.append(
                4096 * hexascii2int(uC_meldingar[i + 1]) + 256 * hexascii2int(uC_meldingar[i + 2]) + 16 * hexascii2int(
                    uC_meldingar[i + 3]) + hexascii2int(uC_meldingar[i + 4]))
        elif uC_meldingar[i] == 'Y':
            #Fiks slik at ein faar fram negative tal.
            a_y_raa.append(
                4096 * hexascii2int(uC_meldingar[i + 1]) + 256 * hexascii2int(uC_meldingar[i + 2]) + 16 * hexascii2int(
                    uC_meldingar[i + 3]) + hexascii2int(uC_meldingar[i + 4]))
        elif uC_meldingar[i] == 'Z':
            #Fiks slik at ein faar fram negative tal.
            a_z_raa.append(
                4096 * hexascii2int(uC_meldingar[i + 1]) + 256 * hexascii2int(uC_meldingar[i + 2]) + 16 * hexascii2int(
                    uC_meldingar[i + 3]) + hexascii2int(uC_meldingar[i + 4]))


 # Lag skalerte lister og rekna ut tilleggsvariablar.
    a_x = []
    a_y = []
    a_z = []
    aks_abs = []  # sqrt(ax**2 + ay**2 + az**2)
    ayz_abs = []
    rull = []     # rullvinkel psi i grader (om x-aksen)
    stamp = []    # stampvinkel theta i grader (om y-aksen)

    for i in range(0, len(a_x_raa)):
        if a_x_raa[i] >= 32768:
            kommando_status.a_x.append((float(a_x_raa[i])-65536.0)/1000.0) # 1mg pr. LSb iflg. databladet.
        else:
            kommando_status.a_x.append(float(a_x_raa[i]/1000.0))

    for i in range(0, len(a_y_raa)):
        if a_y_raa[i] >= 32768:
            kommando_status.a_y.append((float(a_y_raa[i])-65536.0)/1000.0)
        else:
            kommando_status.a_y.append(float(a_y_raa[i]/1000.0))

    for i in range(0, len(a_z_raa)):
        if a_z_raa[i] >= 32768:
            kommando_status.a_z.append((float(a_z_raa[i])-65536.0)/1000.0)
        else:
            kommando_status.a_z.append(float(a_z_raa[i])/1000.0)

    for i in range(0, len(kommando_status.a_z)):
        kommando_status.aks_abs.append(np.sqrt(kommando_status.a_x[i]**2 + kommando_status.a_y[i]**2 + kommando_status.a_z[i]**2))
    for i in range(0, len(a_z_raa)):
        kommando_status.ayz_abs.append(np.sqrt(kommando_status.a_y[i]**2 + kommando_status.a_z[i]**2))

    for i in range(0, len(kommando_status.a_x)):
        kommando_status.stamp.append(np.arctan2(kommando_status.a_x[i], kommando_status.ayz_abs[i]) * 180 / np.pi)

    for i in range(0, len(a_x)):
        if a_z[i] == 0:
            if i == 0:
                kommando_status.rull.append(0)
            else:
                kommando_status.rull.append(rull[i-1])     #Unngaa deling paa null

        else:
            kommando_status.rull.append(np.arctan2(a_y[i], a_z[i]) * 180 / np.pi)

  # Skal laga ei kontinuerleg aukande tidsliste som startar i null.
    tid = []
    Ts = 0.1  # Sampleintervall i sekund
    tidsomloepnr = 0

    for j in range(0, len(kommando_status.tid_raa)):
        kommando_status.tid.append(kommando_status.tid_raa[j] + tidsomloepnr * 256)

        if kommando_status.tid_raa[j] == 255: # Tidsreferansen er paa 8 bit og rullar rundt kvar 256. gong
            tidsomloepnr = tidsomloepnr + 1

    skyv = kommando_status.tid[0] # Vil at tidslista skal starta paa null.
    print(skyv)
    for k in range(0, len(kommando_status.tid)):
        kommando_status.tid[k] = Ts * (kommando_status.tid[k] - skyv)


 # Seks subplott med felles tidsakse.
    


    print('Slutt i main')