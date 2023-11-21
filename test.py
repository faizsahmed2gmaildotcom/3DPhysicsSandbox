# base Vizard libraries
import viz
import vizfx
import vizshape
import vizconnect
import steamvr
import vizact
import viztask
# for trig functions
import math
# used for setting one variable to another
import copy

# controller mode
mode = 'k'
fullscreen = True

# Vizard window initialization
viz.setMultiSample(4)  # FSAA (Full Screen Anti-Alaiasing)
viz.fov(90)
viz.go()

# controls for keyboard/VR
if mode == 'k':
    select = 1
    recall = 'r'
elif mode == 'vr':
    select = 4
    recall = 24
touchPad = 16

if mode == 'vr':
    import steamVR_init
    controls = steamVR_init.Main()
elif mode == 'k':
    import keyboard_mouse_init
    controls = keyboard_mouse_init.Main()
    if fullscreen:
        viz.window.setFullscreen()

refreshRate = 165  # display refresh rate
gConst = 9.81  # gravitational field constant
gasDensity = 1.293  # density of air gas
jointRadius = 0.01  # radius of joints
jointMadness = 0  # yes
theForce = False  # when True, "recalling" points causes them to float slowly to you
jointResolution = 2  # lower to increase performance
pointResolution = 10  # lower to increase performance

# get the scalar distance between 2 points with coordinate attributes
def distance(cordOne, cordTwo):
    diff = [0, 0, 0]
    for d in range(3):
        diff[d] = cordOne[d] - cordTwo[d]
    return math.sqrt(diff[0]**2 + diff[1]**2 + diff[2]**2)

# get the distance between 2 points given differences in x, y, and z values
def diffDistance(diffX, diffY, diffZ):
    return math.sqrt(diffX**2 + diffY**2 + diffZ**2) 

# detects collisions between 2 points with radius attributes (basically spheres)
def detectCollision(pOne, pTwo):
        sumR = pOne.radius + pTwo.radius
        if distance(pOne.cords, pTwo.cords) <= sumR:
            return True

# returns the midpoint of two points
def midpoint(pOne, pTwo):
    mid = [0, 0, 0]
    for m in range(3):
        mid[m] = (pOne.cords[m] + pTwo.cords[m]) / 2
    return [mid[0], mid[1], mid[2]]


# returns the angle [pitch, yaw, roll] between 2 points
def getAngle(pOne, pTwo):
    diff = [0, 0, 0]
    for d in range(3):
        diff[d] = pOne.cords[d] - pTwo.cords[d]
    
    if diff[2] != 0:
        pitch = math.degrees(math.atan(diff[0] / diff[2]))  # angle from x to z
        if diff[0] != 0:
            yaw = 90 - math.degrees(math.atan(diff[1] / math.sqrt(diff[0]**2 + diff[2]**2))) # angle from y to z
        else:
            yaw = 0
    else:
        pitch = 90
        yaw = 0
    #except ZeroDivisionError:
    #    yaw = 0
    if diff[2] <= 0:
        yaw = -yaw  # angle from y to z (reversed since this negates after negative difference along z for some reason)
    roll = jointMadness
    
    return [pitch, yaw, roll]


