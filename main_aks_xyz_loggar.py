__author__ = 'Morten Tengesdal og Kristian Thorsen'
# Dato:2016.08.05
# Oppdatert til Python 3 av K. Thorsen
# Med serieporttraad og med meldingskoe
# Skriptet loggar akselerasjonsdata i X-, Y- og Z-retning i 16-bitsformat og med
# tidsreferanse i 8-bitsformat.
# Meldingsformat STX+(T+samplenr.(2 ASCII HEX-siffer)+X+data(4 ASCII Hex-siffer)
#                                                     Y+data(4 ASCII Hex-siffer)
#                                                     Z+data(4 ASCII Hex-siffer))*N+ETX
# Raadata blir lagra til fil og skalerte data blir plotta.
# Skriptet blir koeyrt saman med prosjektet aks_xyz_loggar_stm32f3_disc paa
# kortet STM32F3Discovery

import threading
import queue
import time
import numpy as np
import serial
import matplotlib.pyplot as mpl
import csv
#from matplotlib.animation import FuncAnimation

# Importerer GUI oppsett
import raakode_gui_metoder
import kommando_status
#start_event = threading.Event()
# --------------------------------------------------------------------------
# Oppsett og Metodar for Liveplotting
# --------------------------------------------------------------------------
#fig, ax = mpl.subplots()
#x_data = []
#y_data = []
#line, =ax.plot([],[],'b-')

datakoe=queue.Queue()


def print_bytes(data):
    print([f"{b:02X}" for b in data])



def seriekomm_egen():
    frame_errors = 0
    while not raakode_gui_metoder.stopp_trigger.is_set():
        # If port is closed or None, stop the loop
        sp = getattr(raakode_gui_metoder, "serieport", None)
        if sp is None or not getattr(sp, "is_open", False):
            time.sleep(0.05)
            continue

        try:
            data = sp.read(21)
        except (serial.SerialException, OSError, AttributeError) as e:
            print("Serial read aborted:", e)
            break

        if len(data) == 21 and data[0] == 0xFF and data[20] == 0xF0:
            datakoe.put(data)
        else:
            print('Frame error')
            frame_errors += 1

        if frame_errors > 5:
            try:
                seriekomm_resynkroniserar()
            except Exception as e:
                print("Resync failed:", e)
                break
            frame_errors = 0

        time.sleep(0.01)


def seriekomm_resynkroniserar():
    sp = getattr(raakode_gui_metoder, "serieport", None)
    if sp is None or not getattr(sp, "is_open", False):
        raise RuntimeError("Serial port not open for resynchronization")

    while True:
        try:
            bitsjekker = sp.read(1)
        except (serial.SerialException, OSError, AttributeError) as e:
            print("Serial read aborted during resync:", e)
            raise

        if bitsjekker == b'\xFF':
            break
    resterande_beskjed = sp.read(20)
    ramme = (bitsjekker or b"") + (resterande_beskjed or b"")
    if len(ramme) == 21 and ramme[-1] == 0xF0:
        print('Jadda, fikk til resynkronisering!')
        datakoe.put(ramme)
        return ramme
    else:
        print('Tror vi prøver en gang til....')
        return seriekomm_resynkroniserar()

