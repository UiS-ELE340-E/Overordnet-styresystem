import sys
import numpy as np
import threading
import time
from PyQt6.QtWidgets import QApplication, QLineEdit, QGroupBox, QFormLayout, QLabel, QPushButton, QMainWindow, QLCDNumber, QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import kommando_status
import serial

# Oppsett for innhenting og stopping av sensordata ----------------
delta_t = 0.05 # Periodetid for sampling i live-plottet
maalinger_n = 100 # Antall målinger som beholdes i live-plottet
stopp_trigger = threading.Event()

sensor_data = { #Array som holder på sensormålingene
    "x": np.linspace(0, delta_t*maalinger_n, 100),
    "avstand": np.zeros(maalinger_n),
    "error": np.zeros(maalinger_n),
    "referanse": np.zeros(maalinger_n),
    "uP": np.zeros(maalinger_n),
    "uI": np.zeros(maalinger_n),
    "uD": np.zeros(maalinger_n)   
}

def sensor_loop(): #Funksjon som setter inn måleverdien fra sensor og rullerer verdiene videre slik at datasettet som plottes alltid er maalinger_n langt.
    while not stopp_trigger.is_set():

        sensor_data["avstand"][:-1] = sensor_data["avstand"][1:]
        sensor_data["error"][:-1] = sensor_data["error"][1:]
        sensor_data["uP"][:-1] = sensor_data["uP"][1:]
        sensor_data["uI"][:-1] = sensor_data["uI"][1:]
        sensor_data["uD"][:-1] = sensor_data["uD"][1:]

        sensor_data["avstand"][-1] = kommando_status.avstand/10
        sensor_data["error"][-1] = kommando_status.error
        sensor_data["uP"][-1] = kommando_status.uP
        sensor_data["uI"][-1] = kommando_status.uI
        sensor_data["uD"][-1] = kommando_status.uD        


        #print(sensor_data["error"])
        
        time.sleep(delta_t)
# ---------------------------------------------------------------

serieport = serial.Serial(
    port='COM13',
    baudrate=115200,
    bytesize=serial.EIGHTBITS,   # 8 data bits
    parity=serial.PARITY_NONE,   # No parity
    stopbits=serial.STOPBITS_ONE, # 1 stop bit
    timeout=0.5   # short timeout so reads can check stopp_trigger and threads can exit
)

def send_RPID(RPID_verdier):
    serieport.write(RPID_verdier)
    

def BE_til_LE(hexverdi):
    return bytes([hexverdi & 0xFF, (hexverdi>>8) & 0xFF])

