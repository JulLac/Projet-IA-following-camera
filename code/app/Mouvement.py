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
        self.center=[largeur/2,hauteur/2] #entre 0 et 1
        self.centre_tete=[(xmax+xmin)/2,(ymax+ymin)/2] #entre 0 et 1
        self.threshold=0.1 #seuil de sensibilité en dégré
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
                    if(self.get_position_horizontal()-self.getpas()>-90):
                        self.mouvement_horizontal(self.get_position_horizontal()-self.getpas())
                    else:
                        self.mouvement_horizontal(-90)
                        self.direction="Droite"
                        self.boucle_balayage+=1
                else:
                    if(self.get_position_horizontal()+self.getpas()<90):
                        self.mouvement_horizontal(self.get_position_horizontal()-self.getpas())
                    else:
                        self.mouvement_horizontal(90)
                        self.direction="Gauche"
            else:
                if(self.temps==0):
                    self.centrer() #centrer caméra
                    self.temps = time.time()#capture du temps actuel

                if(self.temps+5.0>=time.time()):#pause de 5 secondes
                    self.reset()#baculer balayage
        
    def bouger_camera(self):
        self.calculate_centre_tete()

        #H
        if(self.getcentre_tete()[0] > self.getcenter()[0]+self.threshold):
            self.mouvement_horizontal(self.get_position_horizontal()-self.getpas())
        elif(self.getcentre_tete()[0] < self.getcenter()[0]-self.threshold):
            self.mouvement_horizontal(self.get_position_horizontal()+self.getpas())
            
        #V
        if(self.getcentre_tete()[1] > self.getcenter()[1]+self.threshold):
            self.mouvement_vertical(self.get_position_vertical()+self.getpas())
        elif(self.getcentre_tete()[1] < self.getcenter()[1]-self.threshold):
            self.mouvement_vertical(self.get_position_vertical()-self.getpas())

    def centrer(self):
        self.mouvement_horizontal(0)
        self.mouvement_vertical(0)

    def reset(self):
        self.direction='Centre'
        self.temps=0
        self.boucle_balayage=0

    def getpas(self):
        return self.pas

    def calculate_centre_tete(self):
        self.centre_tete=[(self.getxmax()+self.getxmin())/2,(self.getymax()+self.getymin())/2] #entre 0 et 1

    def mouvement_horizontal(self,degre):
        pantilthat.pan(degre)

    def mouvement_vertical(self,degre):
        pantilthat.tilt(degre)

    def get_position_horizontal(self):
        return pantilthat.get_pan()#en degré servo 1

    def get_position_vertical(self):
        return pantilthat.get_tilt()#en degré servo 2

    def getcentre_tete(self):
        return self.centre_tete

    def gethreshold(self):
        return self.threshold

    def getcenter(self):
        return self.center

    def setHauteur(self,hauteur):
        self.hauteur=hauteur

    def getHauteur(self):
        return self.largeur

    def setLargeur(self,largeur):
        self.largeur=largeur

    def getLargeur(self):
        return self.largeur

    def getxmax(self):
        return self.xmax

    def getxmin(self):
        return self.xmin

    def getymax(self):
        return self.ymax

    def getymin(self):
        return self.ymin

    def setxmax(self,xmax):
        self.xmax=round(xmax,2)

    def setxmin(self,xmin):
        self.xmin=round(xmin,2)

    def setymax(self,ymax):
        self.ymax=round(ymax,2)

    def setymin(self,ymin):
        self.ymin=round(ymin,2)
    
