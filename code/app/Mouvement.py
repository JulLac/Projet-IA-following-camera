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

"""
sources : https://github.com/pimoroni/pantilt-hat 
                   http://docs.pimoroni.com/pantilthat/
x=horizontal et y=vertical
Haut   <-- (-90°)  0 (90°) --> Bas
Gauche <-- (-90°)  0 (90°) --> Droite
"""

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
        """
        But: Bouger la caméra hozizontalement et verticalement pour centrer la bounding box reçu au centre de l'objectif
        :return: Mouvement de la caméra
        """
        position_horizontal=self.get_position_horizontal()
        position_vertical=self.get_position_vertical()
        self.calculate_centre_tete()
        self.enable_servo()#mettre en route les moteurs

        #Obtenir un pas fort ou faible en fct de la distance de la bounding box
        pas_horizontal,pas_vertical=self.gestion_pas_camera_Horizontal_Vertical()

        #Horizontal
        if(self.centre_tete[0] > self.center[0]+threshold_horizontal):
            if(position_horizontal-pas_horizontal>=self.max_degre_x_gauche):
                self.mouvement_horizontal(position_horizontal-pas_horizontal)#Gauche
            else:
                self.mouvement_horizontal(self.max_degre_x_gauche)
        elif(self.centre_tete[0] < self.center[0]-threshold_horizontal):
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
        """
        But: Déterminer un pas fort ou faible en fct de la distance du centre de la bounding box et du centre de l'objectif selon un certain seuil
        :return: liste_pas type(liste)
                 liste_pas[0] = pas fort/faible horizontal
                 liste_pas[1] = pas fort/faible vertical
        """
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

        """
        But: Balayer le champ de vision pour détecter une personne (Centre->Gauche->Droite->Gauche->Droite->Centre->Pause 5 secondes->..etc)
        :return: Mouvement de la caméra
        """
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
                        self.mouvement_horizontal(self.max_degre_x_gauche)#Limite Gauche
                        self.direction=Droite
                        self.boucle_balayage+=1
                else:
                    if(position_horizontal+pas_balayage<self.max_degre_x_droite):
                        self.mouvement_horizontal(position_horizontal+pas_balayage)#Droite
                    else:
                        self.mouvement_horizontal(self.max_degre_x_droite)#Limite Droite
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
        """
        But : Centrer la caméra en sa position initiale choisie
        :return: Mouvement de la caméra
        """
        self.mouvement_horizontal(position_degre_defaut_x)
        self.mouvement_vertical(position_degre_defaut_y)
    
    def centrer_bridage(self,x_gauche,x_droite,y_haut,y_bas):
        """
        But : Centrer la caméra en sa position initiale en fonction du bridage en degré choisi
        :return: Mouvement de la caméra
        """
        self.mouvement_horizontal((x_droite+x_gauche)/2)
        self.mouvement_vertical((y_bas+y_haut)/2)

    def reset(self):
        """
        But : Réinitialiser les variables permettant le balayage
        """
        self.direction=Centre
        self.temps=0
        self.boucle_balayage=0

    def calculate_centre_tete(self):
        """
        But : Centrer la caméra en sa position initiale en fonction du bridage en degré choisi
        :return: self.centre_tete[0] -> coordonnées horizontal
                 self.centre_tete[1] -> coordonnées vertical
        """
        self.centre_tete=[(self.xmax+self.xmin)/2,(self.ymax+self.ymin)/2] #entre 0 et 1

    def mouvement_horizontal(self,degre):
        """
        But : Bouger la caméra horizontalement
        :return: Mouvement de la caméra
        """
        if(degre<=self.max_degre_x_droite and degre>=self.max_degre_x_gauche):
            pantilthat.pan(degre)#servo 1
        else:
            print("limite atteinte 'degré' pour mouvement horizontal, degré=",degre," ;max degré=[",self.max_degre_x_droite,',',self.max_degre_x_gauche,']')

    def mouvement_vertical(self,degre):
        """
        But : Bouger la caméra verticalement
        :return: Mouvement de la caméra
        """
        if(degre<=self.max_degre_y_bas and degre>=self.max_degre_y_haut):
            pantilthat.tilt(degre)#servo 2
        else:
            print("limite atteinte 'degré' pour mouvement vertical, degré=",degre," ;max degré=[",self.max_degre_y_haut,',',self.max_degre_y_bas,']')

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
        pantilthat.servo_enable(1,False)#servo 1
        pantilthat.servo_enable(2,False)#servo 2

    def enable_servo(self):
        pantilthat.servo_enable(1,True)#servo 1
        pantilthat.servo_enable(2,True)#servo 2

    def set_max_degre_x_gauche(self,degre):
        self.max_degre_x_gauche=degre

    def set_max_degre_x_droite(self,degre):
        self.max_degre_x_droite=degre

    def set_max_degre_y_haut(self,degre):
        self.max_degre_y_haut=degre

    def set_max_degre_y_bas(self,degre):
        self.max_degre_y_bas=degre