# Main class for main.py
class Main:
    def __init__(self):
        vizshape.addGrid()
        self.gridFloor = 0  # y-coordinate of test collision axis
        self.points = []  # list of points for the whole program
        self.joints = []  # list of joints for the whole program
        self.collisionRect = []  # list of collision rectangles
        self.dragP = 'none'  # last clicked point index
        self.dragC = 'none'  # last clicked controller index for the last clicked point
        self.lastP = -1  # last clicked point that always retains its value for "recalling" objects to the controller
        self.theForceJoint = False  # True if the force is being used
        self.pause = False  # pauses physics
        self.pHeld = False  # sees if 'p' is held down
    
    def main(self):
        # pause if 'p' is pressed
        if ((mode =='k' and viz.key.isDown('p')) or (mode == 'vr')) and (not self.pHeld):
            self.pause = not self.pause
            self.pHeld = True
        elif not viz.key.isDown('p'):
            self.pHeld = False
        
        
        controls.main()  # runs the main function in the current control (keyboard/VR) setting
        self.dragPoints()  # runs the function that detects if controller is "dragging" a point
        
        # update the visuals of joints and constrain points
        for j in range(len(self.joints)):
            self.joints[j].update()
            if not self.pause:
                self.joints[j].constrain()
        
        # detect & resolve collisions with collision boxes
        for p in range(len(self.points)):
            if (self.points[p].cords[1] - self.points[p].radius) <= self.gridFloor:
                self.points[p].cords[1] = self.points[p].oldCords[1]
                # self.points[p].oldCords[1] = self.points[p].cords[1] + self.points[p].velocity[1]
            # detect collisions with other points
            for po in range(len(self.points)):
                if detectCollision(self.points[p], self.points[po]) and (p != po):
                    pass
            
            self.points[p].boxCollision()
            self.points[p].move()
   
   # used to drag points around using pointer/controller
    def dragPoints(self):
        for p in range(len(self.points)):
            for c in range(len(controls.hand)):
                if ((mode == 'k') and (viz.mouse.getState() == select)) or ((mode == 'vr') and (steamVR_init.controllers[c].getButtonState() == select)):  # detect if the select button is being pressed, depending on the controller mode
                    if (self.dragP == 'none') and (self.dragC == 'none'):  # used to set the drag variables if they are not already set
                        if detectCollision(self.points[p], controls.hand[c]):
                            self.dragP = p
                            self.lastP = p
                            self.dragC = c
                    else:
                        self.points[self.dragP].cords = copy.deepcopy(controls.hand[self.dragC].cords)  # set the point position to the controller (that grabbed that point)'s position
                # reset drag variables if select button is not pressed
                elif (self.dragC != 'none') and (((mode == 'vr') and (steamVR_init.controllers[self.dragC].getButtonState() != select)) or ((mode == 'k') and (viz.mouse.getState() != select))):
                    self.dragP = 'none'
                    self.dragC = 'none'
                # recalls the last clicked point to the controller's position
                if ((mode == 'vr') and (steamVR_init.controllers[c].getButtonState() == recall)) or ((mode == 'k') and viz.key.isDown(recall)):
                    # allows the force to be used (if True)
                    if theForce and (self.theForceJoint == False):
                        self.joints.append(Joint(False, 0, 0.05, None, self.lastP, True, c))
                        self.theForceJoint = True
                    # set cords of point to user pointer/hand
                    elif not theForce:
                        self.points[self.lastP].cords = copy.deepcopy(controls.hand[c].cords)
                # remove the force joint after recall is no longer active
                elif self.theForceJoint:
                    if self.joints[-1].show:
                        self.joints[-1].cylinder.remove()
                    self.joints.pop(-1)
                    self.theForceJoint = False