def datakoe_handterer():
    start_sjekk=True
    while not raakode_gui_metoder.stopp_trigger.is_set():
        datakoe_lokal = list(datakoe.get())
        #print_bytes(datakoe_lokal)
        if kommando_status.start_event.is_set():
            # Sjekker hvor mange skritt samplenr. inkrementeres med
            if start_sjekk:
                sample=1
                sample_skritt=0

                start_sjekk=False       
            elif datakoe_lokal[1]>sample_prev:
                sample_skritt = datakoe_lokal[1]-sample_prev
            elif datakoe_lokal[1]==0:
                sample_skritt=256-sample_prev
            elif datakoe_lokal[1]<sample_prev:
                sample_skritt=datakoe_lokal[1]+256-datakoe_lokal[1]
            sample=sample+sample_skritt
            print(sample)
            print(datakoe_lokal[1])
            print(sample_skritt)

            sample_prev=datakoe_lokal[1]
            datakoe_lokal[1]=sample

            # Omgjøring av innkommende verdier
            avstand_raa = (datakoe_lokal[3]<<8)|datakoe_lokal[2]
            kommando_status.avstand = avstand_raa if avstand_raa < 2000 else kommando_status.avstand
            kommando_status.x_aks = (datakoe_lokal[5]<<8)|datakoe_lokal[4]
            kommando_status.y_aks = (datakoe_lokal[7]<<8)|datakoe_lokal[6]
            kommando_status.z_aks = (datakoe_lokal[9]<<8)|datakoe_lokal[8]
            #kommando_status.error = int(kommando_status.avstand)-int(kommando_status.Ref_ny)
            error_raa = (datakoe_lokal[11] << 8) | datakoe_lokal[10]
            # interpret as signed int16 and keep only plausible values
            error_raa = (error_raa - 0x10000) if (error_raa & 0x8000) else error_raa
            kommando_status.error = error_raa if -2000 <= error_raa <= 2000 else kommando_status.error
            kommando_status.power = (datakoe_lokal[13]<<8)|datakoe_lokal[12]
            kommando_status.uP = (datakoe_lokal[15]<<8)|datakoe_lokal[14]
            kommando_status.uI = (datakoe_lokal[17]<<8)|datakoe_lokal[16]
            kommando_status.uD = (datakoe_lokal[19]<<8)|datakoe_lokal[18]
            datakoe_lokal_hex =  " ".join(f"{b:02X}" for b in datakoe_lokal)

            #log_line = (
            #    f"{sample} | "
            #    f"{kommando_status.avstand} | {kommando_status.x_aks} | {kommando_status.y_aks} | {kommando_status.z_aks} | {kommando_status.error} | "
            #    f"{kommando_status.power} | {kommando_status.uP} | {kommando_status.uI} | {kommando_status.uD}\n"
            #)


            #f.write(log_line)

            skrivar.writerow([
                sample, kommando_status.avstand, kommando_status.x_aks, kommando_status.y_aks, kommando_status.z_aks,
                kommando_status.error, kommando_status.power, kommando_status.uP, kommando_status.uI, kommando_status.uD
            ])        
        
            f.flush
        
