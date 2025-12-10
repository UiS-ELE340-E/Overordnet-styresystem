import threading


# ---------------------------------------------------------------
# Initialverdier
Ref_iv = int(300) #mm
Kp_iv = int(2*1000)
Ti_iv = int(1*1000)
Td_iv = int(0*1000)
COMport_nr = 'COM13'  # Endres etter behov
# ---------------------------------------------------------------
# Globale eventer og variabler
start_event = threading.Event()
stopp_event = threading.Event()
stopp_teller = 0


Ref_ny = Ref_iv
Kp_ny = Kp_iv
Ti_ny = Ti_iv
Td_ny = Td_iv

kommando = '0'
status = '0'

tid = []
tid_raa = []
a_x = []
a_y = []
a_z = []
aks_abs = []  # sqrt(ax**2 + ay**2 + az**2)
ayz_abs = []
rull = []     # rullvinkel psi i grader (om x-aksen)
stamp = []    # stampvinkel theta i grader (om y-aksen)

#Tid/sample håndteres internt i funksonen
avstand = 0
x_aks = 0
y_aks = 0
z_aks = 0
error = 0
power = 0
uP = 0
uI = 0
uD = 0

IAE = 0
MAE = 0
RMSE = 0
max_error = 0
percent_in_tol = 0

