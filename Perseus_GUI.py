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
import csv

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
    port=kommando_status.COMport_nr,
    baudrate=115200,
    bytesize=serial.EIGHTBITS,   # 8 databit
    parity=serial.PARITY_NONE,   # Ingen paritet
    stopbits=serial.STOPBITS_ONE, # 1 stop bit
    timeout=1   # Timeout som gjør at koden flyter vider ved mangel på data
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

        # Setter opp ønsket layout på GUI
        gridman = QVBoxLayout()

        subgrid_graf = QVBoxLayout()
        subgrid_HMI = QHBoxLayout()

        Ref_modul = QVBoxLayout()
        Kp_modul = QVBoxLayout()
        Ti_modul = QVBoxLayout()
        Td_modul = QVBoxLayout()
        knapp_modul = QVBoxLayout()

        # Setter opp Grafer
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
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        # Setter opp numerisk display, skrivefelt og knapper
        Ref_modul.addWidget(QLabel("Referanse [cm]"))
        self.Ref_LCD = QLCDNumber()
        self.Ref_LCD.display(kommando_status.Ref_iv/10)
        self.Ref_txt = QLineEdit()
        self.Ref_txt.setText(str(int(kommando_status.Ref_iv/10)))
        

        Kp_modul.addWidget(QLabel("P [x1000]"))
        self.Kp_LCD = QLCDNumber()
        self.Kp_LCD.display(kommando_status.Kp_iv/1000)
        self.Kp_txt = QLineEdit()
        self.Kp_txt.setText(str(int(kommando_status.Kp_iv/1000)))

        Ti_modul.addWidget(QLabel("I"))
        self.Ti_LCD = QLCDNumber()
        self.Ti_LCD.display(kommando_status.Ti_iv/1000)
        self.Ti_txt = QLineEdit()
        self.Ti_txt.setText(str(int(kommando_status.Ti_iv/1000)))

        Td_modul.addWidget(QLabel("D"))
        self.Td_LCD = QLCDNumber()
        self.Td_LCD.display(kommando_status.Td_iv/1000)
        self.Td_txt = QLineEdit()
        self.Td_txt.setText(str(int(kommando_status.Td_iv/1000)))

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
           
        kommando_status.start_event.set()
        RPID = (BE_til_LE(kommando_status.Ref_iv))+(BE_til_LE(kommando_status.Kp_iv))+(BE_til_LE(kommando_status.Ti_iv))+(BE_til_LE(kommando_status.Td_iv))
        print(RPID)
        send_RPID(RPID)        
        

    def stopp_kommando(self):
        if kommando_status.stopp_teller == 0:
            RPID = (BE_til_LE(300))+(BE_til_LE(0))+(BE_til_LE(0))+(BE_til_LE(0))
            print(RPID)
            send_RPID(RPID)
            try:
                serieport.close()
            except Exception:
                pass
            kommando_status.stopp_event.set()
            stopp_trigger.set()
            self.timer.stop()
            kommando_status.stopp_teller = 1
            self.knapp_stopp.setText("Lukk program")

            # Viser oppsummeringsvindu som leser fra loggefilen
            self.summary_win = SecondWindow(self, csv_path="csv_logg.csv")
            self.summary_win.show()
        else:
            QApplication.quit()
            

    def update_plot(self): # Oppdaterer grafene i GUI, blir kalt av intern timer i GUI
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
    
    def update_LCD(self): # Sjekker om skrevne verdier er gyldige, deretter ppdaterer numerisk display og sender nye Ref og PID-verdier til linmot
        kommando_status.Ref_ny = float(self.Ref_txt.text())
        kommando_status.Kp_ny = float(self.Kp_txt.text())
        kommando_status.Ti_ny = float(self.Ti_txt.text())
        kommando_status.Td_ny = float(self.Td_txt.text())

        try:
            Ref_ok = 0
            Kp_ok = 0
            Ti_ok = 0
            Td_ok = 0

            Ref_verdi = int(kommando_status.Ref_ny)*10
            Kp_verdi = int(kommando_status.Kp_ny*1000)
            Ti_verdi = int(kommando_status.Ti_ny*1000)
            Td_verdi = int(kommando_status.Td_ny*1000)

            if 20 <= int(kommando_status.Ref_ny) <= 150:
                Ref_ok = 1   
            else:
                print("Referansen må være et tall innenfor 20 og 150 [cm].")
            
            if 0 <= float(kommando_status.Kp_ny) <= 50:
                Kp_ok = 1
            else:
                print("Kp må være et tall innenfor 0 og 50 [x1000].")
            
            if 0 <= float(kommando_status.Ti_ny) <= 50:
                Ti_ok = 1
            else:
                print("Ti må være et tall innenfor 0 og 50.")
            
            if 0 <= float(kommando_status.Td_ny) <= 50:
                Td_ok = 1
            else:
                print("Td må være et tall innenfor 0 og 50.")
            
            if Ref_ok and Kp_ok and Ti_ok and Td_ok:
                self.Ref_LCD.display(kommando_status.Ref_ny)
                self.Kp_LCD.display(kommando_status.Kp_ny)
                self.Ti_LCD.display(kommando_status.Ti_ny)
                self.Td_LCD.display(kommando_status.Td_ny)
                RPID = (BE_til_LE(Ref_verdi))+(BE_til_LE(Kp_verdi))+(BE_til_LE(Ti_verdi))+(BE_til_LE(Td_verdi))
                print(RPID)
                send_RPID(RPID)
        except ValueError:
            print("Vennligst skriv et tall innenfor 20 og 150 [cm] på referansen og tall mellom 0 og 50 for PID-parametrene.")


