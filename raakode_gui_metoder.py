import sys
import numpy as np
import threading
import time
from PyQt6.QtWidgets import QApplication, QLineEdit, QDial, QPushButton, QMainWindow, QLCDNumber, QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import kommando_status

# Oppsett for innhenting og stopping av sensordata ----------------
delta_t = 0.05 # Periodetid for sampling i live-plottet
maalinger_n = 100 # Antall målinger som beholdes i live-plottet
stopp_trigger = threading.Event()

sensor_data = { #Array som holder på sensormålingene
    "x": np.linspace(0, delta_t*maalinger_n, 100),
    "y": np.zeros(maalinger_n),
    "dy": np.zeros(maalinger_n)   
}

def sensor_loop(): #Funksjon som setter inn måleverdien fra sensor og rullerer verdiene videre slik at datasettet som plottes alltid er maalinger_n langt.
    while not stopp_trigger.is_set():
        sensor_data["y"][:-1] = sensor_data["y"][1:]
        sensor_data["y"][-1] = kommando_status.maaleverdi
        sensor_data["dy"] = np.gradient(sensor_data["y"], delta_t)
        time.sleep(delta_t)
# ---------------------------------------------------------------

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
        gridman = QHBoxLayout()
        subgrid_1 = QVBoxLayout()
        subgrid_2 = QVBoxLayout()
        subgrid_3 = QVBoxLayout()

        # Setter opp Graf 1 og 2, per nå er graf 1 bare en avlesning av X-retning på aks-måler, og 2 er den deriverte av dette
        self.graf = Mpl_grafer(self)
        self.line, = self.graf.ax.plot(sensor_data["x"], sensor_data["y"], color="blue")

        self.graf_deriv = Mpl_grafer(self)
        self.line_deriv, = self.graf_deriv.ax.plot(sensor_data["x"], sensor_data["dy"], color="red")

        subgrid_1.addWidget(self.graf)
        subgrid_1.addWidget(self.graf_deriv)

        # Setter opp en timer for å automatisk oppdatere plottene
        self.timer = QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        # Setter opp numerisk display og knapper
        self.LCD = QLCDNumber()
        self.LCD.display(30)

        self.tekstboks = QLineEdit()
        self.knapp_set = QPushButton("Sett distanse")

        subgrid_2.addWidget(self.LCD)
        subgrid_2.addWidget(self.tekstboks)
        subgrid_2.addWidget(self.knapp_set)

        self.knapp_start = QPushButton("Start")
        self.knapp_stopp = QPushButton("Stopp")
        subgrid_3.addWidget(self.knapp_start)
        subgrid_3.addWidget(self.knapp_stopp)

        gridman.addLayout(subgrid_1)
        gridman.addLayout(subgrid_2)
        gridman.addLayout(subgrid_3)

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
        

    def stopp_kommando(self):
        print("s")
        kommando_status.stopp_event.set()
        stopp_trigger.set()
        self.timer.stop()
        QApplication.quit()

    def update_plot(self):
        self.line.set_ydata(sensor_data["y"] + self.y_shift)
        self.line_deriv.set_ydata(sensor_data["dy"])

        ax = self.line.axes
        ax_deriv = self.line_deriv.axes
    
        # autoscale both plots
        ax.relim()
        ax.autoscale_view()
        ax_deriv.relim()
        ax_deriv.autoscale_view()
        
        self.graf.draw()
        self.graf_deriv.draw()
    
    def update_LCD(self):
        text = self.tekstboks.text()
        try:
            verdi = float(text)
            if 20 < verdi < 150:
                self.LCD.display(verdi)
                self.y_shift = verdi
            else:
                print("Vennligst skriv et tall innenfor 20 og 150 [cm].")
        except ValueError:
            print("Vennligst skriv et tall innenfor 20 og 150 [cm].")
#------------------------------------------------------------------


if __name__ == "__main__":
    thread1 = threading.Thread(target=sensor_loop, daemon=True)
    thread1.start()

    applikasjon = QApplication(sys.argv)
    vindu = MainWindow()
    vindu.show()
    applikasjon.exec()