# class for spheres
class Point:
    def __init__(self, radius, density):
        self.radius = radius
        self.sphere = vizshape.addSphere(radius, slices=pointResolution)  # vizard object for sphere
        self.cords = [0, 0, 0]
        self.oldCords = [0, 0, 0]  # coordinates from last frame
        self.velocity = [0, 0, 0]
        self.force = [0, 0, 0]
        self.acc = [0, 0, 0]
        self.density = density
        self.volume = 4/3 * math.pi * self.radius**3
        self.mass = self.density * self.volume
        self.weight = self.mass * gConst
        self.gasDrag = [0, 0, 0]
        self.liquidDrag = [0, 0, 0]
        self.gasUpthrust = [0, 0, 0]
        self.liquidUpthrust = [0, 0, 0]
        self.friction = [0, 0, 0]
        self.constrainForce = [0, 0, 0]
        self.collision = ''
        
    
    def setRadiusDensity(self, radius, density):
        self.radius = radius
        self.volume = 4/3 * math.pi * self.radius**3
        self.mass = density * self.volume
        self.weight = self.mass * gConst
        self.sphere.remove()
        self.sphere = vizshape.addSphere(radius, slices=pointResolution)
    
    
    def move(self):
        # Verlet integration
        for c in range(3):
            self.velocity[c] = self.cords[c] - self.oldCords[c]  # set velocity to change in position
        
        if not game.pause:
            self.physics()  # run physics if the game is not paused
        
        self.oldCords = copy.deepcopy(self.cords)
        
        if not game.pause:
            for v in range(3):
                self.cords[v] += self.velocity[v]  # change coordinates based on velocity
        
        self.sphere.setPosition(self.cords)
    
    
    def physics(self):
        for axis in range(3):
            # add physics here
            
            self.force[axis] = self.gasDrag[axis] + self.liquidDrag[axis] + self.gasUpthrust[axis] + self.liquidUpthrust[axis] + self.friction[axis] + self.constrainForce[axis]
            if axis == 1:
                self.force[1] -= self.weight
            self.acc[axis] = self.force[axis] / self.mass
            self.velocity[axis] += self.acc[axis] / (refreshRate**2)
    
    
    def boxCollision(self):
        for b in game.collisionRect:
            if (self.cords[1] > b.plane['bottom']) and (self.cords[1] < b.plane['top']):
                if (self.cords[2] < b.plane['front']) and (self.cords[2] > b.plane['back']):
                    if self.cords[0] > b.plane['right']:
                        self.collision = 'right'
                    elif self.cords[0] < b.plane['left']:
                        self.collision = 'left'
                elif (self.cords[0] > b.plane['left']) and (self.cords[0] < b.plane['right']):
                    if self.cords[2] > b.plane['front']:
                        self.collision = 'front'
                    elif self.cords[2] < b.plane['back']:
                        self.collision = 'back'
            elif (self.cords[0] > b.plane['left']) and (self.cords[0] < b.plane['right']) and (self.cords[2] < b.plane['front']) and (self.cords[2] > b.plane['back']):
                if self.cords[1] > b.plane['top']:
                    self.collision = 'top'
                elif self.cords[1] < b.plane['bottom']:
                    self.collision = 'bottom'
            
            vertexDist = []
            for v in b.vertex:
                vertexDist.append(distance(self.cords, v))
            tempList = copy.deepcopy(vertexDist)
            minDist = [vertexDist[0], vertexDist[0]]
            for i in range(2):
                for ve in range(len(vertexDist)):
                    if i == 0:
                        if vertexDist[ve] < minDist[0]:
                            minDist[0] = vertexDist[ve]
                            tempIdx = ve
                    if i == 1:
                        if vertexDist[ve] < minDist[1]:#(vertexDist[ve] >= minDist[0]) and (vertexDist[ve] < minDist[1]):
                            minDist[1] = vertexDist[ve]
                if i == 0:
                    try:
                        vertexDist.pop(tempIdx)
                    except UnboundLocalError:
                        pass
                    # get max 2 values in list
            print(minDist)
            # minDist[0] += self.radius
            # minDist[1] += self.radius
            minDist[0] = math.sqrt(minDist[0]**2 - self.radius**2)
            minDist[1] = math.sqrt(minDist[1]**2 - self.radius**2)
            print(tempList)
            print(minDist)
            if (minDist[0] + minDist[1]) <= 2:
                print('vertex collision!')
                self.cords = self.oldCords
            #elif ((self.cords[0] + self.radius) > b.plane['left']) and ((self.cords[0] - self.radius) < b.plane['right']) and ((self.cords[1] + self.radius) > b.plane['bottom']) and ((self.cords[1] - self.radius) < b.plane['top']) and ((self.cords[2] - self.radius) < b.plane['front']) and ((self.cords[2] + self.radius) > b.plane['back']):
            #    self.cords = self.oldCords
            else:
                print(self.collision)
            



# class for cylinders (joints) connecting spheres
class Joint:
    def __init__(self, show, maxLength, stiffness, pOne, pTwo, *theForceJoint):
        self.height = 1
        self.pOne = pOne
        self.pTwo = pTwo
        if stiffness == '':
            self.stiffness = 0.1
        else:
            self.stiffness = stiffness
        self.cords = [0, 0, 0]
        self.angle = [0, 0, 0]
        self.show = show
        if maxLength == '':
            self.maxLength = distance(game.points[self.pOne].cords, game.points[self.pTwo].cords)
        else:
            self.maxLength = maxLength
        self.diff = [0, 0, 0]  # prevents multiple sq(rt) calculations to increase performance
        self._update = [0, 0, 0]
        if self.show:
            self.cylinder = vizshape.addCylinder(self.height, jointRadius, slices=jointResolution)  # make the cyldinder object for the joint if shown
        self.theForceJoint = False
        self.cIdx = -1
        # additional arguments to set the joint to be "the chosen force joint"
        if len(theForceJoint) > 0:
            self.theForceJoint = theForceJoint[0]
            self.cIdx = theForceJoint[1]
        
    
    # update the position and appearance of the joint
    def update(self):
        if self.show:
            self.cylinder.remove()
        
        for d in range(3):
            if self.theForceJoint:
                self.diff[d] = controls.hand[self.cIdx].cords[d] - game.points[self.pTwo].cords[d]
            else:
                self.diff[d] = game.points[self.pOne].cords[d] - game.points[self.pTwo].cords[d]
        
        self.height = diffDistance(self.diff[0], self.diff[1], self.diff[2])
        
        if self.show:
            self.cylinder = vizshape.addCylinder(self.height, jointRadius, slices=jointResolution)
            if self.theForceJoint:
                self.cords = midpoint(controls.hand[self.cIdx], game.points[self.pTwo])
                self.cylinder.setEuler(getAngle(controls.hand[self.cIdx], game.points[self.pTwo]))
            else:
                self.cords = midpoint(game.points[self.pOne], game.points[self.pTwo])
                self.cylinder.setEuler(getAngle(game.points[self.pOne], game.points[self.pTwo]))
            
            self.cylinder.setPosition(self.cords)
        
    
    # constrain points connected to this joint
    def constrain(self):
        if (self.height < self.maxLength) or (self.height > self.maxLength):
            for u in range(3):
                self._update[u] = self.stiffness * self.diff[u] * ((self.maxLength / self.height) - 1)
        
        
        for i in range(3):
            if self.theForceJoint:
                game.points[self.pTwo].cords[i] -= self._update[i]  # pull last dragged point regardless of its mass
            else:
                game.points[self.pOne].cords[i] += self._update[i] / game.points[self.pOne].mass  # pull each point depending on its mass
                game.points[self.pTwo].cords[i] -= self._update[i] / game.points[self.pTwo].mass  # pull each point depending on its mass 



