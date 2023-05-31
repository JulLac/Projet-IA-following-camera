import pantilthat
import time

#CONSTANTES
position_degre_defaut_x=0
position_degre_defaut_y=-10
threshold_horizontal=0.1 #seuil de sensibilité mouvement horizontal
threshold_vertical=0.1 #seuil de sensibilité mouvement vertical
threshold_pas=0.25 #distance à laquelle on switch entre un pas moteur faible ou fort
pas_balayage=1 #pas en degré lors du balayage de la caméra
pas_faible=2 #pas en degré lors d'un mouvement faible de la caméra
pas_fort=7 #pas en degré lors d'un mouvement fort de la caméra
Gauche="Gauche"
Droite="Droite"
Centre="Centre"

#x=horizontal et y=vertical

class Mouvement_camera:
    def __init__(self,hauteur,largeur,xmax,xmin,ymax,ymin):
        self.hauteur=hauteur
        self.largeur=largeur
        self.xmax=xmax
        self.xmin=xmin
        self.ymax=ymax
        self.ymin=ymin
        self.center=[largeur/2,hauteur/2] #entre 0 et 1
        self.centre_tete=[(xmax+xmin)/2,(ymax+ymin)/2] #entre 0 et 1
        self.direction=Centre
        self.boucle_balayage=0
        self.temps=0
        self.max_degre_x_gauche=-90
        self.max_degre_x_droite=90
        self.max_degre_y_haut=-90
        self.max_degre_y_bas=90

    def bouger_camera(self):
        self.calculate_centre_tete()
        position_horizontal=self.get_position_horizontal()
        position_vertical=self.get_position_vertical()
        self.enable_servo()#mettre en route les moteurs

        #Obtenir un pas fort ou faible en fct de la distance de la tête en fonction de la distance de la personne
        pas_horizontal,pas_vertical=self.gestion_pas_camera_Horizontal_Vertical()

        #Horizontal
        if(self.centre_tete[0] > self.center[0]+threshold_horizontal):#Tête à droite
            if(position_horizontal-pas_horizontal>=self.max_degre_x_gauche):
                self.mouvement_horizontal(position_horizontal-pas_horizontal)#Gauche
            else:
                self.mouvement_horizontal(self.max_degre_x_gauche)
        elif(self.centre_tete[0] < self.center[0]-threshold_horizontal):#Tête à gauche
            if(position_horizontal+pas_horizontal<=self.max_degre_x_droite):
                self.mouvement_horizontal(position_horizontal+pas_horizontal)#Droite
            else:
                self.mouvement_horizontal(self.max_degre_x_droite)

        #Vertical
        if(self.centre_tete[1] > self.center[1]+threshold_vertical):#Tête en bas
            if(position_vertical+pas_vertical<=self.max_degre_y_bas):
                self.mouvement_vertical(position_vertical+pas_vertical)#Bas
            else:
                self.mouvement_vertical(self.max_degre_y_bas)
        elif(self.centre_tete[1] < self.center[1]-threshold_vertical):#Tête en haut
            if(position_vertical-pas_vertical>=self.max_degre_y_haut):
                self.mouvement_vertical(position_vertical-pas_vertical)#Haut
            else:
                self.mouvement_vertical(self.max_degre_y_haut)

    def gestion_pas_camera_Horizontal_Vertical(self):
        liste_pas=[]
        #Horizontal
        if((self.centre_tete[0] - self.center[0]+threshold_horizontal >threshold_pas) or (self.center[0]-threshold_horizontal -self.centre_tete[0] > threshold_pas)):
            liste_pas.append(pas_fort)
        else:
            liste_pas.append(pas_faible)

        #Vertical
        if((self.centre_tete[1] - self.center[1]+threshold_vertical >threshold_pas) or (self.center[1]-threshold_vertical -self.centre_tete[1] > threshold_pas)):
            liste_pas.append(pas_fort)
        else:
            liste_pas.append(pas_faible)
        return liste_pas[0],liste_pas[1]

    def balayage(self):
        position_horizontal=self.get_position_horizontal()
        position_vertical=self.get_position_vertical()
        if(self.direction==Centre):
            if(position_horizontal<=position_degre_defaut_x+1 and position_horizontal>=position_degre_defaut_x-1 and position_vertical<=position_degre_defaut_y+1 and position_vertical>=position_degre_defaut_y-1 ):
                self.direction=Gauche
            else:#Centrer de manière smooth
                #Gauche ou droite
                if(position_horizontal>position_degre_defaut_x):#Gauche
                    self.mouvement_horizontal(position_horizontal-1)
                else:#Droite
                    self.mouvement_horizontal(position_horizontal+1)

                #Haut ou bas
                if(position_vertical>position_degre_defaut_y):#Haut
                    self.mouvement_vertical(position_vertical-1)
                else:#Bas
                    self.mouvement_vertical(position_vertical+1)

        else:
            if(self.boucle_balayage<=1):
                if(self.direction==Gauche):
                    if(position_horizontal-pas_balayage>self.max_degre_x_gauche):
                        self.mouvement_horizontal(position_horizontal-pas_balayage)#Gauche
                    else:
                        self.mouvement_horizontal(self.max_degre_x_gauche)
                        self.direction=Droite
                        self.boucle_balayage+=1
                else:
                    if(position_horizontal+pas_balayage<self.max_degre_x_droite):
                        self.mouvement_horizontal(position_horizontal+pas_balayage)#Droite
                    else:
                        self.mouvement_horizontal(self.max_degre_x_droite)
                        self.direction=Gauche
            else:
                if(position_horizontal!=0):#centrer de manière smooth à la fin du balayage
                    self.mouvement_horizontal(position_horizontal+pas_balayage)#Gauche
                else:
                    if(self.temps==0):
                        self.temps = time.time()#capture du temps actuel
                        self.disable_servo()#arrêt des moteurs
                    elif(time.time()-self.temps>5.0):#pause de 5 secondes
                        self.reset()#baculer en mode balayage
                        self.enable_servo()#mettre en route les moteurs

    def centrer(self):
        self.mouvement_horizontal(position_degre_defaut_y)
        self.mouvement_vertical(position_degre_defaut_x)

    def reset(self):
        self.direction=Centre
        self.temps=0
        self.boucle_balayage=0

    def calculate_centre_tete(self):
        #calcul_quart_moitie=(self.ymax+self.ymin/2)/4
        #self.centre_tete=[(self.xmax+self.xmin)/2,((self.ymax+self.ymin)/2)-calcul_quart_moitie] #entre 0 et 1
        self.centre_tete=[(self.xmax+self.xmin)/2,(self.ymax+self.ymin)/2] #entre 0 et 1

    def mouvement_horizontal(self,degre):
        if(degre<=self.max_degre_x_droite and degre>=self.max_degre_x_gauche):
            pantilthat.pan(degre)
        else:
            print("Erreur paramètre 'degré' pour mouvement horizontal hors limite, degré=",degre," ;max degré=[",self.max_degre_x_droite,',',self.max_degre_x_gauche,']')

    def mouvement_vertical(self,degre):
        if(degre<=self.max_degre_y_bas and degre>=self.max_degre_y_haut):
            pantilthat.tilt(degre)
        else:
            print("Erreur paramètre 'degré' pour mouvement vertical hors limite, degré=",degre," ;max degré=[",self.max_degre_y_haut,',',self.max_degre_y_bas,']')

    def get_position_horizontal(self):
        return pantilthat.get_pan()#en degré servo 1

    def get_position_vertical(self):
        return pantilthat.get_tilt()#en degré servo 2

    def setxmax(self,xmax):
        self.xmax=round(xmax,2)

    def setxmin(self,xmin):
        self.xmin=round(xmin,2)

    def setymax(self,ymax):
        self.ymax=round(ymax,2)

    def setymin(self,ymin):
        self.ymin=round(ymin,2)

    def disable_servo(self):
        pantilthat.servo_enable(1,False)
        pantilthat.servo_enable(2,False)

    def enable_servo(self):
        pantilthat.servo_enable(1,True)
        pantilthat.servo_enable(2,True)

    def set_max_degre_x_gauche(self,degre):
        self.max_degre_x_gauche=degre

    def set_max_degre_x_droite(self,degre):
        self.max_degre_x_droite=degre

    def set_max_degre_y_haut(self,degre):
        self.max_degre_y_haut=degre

    def set_max_degre_y_bas(self,degre):
        self.max_degre_y_bas=degre