def oppsummering(logge_fil):
    print("Kort oppsummering")
    # Error-relaterte metrics
    # RMSE - Root Mean Square Error
    # MAE - Mean Absolute Error
    # Max Absolute Error
    # Time-in-Tolerance%
    # IAE - Integral of Absolute Error

    # PID metrics
    # Average absolute contribution - % of control effort - Viser hvilket av PID leddene som kontributerer mest
    # StdDev of uD - Derivative noise amplification - Stor std(uD) kan være et tegn på at den amplifiserer støy e.l.
    # Mean absolute control effort - høy mean-power ved dårlig performance er et tegn på at bedre tuning behøves, evt. anti-windup

    # Overshoot % - høy overshoot kan tyde på aggressiv tuning eller resonans
    # Actuator saturation - hvis power ofte fører til at styrekortet spør om mer pådrag enn linmoten har tilgjengelig bør den tunes på en annen måte


    dt = 0.01
    error_liste=[]

    uP_liste=[]
    uI_liste=[]
    uD_liste=[]
    power_liste=[]
    distanse_liste=[]

    linmot_limit = 1000
    TOL = 5.0

    with open(logge_fil,"r") as fil:
        header = fil.readline()
        for line in fil:
            parts = line.strip().split(",")

            distanse = float(parts[1])
            error = float(parts[5])
            power = float(parts[6])
            uP = float(parts[7])
            uI = float(parts[8])
            uD = float(parts[9])

            distanse_liste.append(distanse)
            error_liste.append(error)
            power_liste.append(power)
            uP_liste.append(uP)
            uI_liste.append(uI)
            uD_liste.append(uD)

    n = len(error_liste)

    # error-metrics
    kommando_status.IAE = sum(abs(e) * dt for e in error_liste)
    kommando_status.MAE  = sum(abs(e) for e in error_liste) / n
    kommando_status.RMSE = (sum(e*e for e in error_liste) / n) ** 0.5
    kommando_status.max_error = max(abs(e) for e in error_liste)
    
    kommando_status.percent_in_tol = 100 * sum(1 for e in error_liste if abs(e) <= TOL) / n

    # PID-metrics
    avg_abs_uP = sum(abs(x) for x in uP_liste)/n
    avg_abs_uI = sum(abs(x) for x in uI_liste)/n
    avg_abs_uD = sum(abs(x) for x in uD_liste)/n

    sum_abs_PID = avg_abs_uP + avg_abs_uI + avg_abs_uD
    if sum_abs_PID == 0:
        pct_uP = pct_uI = pct_uD = 0
    else:
        pct_uP = 100 * avg_abs_uP/sum_abs_PID
        pct_uI = 100 * avg_abs_uI/sum_abs_PID
        pct_uD = 100 * avg_abs_uD/sum_abs_PID

    
    # std(uD)
    mean_uD = sum(uD_liste)/n
    std_uD = (sum((x - mean_uD)**2 for x in uD_liste)/n)**0.5
    # Total kontrolleffekt 
    mean_abs_power = sum(abs(x) for x in power_liste)/n

    # Ekstra relevante metrics
    overshoot = max(error_liste)

    # Overshoot relativt til gjennomsnittsdistanse - %
    mean_distanse = sum(distanse_liste)/n
    overshoot_pct = 100*(overshoot / mean_distanse) if mean_distanse != 0 else 0

    # Actuator saturation
    saturation_pct = 100 * sum(1 for p in power_liste if abs(p) >= linmot_limit) / n




    print("IAE =",kommando_status.IAE)
    print("MAE =",kommando_status.MAE)
    print("RMSE =",kommando_status.RMSE)
    print("max_error =",kommando_status.max_error)
    print("Time in tolerance ±5mm = ", kommando_status.percent_in_tol,"%")

    print("Gjennomsnittlig |uP|:",avg_abs_uP)
    print("Gjennomsnittlig |uI|:",avg_abs_uI)
    print("Gjennomsnittlig |uD|:",avg_abs_uD)
    print("P/I/D ratio:",pct_uP,"%",pct_uI,"%",pct_uD,"%")
    print("std(uD):",std_uD)
    print("Gjennomsnittlig |power|:",mean_abs_power)

    print("Overshoot abs:",overshoot)
    print("Overshoot %:",overshoot_pct)
    print("Linmot saturering:",saturation_pct)



        



if __name__ == "__main__":

    #fileNamn = 'logg.txt'
    #f = open(fileNamn, 'w')
    #f.write("Tid | Avstand | X | Y | Z | Error | Power | uP | uI | uD\n")

    fileNamn = 'csv_logg.csv'
    f = open(fileNamn,"w",newline="")
    skrivar = csv.writer(f)
    skrivar.writerow([
    "Tid", "Avstand", "X", "Y", "Z", "Error",
    "Power", "uP", "uI", "uD"
    ])


    thread1 = threading.Thread(target=raakode_gui_metoder.sensor_loop, daemon=True)
    thread1.start()

    thread3 = threading.Thread(target=datakoe_handterer, daemon=True)
    thread3.start()

    thread2 = threading.Thread(target=seriekomm_egen, daemon=True)
    thread2.start()



    applikasjon = raakode_gui_metoder.QApplication(raakode_gui_metoder.sys.argv)
    vindu = raakode_gui_metoder.MainWindow()
    vindu.show()
    applikasjon.exec()    

    f.close()
    raakode_gui_metoder.serieport.close()

    oppsummering(fileNamn)