class CollisionRect:
    def __init__(self, size, cords, angle):
        self.size = size
        self.rect = vizshape.addBox(self.size)
        self.cords = cords
        self.angle = angle
        self.vertex = []
        self.plane = {
        'front': [0, 0, 0],
        'back': [0, 0, 0],
        'left': [0, 0, 0],
        'right': [0, 0, 0],
        'top': [0, 0, 0],
        'bottom': [0, 0, 0]
        }
        self.update()
    
    
    def update(self):
        self.rect.remove()
        self.rect = vizshape.addBox(self.size)
        self.rect.setPosition(self.cords)
        self.rect.setEuler(self.angle)
        sizeMultiplier = [0.5, 0.5, 0.5]
        for v in range(8):
            if (v == 1) or (v == 5):
                sizeMultiplier[0] = -sizeMultiplier[0]
            elif (v == 2) or (v == 6):
                sizeMultiplier[0] = -sizeMultiplier[0]
                sizeMultiplier[1] = -sizeMultiplier[1]
            elif (v == 3) or (v == 7):
                sizeMultiplier[0] = -sizeMultiplier[0]
            elif v == 4:
                sizeMultiplier[0] = -sizeMultiplier[0]
                sizeMultiplier[1] = -sizeMultiplier[1]
                sizeMultiplier[2] = -sizeMultiplier[2]
            tempVertex = [0, 0, 0]
            for i in range(3):
                tempVertex[i] = self.cords[i] + (self.size[i] * sizeMultiplier[i])
            self.vertex.append(tempVertex)
        self.plane['front'] = self.cords[2] + (self.size[2] / 2)
        self.plane['back'] = self.cords[2] - (self.size[2] / 2)
        self.plane['left'] = self.cords[0] - (self.size[0] / 2)
        self.plane['right'] = self.cords[0] + (self.size[0] / 2)
        self.plane['top'] = self.cords[1] + (self.size[1] / 2)
        self.plane['bottom'] = self.cords[1] - (self.size[1] / 2)



game = Main()

# makes a cube using points and joints
#cubeSize = 8
#for ve in range(cubeSize):
#    if ve != 7:
#        game.points.append(Point(0.1, 1000))
#    else:
#        game.points.append(Point(0.3, 1000))
#game.points[0].cords = [2, 4.5, 2]  # top-front-right
#game.points[0].oldCords = [2, 4.5, 2]
#game.points[1].cords = [2, 4.5, -2]  # top-back-right
#game.points[1].oldCords = [2, 4.5, -2]
#game.points[2].cords = [-2, 4.5, -2]  # top-back-left
#game.points[2].oldCords = [-2, 4, -2]
#game.points[3].cords = [-2, 4.5, 2]  # top-front-left
#game.points[3].oldCords = [-2, 4, 2]
#game.points[4].cords = [2, 0.5, 2]
#game.points[4].oldCords = [2, 0.5, 2]
#game.points[5].cords = [2, 0.5, -2]
#game.points[5].oldCords = [2, 0, -2]
#game.points[6].cords = [-2, 0.5, -2]
#game.points[6].oldCords = [-2, 0.5, -2]
#game.points[7].cords = [-2, 0.5, 2]
#game.points[7].oldCords = [-2, 0.5, 2]

#for j in range(cubeSize):
#    for jo in range(cubeSize):
#        if (j != jo) and (jo >= j):
#            game.joints.append(Joint(True, '', 0.4, j, jo))

game.points.append(Point(1, 1))

game.collisionRect.append(CollisionRect((2, 2, 2), [0, 2, -10], [0, 0, 0]))

vizact.ontimer(1 / refreshRate, game.main)  # run game.main refreshRate times each second
# add framerate here