# Oppsett av grafer til GUI ----------------------------
class Mpl_grafer(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
#------------------------------------------------------

# GUI hovedvindu -------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ELE340 - Gruppe E")

        # Setter opp ønsket layout på GUI: 3 blokker horisontalt med undergrupper for: Grafer, setpunkt, start/stopp
        gridman = QVBoxLayout()

        subgrid_graf = QVBoxLayout()
        subgrid_HMI = QHBoxLayout()

        Ref_modul = QVBoxLayout()
        Kp_modul = QVBoxLayout()
        Ti_modul = QVBoxLayout()
        Td_modul = QVBoxLayout()
        knapp_modul = QVBoxLayout()

        # Setter opp Graf 1 og 2, per nå er graf 1 bare en avlesning av X-retning på aks-måler, og 2 er den deriverte av dette
        self.graf = Mpl_grafer(self)
        self.graf_error = Mpl_grafer(self)
        ax = self.graf.ax
        #ax.set_autoscale_on(False)
        #ax.set_autoscalex_on(True)
        #ax.set_autoscaley_on(False)
        #self.graf.ax.set_ylim(0,50)
        self.line, = self.graf.ax.plot(sensor_data["x"], sensor_data["avstand"], color="blue", label="Avstand [cm]")

        ax2 = self.graf_error.ax
        self.line2, = self.graf_error.ax.plot(sensor_data["x"], sensor_data["error"], color="red", label="Error [cm]")

        self.graf.ax.set_ylabel("Avstand [cm]", color="blue")
        self.graf.ax.tick_params(axis='y', labelcolor="blue")
        ax2.set_ylabel("Error [mm]", color="red")
        ax2.tick_params(axis='y', labelcolor="red")

        self.ax2 = ax2

        self.graf_PID = Mpl_grafer(self)
        
        self.graf_PID.ax.set_yscale("log")
        self.line_P, = self.graf_PID.ax.plot(sensor_data["x"], sensor_data["uP"], color="red")
        self.line_I, = self.graf_PID.ax.plot(sensor_data["x"], sensor_data["uI"], color="green")
        self.line_D, = self.graf_PID.ax.plot(sensor_data["x"], sensor_data["uD"], color="blue")


        # Setter opp en timer for å automatisk oppdatere plottene
        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        # Setter opp numerisk display og knapper
        Ref_modul.addWidget(QLabel("Referanse [cm]"))
        self.Ref_LCD = QLCDNumber()
        self.Ref_LCD.display(kommando_status.Ref_iv/10)
        self.Ref_txt = QLineEdit()

        Kp_modul.addWidget(QLabel("P [x1000]"))
        self.Kp_LCD = QLCDNumber()
        self.Kp_LCD.display(kommando_status.Kp_iv/1000)
        self.Kp_txt = QLineEdit()

        Ti_modul.addWidget(QLabel("I"))
        self.Ti_LCD = QLCDNumber()
        self.Ti_LCD.display(kommando_status.Ti_iv/1000)
        self.Ti_txt = QLineEdit()

        Td_modul.addWidget(QLabel("D"))
        self.Td_LCD = QLCDNumber()
        self.Td_LCD.display(kommando_status.Td_iv/1000)
        self.Td_txt = QLineEdit()

        self.knapp_start = QPushButton("Start")
        self.knapp_stopp = QPushButton("Stopp")
        self.knapp_set = QPushButton("Sett distanse")

        #Setter opp innhold i subgrids
        subgrid_graf.addWidget(self.graf)
        subgrid_graf.addWidget(self.graf_error)
        subgrid_graf.addWidget(self.graf_PID)
        
        Ref_modul.addWidget(self.Ref_LCD)
        Ref_modul.addWidget(self.Ref_txt)

        Kp_modul.addWidget(self.Kp_LCD)
        Kp_modul.addWidget(self.Kp_txt)

        Ti_modul.addWidget(self.Ti_LCD)
        Ti_modul.addWidget(self.Ti_txt)
        
        Td_modul.addWidget(self.Td_LCD)
        Td_modul.addWidget(self.Td_txt)
        
        knapp_modul.addWidget(self.knapp_start)
        knapp_modul.addWidget(self.knapp_set)
        knapp_modul.addWidget(self.knapp_stopp)

        subgrid_HMI.addLayout(Ref_modul)
        subgrid_HMI.addLayout(Kp_modul)
        subgrid_HMI.addLayout(Ti_modul)
        subgrid_HMI.addLayout(Td_modul)
        subgrid_HMI.addLayout(knapp_modul)

        gridman.addLayout(subgrid_graf)
        gridman.addLayout(subgrid_HMI)

        # Setter opp sknapp-events
        self.knapp_set.clicked.connect(self.update_LCD)
        self.y_shift = 0

        self.knapp_start.clicked.connect(self.start_kommando)
        self.knapp_stopp.clicked.connect(self.stopp_kommando)



        widget = QWidget()
        widget.setLayout(gridman)
        self.setCentralWidget(widget)

    # Div funksjoner for knapp-events og oppdatering av GUI-elementer
    def start_kommando(self):
        print("k")   
        kommando_status.start_event.set()
        kommando='k'
        status = 'k'
        RPID = (BE_til_LE(kommando_status.Ref_iv))+(BE_til_LE(kommando_status.Kp_iv))+(BE_til_LE(kommando_status.Ti_iv))+(BE_til_LE(kommando_status.Td_iv))
        print(RPID)
        send_RPID(RPID)        
        

    def stopp_kommando(self):
        RPID = (BE_til_LE(300))+(BE_til_LE(0))+(BE_til_LE(0))+(BE_til_LE(0))
        print(RPID)
        send_RPID(RPID)
        print("s")
        # Close serial port to unblock any blocking reads in worker threads
        try:
            serieport.close()
        except Exception:
            pass
        kommando_status.stopp_event.set()
        stopp_trigger.set()
        self.timer.stop()
        QApplication.quit()

    def update_plot(self):
        self.line.set_ydata(sensor_data["avstand"])
        self.line2.set_ydata(sensor_data["error"])

        self.line_P.set_ydata(sensor_data["uP"])
        self.line_I.set_ydata(sensor_data["uI"])
        self.line_D.set_ydata(sensor_data["uD"])
        
        ax = self.line.axes
        ax2 = self.line2.axes
        ax_PID = self.line_P.axes
    
        # autoscale both plots
        ax.relim()
        ax.autoscale_view()
        ax2.relim()
        ax2.autoscale_view()
        ax_PID.relim()
        ax_PID.autoscale_view()
        #ax.relim()
        #ax.autoscale_view(scalex=True, scaley=False)
        
        self.graf.draw()
        self.graf_error.draw()
        self.graf_PID.draw()
    
    def update_LCD(self):
        kommando_status.Ref_ny = float(self.Ref_txt.text())
        kommando_status.Kp_ny = float(self.Kp_txt.text())
        kommando_status.Ti_ny = float(self.Ti_txt.text())
        kommando_status.Td_ny = float(self.Td_txt.text())

        try:
            print(1)
            Ref_verdi = int(kommando_status.Ref_ny)*10
            print(2)
            Kp_verdi = int(kommando_status.Kp_ny*1000)
            Ti_verdi = int(kommando_status.Ti_ny*1000)
            Td_verdi = int(kommando_status.Td_ny*1000)
            print(3)
            print(Ref_verdi)
            print(Kp_verdi)
            print(Ti_verdi)
            print(Td_verdi)
            if 10 < int(kommando_status.Ref_ny) < 400:
                self.Ref_LCD.display(float(kommando_status.Ref_ny))   
            else:
                print("Vennligst skriv et tall innenfor 20 og 150 [cm].")
            self.Kp_LCD.display(kommando_status.Kp_ny)
            self.Ti_LCD.display(kommando_status.Ti_ny)
            self.Td_LCD.display(kommando_status.Td_ny)
            RPID = (BE_til_LE(Ref_verdi))+(BE_til_LE(Kp_verdi))+(BE_til_LE(Ti_verdi))+(BE_til_LE(Td_verdi))
            print(RPID)
            send_RPID(RPID)
        except ValueError:
            print("Vennligst skriv et tall innenfor 20 og 150 [cm].")
#------------------------------------------------------------------
# GUI oppsummering ---------We've had one, yes, but what about second GUI? ----------------------------------
class SecondWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ELE340 - Gruppe E - Oppsummering")

        # Setter opp ønsket layout på GUI
        gridman_the_second = QVBoxLayout()

        self.oppsummering = QGroupBox("Ytelsessammendrag")
        oppsummering_layout = QFormLayout()


        oppsummering_layout.addRow("IAE:", QLabel(f"{kommando_status.IAE:.3f}"))
        oppsummering_layout.addRow("MAE:", QLabel(f"{kommando_status.MAE:.3f}"))
        oppsummering_layout.addRow("RMSE:", QLabel(f"{kommando_status.RMSE:.3f}"))
        oppsummering_layout.addRow("Max absolutt Error:", QLabel(f"{kommando_status.max_error:.3f}"))
        oppsummering_layout.addRow("Tid innenfor ±5mm i %:", QLabel(f"{kommando_status.percent_in_tol:.2f}%"))

        self.oppsummering.setLayout(oppsummering_layout)
        gridman_the_second.addWidget(self.oppsummering)

        widget2 = QWidget()
        widget2.setLayout(gridman_the_second)
        self.setCentralWidget(widget2)

        self.resize(400, 600)




# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    thread1 = threading.Thread(target=sensor_loop, daemon=True)
    thread1.start()

    applikasjon = QApplication(sys.argv)
    vindu = MainWindow()
    vindu.show()
    applikasjon.exec()
    serieport.close()