# GUI for  oppsummering ----------------We've had one, yes, but what about second GUI? ----------------------------------
class SecondWindow(QMainWindow):
    def __init__(self, parent=None, csv_path="csv_logg.csv"):
        super().__init__(parent)
        self.setWindowTitle("ELE340 - Gruppe E - Oppsummering")
        self.resize(420, 320)

        self.csv_path = csv_path

        self.oppsummering_group = QGroupBox("Ytelsessammendrag")
        layout = QFormLayout()

        # Regner ut oppsummeringsdata fra loggefil
        metrics = self._compute_metrics(self.csv_path)

        # Kapper desimalene og legger verdiene inn i GUI som labels
        layout.addRow("IAE:", QLabel(f"{metrics['IAE']:.3f}"))
        layout.addRow("MAE:", QLabel(f"{metrics['MAE']:.3f}"))
        layout.addRow("RMSE:", QLabel(f"{metrics['RMSE']:.3f}"))
        layout.addRow("Max absolutt Error:", QLabel(f"{metrics['max_error']:.3f}"))
        layout.addRow("Tid innenfor ±5mm i %:", QLabel(f"{metrics['percent_in_tol']:.2f}%"))
        layout.addRow("Gj.snitt |uP|:", QLabel(f"{metrics['avg_abs_uP']:.3f}"))
        layout.addRow("Gj.snitt |uI|:", QLabel(f"{metrics['avg_abs_uI']:.3f}"))
        layout.addRow("Gj.snitt |uD|:", QLabel(f"{metrics['avg_abs_uD']:.3f}"))
        layout.addRow("P/I/D %:", QLabel(f"{metrics['pct_uP']:.1f}% / {metrics['pct_uI']:.1f}% / {metrics['pct_uD']:.1f}%"))
        layout.addRow("std(uD):", QLabel(f"{metrics['std_uD']:.3f}"))
        layout.addRow("Gj.snitt |power|:", QLabel(f"{metrics['mean_abs_power']:.3f}"))
        layout.addRow("Overshoot (abs):", QLabel(f"{metrics['overshoot']:.3f}"))
        layout.addRow("Overshoot (% av gj.snitt):", QLabel(f"{metrics['overshoot_pct']:.2f}%"))
        layout.addRow("Linmot saturering %:", QLabel(f"{metrics['saturation_pct']:.2f}%"))

        self.oppsummering_group.setLayout(layout)
        container = QWidget()
        v = QVBoxLayout()
        v.addWidget(self.oppsummering_group)
        container.setLayout(v)
        self.setCentralWidget(container)

    def _compute_metrics(self, filename):
        # Setter opp verdiene som skal regnes ut
        metrics = {
            "IAE": 0.0, "MAE": 0.0, "RMSE": 0.0, "max_error": 0.0,
            "percent_in_tol": 0.0,
            "avg_abs_uP": 0.0, "avg_abs_uI": 0.0, "avg_abs_uD": 0.0,
            "pct_uP": 0.0, "pct_uI": 0.0, "pct_uD": 0.0,
            "std_uD": 0.0, "mean_abs_power": 0.0,
            "overshoot": 0.0, "overshoot_pct": 0.0, "saturation_pct": 0.0
        }
        try: # Hadde problemer med verdier som ikke ble lagt inn ordentlig i loggefilen, dette er mest sannsynlig løst etter at framing_errors ble rettet opp i, men skader ikke å beholde
            with open(filename, "r", newline="") as f:
                reader = csv.reader(f) # Åpner CSV-filen
                header = next(reader, None)
                error_l = []
                uP_l = []
                uI_l = []
                uD_l = []
                power_l = []
                distanse_l = []
                for row in reader: # Leser gjennom hver linje i filen og legger verdiene til i respektive lister
                    if len(row) < 10: # Hvis en linje skulle ha færre verdier enn alle 10 blir den skippet
                        continue
                    # Format i CSV-fil: "Tid", "Avstand", "X", "Y", "Z", "Error", "Power", "uP", "uI", "uD"
                    try:
                        dist = float(row[1])
                        err = float(row[5])
                        power = float(row[6])
                        uP = float(row[7])
                        uI = float(row[8])
                        uD = float(row[9])
                    except ValueError:
                        continue
                    distanse_l.append(dist)
                    error_l.append(err)
                    power_l.append(power)
                    uP_l.append(uP)
                    uI_l.append(uI)
                    uD_l.append(uD)

            n = len(error_l)
            if n == 0:
                return metrics


                
                # Error-relaterte metrics
                # IAE - Integral of Absolute Error 
                # RMSE - Root Mean Square Error 
                # MAE - Mean Absolute Error 
                # Max Absolute Error 
                # Time-in-Tolerance (%) (her ±5mm)          
                # PID metrics
                # Average absolute contribution - % of control effort - Viser hvilket av PID leddene som kontributerer mest
                # StdDev of uD - Derivative noise amplification - Stor std(uD) kan være et tegn på at den amplifiserer støy e.l.
                # Mean absolute control effort - høy mean-power ved dårlig performance er et tegn på at bedre tuning behøves, evt. anti-w               
                # Overshoot % - høy overshoot kan tyde på aggressiv tuning eller resonans
                # Actuator saturation - hvis power ofte fører til at styrekortet spør om mer pådrag enn linmoten har tilgjengelig bør den tunes på en annen måte

            dt = 0.01
            metrics["IAE"] = sum(abs(e) * dt for e in error_l)
            metrics["MAE"] = sum(abs(e) for e in error_l) / n
            metrics["RMSE"] = (sum(e*e for e in error_l) / n) ** 0.5
            metrics["max_error"] = max(abs(e) for e in error_l)
            TOL = 5.0
            metrics["percent_in_tol"] = 100 * sum(1 for e in error_l if abs(e) <= TOL) / n

            metrics["avg_abs_uP"] = sum(abs(x) for x in uP_l)/n
            metrics["avg_abs_uI"] = sum(abs(x) for x in uI_l)/n
            metrics["avg_abs_uD"] = sum(abs(x) for x in uD_l)/n

            sum_abs_PID = metrics["avg_abs_uP"] + metrics["avg_abs_uI"] + metrics["avg_abs_uD"]
            if sum_abs_PID == 0:
                metrics["pct_uP"] = metrics["pct_uI"] = metrics["pct_uD"] = 0.0
            else:
                metrics["pct_uP"] = 100 * metrics["avg_abs_uP"]/sum_abs_PID
                metrics["pct_uI"] = 100 * metrics["avg_abs_uI"]/sum_abs_PID
                metrics["pct_uD"] = 100 * metrics["avg_abs_uD"]/sum_abs_PID

            mean_uD = sum(uD_l)/n
            metrics["std_uD"] = (sum((x - mean_uD)**2 for x in uD_l)/n)**0.5
            metrics["mean_abs_power"] = sum(abs(x) for x in power_l)/n

            metrics["overshoot"] = max(error_l)
            mean_distanse = sum(distanse_l)/n if n else 0.0
            metrics["overshoot_pct"] = 100*(metrics["overshoot"] / mean_distanse) if mean_distanse != 0 else 0.0

            linmot_limit = 65535 # Pådragsgrenen for verdien som blir konvertert til linmot-frekvens
            metrics["saturation_pct"] = 100 * sum(1 for p in power_l if abs(p) >= linmot_limit) / n
        except FileNotFoundError:
            # no file yet
            pass
        except Exception as e:
            print("Error computing summary:", e)
        return metrics
# -----------------------------------------------------------------------------------------------

if __name__ == "__main__":
    thread1 = threading.Thread(target=sensor_loop, daemon=True)
    thread1.start()

    applikasjon = QApplication(sys.argv)
    vindu = MainWindow()
    vindu.show()
    applikasjon.exec()
    serieport.close()