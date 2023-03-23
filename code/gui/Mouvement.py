import pantilthat
import time

class Mouvement_camera:
    def __init__(self,hauteur,largeur,xmax,xmin,ymax,ymin):
        self.hauteur=hauteur
        self.largeur=largeur
        self.xmax=xmax
        self.xmin=xmin
        self.ymax=ymax
        self.ymin=ymin
        self.center=[largeur/2,hauteur/2] #entre 0 et 10
        self.centre_tete=[(xmax+xmin)/2,(ymax+ymin)/2] #entre 0 et 1
        self.threshold=0.1 #seuil de sensibilité en dégré
        self.pasbalayage=2
        #self.pasvertical=2
        #self.pashorizontal=2
        self.pas=2
        self.direction="Centre"
        self.boucle_balayage=0
        self.temps=0

    def balayage(self):
        if(self.direction=="Centre"):
            self.mouvement_vertical(0)#centrer l'axe vertical
            self.mouvement_horizontal(0)#centrer l'axe horizontal
            self.direction="Gauche"
        else:
            if(self.boucle_balayage<=1):
                if(self.direction=="Gauche"):
                    if(self.get_position_horizontal()-self.pasbalayage>-90):
                        self.mouvement_horizontal(self.get_position_horizontal()-self.pasbalayage)#Gauche
                    else:
                        self.mouvement_horizontal(-90)
                        self.direction="Droite"
                        self.boucle_balayage+=1
                else:
                    if(self.get_position_horizontal()+self.pasbalayage<90):
                        self.mouvement_horizontal(self.get_position_horizontal()+self.pasbalayage)#Droite
                    else:
                        self.mouvement_horizontal(90)
                        self.direction="Gauche"
            else:
                if(self.temps==0):
                    self.centrer() #centrer caméra
                    self.temps = time.time()#capture du temps actuel
                elif(time.time()-self.temps>5.0):#pause de 5 secondes
                    self.reset()#baculer balayage
        
    def bouger_camera(self):
        self.calculate_centre_tete()
        #self.calcul_pas()
        #H
        if(self.centre_tete[0] > self.center[0]+self.threshold):
            if(self.center[0]+self.threshold<=90):
                self.mouvement_horizontal(self.get_position_horizontal()-self.pas)#Gauche
            else:
                self.mouvement_horizontal(90)
        elif(self.centre_tete[0] < self.center[0]-self.threshold):
            if(self.center[0]-self.threshold>=-90):
                self.mouvement_horizontal(self.get_position_horizontal()+self.pas)#Droite
            else:
                self.mouvement_horizontal(-90)
            
        #V
        if(self.centre_tete[1] > self.center[1]+self.threshold):
            if(self.center[1]+self.threshold<=90):
                self.mouvement_vertical(self.get_position_vertical()+self.pas)#Bas
            else:
                self.mouvement_vertical(90)
        elif(self.centre_tete[1] < self.center[1]-self.threshold):
            if(self.center[1]-self.threshold>=-90):
                self.mouvement_vertical(self.get_position_vertical()-self.pas)#Haut
            else:
                self.mouvement_vertical(-90)


    def calcul_pas(self):
        pas_max=10
        x=self.xmax-self.xmin
        y=self.ymax-self.ymin
        self.pasvertical = round(x*pas_max)
        self.pashorizontal = round(y*pas_max)

    def centrer(self):
        self.mouvement_horizontal(0)
        self.mouvement_vertical(0)

    def reset(self):
        self.direction='Centre'
        self.temps=0
        self.boucle_balayage=0

    def calculate_centre_tete(self):
        self.centre_tete=[(self.xmax+self.xmin)/2,(self.ymax+self.ymin)/2] #entre 0 et 1

    def mouvement_horizontal(self,degre):
        pantilthat.pan(degre)

    def mouvement_vertical(self,degre):
        pantilthat.tilt(degre)

    def get_position_horizontal(self):
        return pantilthat.get_pan()#en degré servo 1

    def get_position_vertical(self):
        return pantilthat.get_tilt()#en degré servo 2

    def setHauteur(self,hauteur):
        self.hauteur=hauteur

    def setLargeur(self,largeur):
        self.largeur=largeur

    def setxmax(self,xmax):
        self.xmax=round(xmax,2)

    def setxmin(self,xmin):
        self.xmin=round(xmin,2)

    def setymax(self,ymax):
        self.ymax=round(ymax,2)

    def setymin(self,ymin):
        self.ymin=round(ymin,2)
    
